from dataclasses import asdict, dataclass

from sqlalchemy.orm import Session

from app.models import MarketCandle, Strategy, WalkForwardRun
from app.schemas.trading import (
    WalkForwardAggregatedResult,
    WalkForwardMetrics,
    WalkForwardRequest,
    WalkForwardRunRead,
)
from app.services.audit import record_event
from app.services.backtesting.engine import BacktestTrade, annualized_sharpe
from app.services.indicators.technical import rsi
from app.services.repository import ensure_default_strategy, get_symbol, list_candles, seed_defaults


@dataclass(frozen=True)
class CandidateParameters:
    fast_ema: int
    slow_ema: int
    rsi_ceiling: int
    exposure: float


CANDIDATES = [
    CandidateParameters(fast_ema=9, slow_ema=21, rsi_ceiling=72, exposure=0.15),
    CandidateParameters(fast_ema=12, slow_ema=26, rsi_ceiling=70, exposure=0.20),
    CandidateParameters(fast_ema=20, slow_ema=50, rsi_ceiling=68, exposure=0.25),
    CandidateParameters(fast_ema=8, slow_ema=34, rsi_ceiling=74, exposure=0.18),
]


def run_walk_forward(db: Session, payload: WalkForwardRequest) -> WalkForwardRunRead:
    seed_defaults(db)
    symbol = get_symbol(db, payload.symbol)
    if symbol is None:
        raise ValueError(f"Symbol {payload.symbol.upper()} is not configured")

    strategy = db.get(Strategy, payload.strategy_id) if payload.strategy_id else ensure_default_strategy(db)
    if strategy is None:
        raise ValueError("Strategy not found")

    required_candles = payload.training_period + payload.validation_period + payload.test_period + (
        (payload.rolling_windows - 1) * payload.test_period
    )
    candles = list_candles(db, symbol.symbol, payload.timeframe, required_candles)
    if len(candles) < required_candles:
        raise ValueError(f"At least {required_candles} candles are required for this walk-forward configuration")

    window_results = []
    optimization_results = []
    out_of_sample_results = []
    test_returns = []
    validation_returns = []
    all_test_trades: list[BacktestTrade] = []
    max_drawdown = 0.0
    compounded_return = 1.0

    for window in range(payload.rolling_windows):
        start = window * payload.test_period
        train_slice = candles[start : start + payload.training_period]
        validation_slice = candles[start + payload.training_period : start + payload.training_period + payload.validation_period]
        test_slice = candles[
            start + payload.training_period + payload.validation_period : start + payload.training_period + payload.validation_period + payload.test_period
        ]

        ranked_candidates = []
        for candidate in CANDIDATES:
            training_metrics = simulate_window(train_slice, payload.initial_balance, candidate)
            validation_metrics = simulate_window(validation_slice, payload.initial_balance, candidate)
            score = optimization_score(validation_metrics)
            ranked_candidates.append(
                {
                    "parameters": asdict(candidate),
                    "score": round(score, 6),
                    "training_metrics": training_metrics.model_dump(),
                    "validation_metrics": validation_metrics.model_dump(),
                }
            )

        ranked_candidates.sort(key=lambda item: item["score"], reverse=True)
        selected = ranked_candidates[0]
        selected_params = CandidateParameters(**selected["parameters"])
        test_metrics, test_trades = simulate_window_with_trades(test_slice, payload.initial_balance, selected_params)

        window_result = {
            "window": window + 1,
            "train_start": train_slice[0].opened_at.isoformat(),
            "train_end": train_slice[-1].opened_at.isoformat(),
            "validation_start": validation_slice[0].opened_at.isoformat(),
            "validation_end": validation_slice[-1].opened_at.isoformat(),
            "test_start": test_slice[0].opened_at.isoformat(),
            "test_end": test_slice[-1].opened_at.isoformat(),
            "selected_parameters": selected["parameters"],
            "optimization_score": selected["score"],
            "training_metrics": selected["training_metrics"],
            "validation_metrics": selected["validation_metrics"],
            "test_metrics": test_metrics.model_dump(),
        }
        window_results.append(window_result)
        optimization_results.append({"window": window + 1, "candidates": ranked_candidates})
        out_of_sample_results.append({"window": window + 1, "metrics": test_metrics.model_dump()})
        test_returns.append(test_metrics.total_return)
        validation_returns.append(selected["validation_metrics"]["total_return"])
        all_test_trades.extend(test_trades)
        max_drawdown = max(max_drawdown, test_metrics.max_drawdown)
        compounded_return *= 1 + test_metrics.total_return

    aggregate = aggregate_results(
        windows=payload.rolling_windows,
        cumulative_return=compounded_return - 1,
        test_returns=test_returns,
        validation_returns=validation_returns,
        trades=all_test_trades,
        max_drawdown=max_drawdown,
    )
    warning = build_warning(aggregate)
    run = WalkForwardRun(
        symbol_id=symbol.id,
        strategy_id=strategy.id,
        timeframe=payload.timeframe,
        training_period=payload.training_period,
        validation_period=payload.validation_period,
        test_period=payload.test_period,
        rolling_windows=payload.rolling_windows,
        initial_balance=payload.initial_balance,
        optimization_results=optimization_results,
        out_of_sample_results=out_of_sample_results,
        window_metrics=window_results,
        aggregated_result=aggregate.model_dump(),
        status="completed",
        warning=warning,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    record_event(
        db,
        event_type="backtest.walk_forward.completed",
        entity_type="walk_forward",
        entity_id=run.id,
        message=f"Walk-forward test completed for {symbol.symbol}.",
        metadata={"symbol": symbol.symbol, "timeframe": payload.timeframe, "cumulative_return": aggregate.cumulative_return},
        commit=True,
    )
    return walk_forward_to_schema(run)


def get_walk_forward_run(db: Session, run_id: int) -> WalkForwardRunRead | None:
    run = db.get(WalkForwardRun, run_id)
    return walk_forward_to_schema(run) if run else None


def simulate_window(candles: list[MarketCandle], initial_balance: float, params: CandidateParameters) -> WalkForwardMetrics:
    metrics, _trades = simulate_window_with_trades(candles, initial_balance, params)
    return metrics


def simulate_window_with_trades(
    candles: list[MarketCandle],
    initial_balance: float,
    params: CandidateParameters,
) -> tuple[WalkForwardMetrics, list[BacktestTrade]]:
    balance = initial_balance
    peak_balance = initial_balance
    max_drawdown = 0.0
    position_entry: float | None = None
    position_size = 0.0
    trades: list[BacktestTrade] = []
    equity_curve = [initial_balance]
    closes = [candle.close for candle in candles]

    start_index = min(max(params.slow_ema + 1, 30), max(1, len(candles) - 1))
    for index in range(start_index, len(candles)):
        window = closes[: index + 1]
        close = closes[index]
        fast = average(window[-params.fast_ema :])
        slow = average(window[-params.slow_ema :])
        latest_rsi = rsi(window[-15:], 14)

        should_enter = position_entry is None and fast > slow and latest_rsi < params.rsi_ceiling
        should_exit = position_entry is not None and (fast < slow or latest_rsi > params.rsi_ceiling + 6 or index == len(candles) - 1)

        if should_enter:
            position_entry = close
            position_size = balance * params.exposure
            continue

        if should_exit and position_entry is not None:
            gross_pnl = position_size * ((close - position_entry) / position_entry)
            fee = position_size * 0.001 * 2
            pnl = gross_pnl - fee
            balance += pnl
            trades.append(BacktestTrade(entry=position_entry, exit=close, pnl=round(pnl, 2), fee=round(fee, 4), slippage=0.0))
            position_entry = None
            position_size = 0.0
            peak_balance = max(peak_balance, balance)
            if peak_balance > 0:
                max_drawdown = max(max_drawdown, (peak_balance - balance) / peak_balance)
            equity_curve.append(balance)

    returns = [(equity_curve[index] - equity_curve[index - 1]) / equity_curve[index - 1] for index in range(1, len(equity_curve)) if equity_curve[index - 1]]
    winning_trades = sum(1 for trade in trades if trade.pnl > 0)
    gross_profit = sum(trade.pnl for trade in trades if trade.pnl > 0)
    gross_loss = abs(sum(trade.pnl for trade in trades if trade.pnl < 0))
    profit_factor = gross_profit / gross_loss if gross_loss else (gross_profit if gross_profit else 0.0)
    total_return = (balance - initial_balance) / initial_balance if initial_balance else 0.0
    metrics = WalkForwardMetrics(
        total_return=round(total_return, 6),
        ending_balance=round(balance, 2),
        win_rate=round(winning_trades / len(trades), 6) if trades else 0.0,
        max_drawdown=round(max_drawdown, 6),
        trades_count=len(trades),
        profit_factor=round(profit_factor, 6),
        sharpe_ratio=round(annualized_sharpe(returns), 6),
    )
    return metrics, trades


def aggregate_results(
    windows: int,
    cumulative_return: float,
    test_returns: list[float],
    validation_returns: list[float],
    trades: list[BacktestTrade],
    max_drawdown: float,
) -> WalkForwardAggregatedResult:
    winning_trades = sum(1 for trade in trades if trade.pnl > 0)
    gross_profit = sum(trade.pnl for trade in trades if trade.pnl > 0)
    gross_loss = abs(sum(trade.pnl for trade in trades if trade.pnl < 0))
    profit_factor = gross_profit / gross_loss if gross_loss else (gross_profit if gross_profit else 0.0)
    average_test = average(test_returns)
    average_validation = average(validation_returns)
    robustness = max(0.0, min(1.0, (average_test + 0.05) / 0.15))
    if average_validation > 0:
        robustness *= max(0.0, min(1.0, average_test / average_validation))
    if max_drawdown > 0.2:
        robustness *= 0.7
    return WalkForwardAggregatedResult(
        windows=windows,
        cumulative_return=round(cumulative_return, 6),
        average_test_return=round(average_test, 6),
        average_validation_return=round(average_validation, 6),
        average_win_rate=round(winning_trades / len(trades), 6) if trades else 0.0,
        max_drawdown=round(max_drawdown, 6),
        total_trades=len(trades),
        profit_factor=round(profit_factor, 6),
        sharpe_ratio=round(annualized_sharpe(test_returns), 6),
        robustness_score=round(robustness, 6),
    )


def walk_forward_to_schema(run: WalkForwardRun) -> WalkForwardRunRead:
    return WalkForwardRunRead(
        id=run.id,
        symbol=run.symbol_ref.symbol,
        strategy=run.strategy_ref.name if run.strategy_ref else None,
        strategy_id=run.strategy_id,
        timeframe=run.timeframe,
        training_period=run.training_period,
        validation_period=run.validation_period,
        test_period=run.test_period,
        rolling_windows=run.rolling_windows,
        initial_balance=run.initial_balance,
        optimization_results=run.optimization_results,
        out_of_sample_results=run.out_of_sample_results,
        window_metrics=run.window_metrics,
        aggregated_result=WalkForwardAggregatedResult.model_validate(run.aggregated_result),
        status=run.status,
        warning=run.warning,
        created_at=run.created_at,
    )


def optimization_score(metrics: WalkForwardMetrics) -> float:
    return metrics.total_return + (metrics.sharpe_ratio * 0.01) - (metrics.max_drawdown * 0.75)


def build_warning(result: WalkForwardAggregatedResult) -> str | None:
    if result.average_test_return < 0 or result.robustness_score < 0.35:
        return "Out-of-sample results are weak; avoid deployment until the strategy is more robust."
    if result.average_test_return < result.average_validation_return * 0.5:
        return "Out-of-sample performance is materially weaker than validation performance."
    return None


def average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0

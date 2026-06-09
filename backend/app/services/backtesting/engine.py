from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BacktestRun, MarketCandle
from app.schemas.trading import BacktestRunRequest
from app.services.audit import record_event
from app.services.indicators.technical import rsi
from app.services.repository import (
    ensure_default_risk_settings,
    ensure_default_strategy,
    get_symbol,
    list_candles,
    seed_defaults,
)


@dataclass
class BacktestTrade:
    entry: float
    exit: float
    pnl: float
    fee: float
    slippage: float


def run_backtest(db: Session, payload: BacktestRunRequest) -> BacktestRun:
    seed_defaults(db)
    symbol = get_symbol(db, payload.symbol)
    if symbol is None:
        raise ValueError(f"Symbol {payload.symbol.upper()} is not configured")

    strategy = ensure_default_strategy(db)
    risk_settings = ensure_default_risk_settings(db)
    candles = list_candles(db, symbol.symbol, payload.timeframe, payload.lookback)

    if len(candles) < 60:
        raise ValueError(f"At least 60 candles are required to backtest {symbol.symbol}")

    trades, ending_balance, max_drawdown, equity_curve = simulate_ema_rsi_strategy(
        candles=candles,
        initial_balance=payload.initial_balance,
        exposure=risk_settings.max_symbol_exposure,
        fee_rate=payload.fee_rate,
        slippage_rate=payload.slippage_rate,
        spread_rate=payload.spread_rate,
    )
    winning_trades = sum(1 for trade in trades if trade.pnl > 0)
    losing_trades = sum(1 for trade in trades if trade.pnl <= 0)
    win_rate = winning_trades / len(trades) if trades else 0.0
    total_return = (ending_balance - payload.initial_balance) / payload.initial_balance
    gross_profit = sum(trade.pnl for trade in trades if trade.pnl > 0)
    gross_loss = abs(sum(trade.pnl for trade in trades if trade.pnl < 0))
    profit_factor = gross_profit / gross_loss if gross_loss else (gross_profit if gross_profit else 0.0)
    returns = [
        (equity_curve[index]["equity"] - equity_curve[index - 1]["equity"]) / equity_curve[index - 1]["equity"]
        for index in range(1, len(equity_curve))
        if equity_curve[index - 1]["equity"]
    ]
    sharpe_ratio = annualized_sharpe(returns)
    fees = sum(trade.fee for trade in trades)
    slippage = sum(trade.slippage for trade in trades)
    summary = build_backtest_summary(symbol.symbol, total_return, len(trades), win_rate)

    run = BacktestRun(
        symbol_id=symbol.id,
        strategy_id=strategy.id,
        timeframe=payload.timeframe,
        initial_balance=round(payload.initial_balance, 2),
        ending_balance=round(ending_balance, 2),
        total_return=round(total_return, 6),
        win_rate=round(win_rate, 6),
        max_drawdown=round(max_drawdown, 6),
        fees=round(fees, 4),
        slippage=round(slippage, 4),
        spread=round(payload.spread_rate, 6),
        profit_factor=round(profit_factor, 6),
        sharpe_ratio=round(sharpe_ratio, 6),
        equity_curve=equity_curve,
        trades_count=len(trades),
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        status="completed",
        summary=summary,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    record_event(
        db,
        event_type="backtest.completed",
        entity_type="backtest",
        entity_id=run.id,
        severity="info",
        message=run.summary,
        metadata={
            "symbol": symbol.symbol,
            "timeframe": payload.timeframe,
            "total_return": run.total_return,
            "win_rate": run.win_rate,
            "trades_count": run.trades_count,
            "profit_factor": run.profit_factor,
            "sharpe_ratio": run.sharpe_ratio,
        },
        commit=True,
    )
    return run


def list_backtest_runs(db: Session, limit: int = 10) -> list[BacktestRun]:
    statement = select(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(limit)
    return list(db.scalars(statement).all())


def get_backtest_run(db: Session, run_id: int) -> BacktestRun | None:
    return db.get(BacktestRun, run_id)


def simulate_ema_rsi_strategy(
    candles: list[MarketCandle],
    initial_balance: float,
    exposure: float,
    fee_rate: float,
    slippage_rate: float,
    spread_rate: float,
) -> tuple[list[BacktestTrade], float, float, list[dict]]:
    balance = initial_balance
    peak_balance = initial_balance
    max_drawdown = 0.0
    position_entry: float | None = None
    position_size = 0.0
    trades: list[BacktestTrade] = []
    equity_curve: list[dict] = [{"timestamp": candles[0].opened_at.isoformat(), "equity": round(balance, 2)}]

    closes = [candle.close for candle in candles]

    for index in range(30, len(candles)):
        window = closes[: index + 1]
        close = closes[index]
        fast = average(window[-9:])
        slow = average(window[-21:])
        latest_rsi = rsi(window[-15:], 14)

        should_enter = position_entry is None and fast > slow and latest_rsi < 72
        should_exit = position_entry is not None and (fast < slow or latest_rsi > 78 or index == len(candles) - 1)

        if should_enter:
            position_entry = close * (1 + slippage_rate + spread_rate)
            position_size = balance * min(max(exposure, 0.01), 1.0)
            continue

        if should_exit and position_entry is not None:
            exit_price = close * (1 - slippage_rate - spread_rate)
            gross_pnl = position_size * ((exit_price - position_entry) / position_entry)
            fee = position_size * fee_rate * 2
            slippage_cost = position_size * slippage_rate * 2
            pnl = gross_pnl - fee
            balance += pnl
            trades.append(BacktestTrade(entry=position_entry, exit=exit_price, pnl=round(pnl, 2), fee=round(fee, 4), slippage=round(slippage_cost, 4)))
            position_entry = None
            position_size = 0.0
            peak_balance = max(peak_balance, balance)
            if peak_balance > 0:
                max_drawdown = max(max_drawdown, (peak_balance - balance) / peak_balance)
            equity_curve.append({"timestamp": candles[index].opened_at.isoformat(), "equity": round(balance, 2), "pnl": round(pnl, 2)})

    if len(equity_curve) == 1:
        equity_curve.append({"timestamp": candles[-1].opened_at.isoformat(), "equity": round(balance, 2), "pnl": 0.0})

    return trades, balance, max_drawdown, equity_curve


def average(values: list[float]) -> float:
    return sum(values) / len(values)


def annualized_sharpe(returns: list[float]) -> float:
    if len(returns) < 2:
        return 0.0
    mean = average(returns)
    variance = sum((value - mean) ** 2 for value in returns) / (len(returns) - 1)
    std_dev = variance ** 0.5
    return 0.0 if std_dev == 0 else (mean / std_dev) * (252 ** 0.5)


def build_backtest_summary(symbol: str, total_return: float, trades_count: int, win_rate: float) -> str:
    direction = "gain" if total_return >= 0 else "loss"
    return (
        f"{symbol} backtest completed with {trades_count} trades, "
        f"{abs(total_return) * 100:.2f}% {direction}, and {win_rate * 100:.1f}% win rate."
    )

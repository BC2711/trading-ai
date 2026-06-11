from collections import defaultdict
from math import sqrt
from statistics import mean, stdev

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BacktestRun, PaperPosition, Signal, Strategy
from app.schemas.analytics import (
    AnalyticsEquityCurveResponse,
    AnalyticsEquityPoint,
    AnalyticsTradeRead,
    PerformanceSummaryResponse,
    StrategyComparisonRead,
    StrategyComparisonResponse,
)
from app.services.execution.paper import PAPER_EQUITY


def get_performance_summary(db: Session) -> PerformanceSummaryResponse:
    trades = get_analytics_trades(db)
    values = [trade.realized_pnl for trade in trades]
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    total = len(trades)
    gross_profit = sum(wins)
    gross_loss = sum(losses)

    best_trade = max(trades, key=lambda trade: trade.realized_pnl) if trades else None
    worst_trade = min(trades, key=lambda trade: trade.realized_pnl) if trades else None

    return PerformanceSummaryResponse(
        win_rate=round(len(wins) / total, 6) if total else 0.0,
        loss_rate=round(len(losses) / total, 6) if total else 0.0,
        average_win=round(mean(wins), 4) if wins else 0.0,
        average_loss=round(abs(mean(losses)), 4) if losses else 0.0,
        profit_factor=round(_profit_factor(gross_profit, gross_loss), 6),
        sharpe_ratio=round(_sharpe_ratio(values), 6),
        max_drawdown=get_equity_curve(db).max_drawdown,
        total_trades=total,
        winning_trades=len(wins),
        losing_trades=len(losses),
        best_trade=best_trade,
        worst_trade=worst_trade,
        net_pnl=round(sum(values), 4),
        gross_profit=round(gross_profit, 4),
        gross_loss=round(abs(gross_loss), 4),
    )


def get_equity_curve(db: Session) -> AnalyticsEquityCurveResponse:
    running_pnl = 0.0
    peak_equity = PAPER_EQUITY
    max_drawdown = 0.0
    points: list[AnalyticsEquityPoint] = []

    for trade in get_analytics_trades(db):
        running_pnl += trade.realized_pnl
        equity = PAPER_EQUITY + running_pnl
        peak_equity = max(peak_equity, equity)
        drawdown = (peak_equity - equity) / peak_equity if peak_equity else 0.0
        max_drawdown = max(max_drawdown, drawdown)
        points.append(
            AnalyticsEquityPoint(
                timestamp=trade.closed_at,
                equity=round(equity, 4),
                realized_pnl=round(running_pnl, 4),
                drawdown=round(drawdown, 6),
                event=f"closed {trade.symbol} {trade.side}",
            )
        )

    ending_equity = points[-1].equity if points else PAPER_EQUITY
    return AnalyticsEquityCurveResponse(
        starting_equity=PAPER_EQUITY,
        ending_equity=round(ending_equity, 4),
        max_drawdown=round(max_drawdown, 6),
        points=points,
    )


def get_strategy_comparison(db: Session) -> StrategyComparisonResponse:
    backtest_rows = _strategy_comparison_from_backtests(db)
    if backtest_rows:
        return StrategyComparisonResponse(strategies=backtest_rows)
    return StrategyComparisonResponse(strategies=_strategy_comparison_from_signals(db))


def get_analytics_trades(db: Session, limit: int | None = None) -> list[AnalyticsTradeRead]:
    statement = (
        select(PaperPosition)
        .where(PaperPosition.status == "closed", PaperPosition.closed_at.is_not(None))
        .order_by(PaperPosition.closed_at)
    )
    if limit is not None:
        statement = statement.limit(limit)
    return [position_to_trade(position) for position in db.scalars(statement).all()]


def position_to_trade(position: PaperPosition) -> AnalyticsTradeRead:
    notional = abs(position.quantity * position.avg_entry_price)
    return AnalyticsTradeRead(
        id=position.id,
        symbol=position.symbol_ref.symbol,
        strategy=None,
        side=position.side,
        quantity=position.quantity,
        entry_price=position.avg_entry_price,
        exit_price=position.mark_price,
        realized_pnl=round(position.realized_pnl, 4),
        return_pct=round(position.realized_pnl / notional, 6) if notional else 0.0,
        opened_at=position.created_at,
        closed_at=position.closed_at or position.updated_at,
        outcome="win" if position.realized_pnl > 0 else "loss" if position.realized_pnl < 0 else "flat",
    )


def _strategy_comparison_from_backtests(db: Session) -> list[StrategyComparisonRead]:
    runs = list(db.scalars(select(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(100)).all())
    grouped: dict[str, list[BacktestRun]] = defaultdict(list)
    for run in runs:
        name = run.strategy_ref.name if run.strategy_ref else "Default Strategy"
        grouped[name].append(run)

    rows: list[StrategyComparisonRead] = []
    for strategy_name, strategy_runs in grouped.items():
        latest = strategy_runs[0]
        total_trades = sum(run.trades_count for run in strategy_runs)
        rows.append(
            StrategyComparisonRead(
                id=f"backtest-{latest.strategy_id or 'default'}",
                strategy_id=latest.strategy_id,
                strategy=strategy_name,
                total_trades=total_trades,
                win_rate=round(mean([run.win_rate for run in strategy_runs]), 6),
                total_return=round(mean([run.total_return for run in strategy_runs]), 6),
                profit_factor=round(mean([run.profit_factor for run in strategy_runs]), 6),
                sharpe_ratio=round(mean([run.sharpe_ratio for run in strategy_runs]), 6),
                max_drawdown=round(max(run.max_drawdown for run in strategy_runs), 6),
                best_trade=None,
                worst_trade=None,
                source="backtest",
            )
        )
    return sorted(rows, key=lambda item: (item.total_return, item.profit_factor), reverse=True)


def _strategy_comparison_from_signals(db: Session) -> list[StrategyComparisonRead]:
    strategies = list(db.scalars(select(Strategy).order_by(Strategy.name)).all())
    rows: list[StrategyComparisonRead] = []
    for strategy in strategies:
        signals = list(db.scalars(select(Signal).where(Signal.strategy_id == strategy.id)).all())
        actionable = [signal for signal in signals if signal.direction in {"buy", "sell"}]
        rows.append(
            StrategyComparisonRead(
                id=f"signals-{strategy.id}",
                strategy_id=strategy.id,
                strategy=strategy.name,
                total_trades=len(actionable),
                win_rate=0.0,
                total_return=0.0,
                profit_factor=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                best_trade=None,
                worst_trade=None,
                source="signals",
            )
        )
    return rows


def _profit_factor(gross_profit: float, gross_loss: float) -> float:
    if gross_loss < 0:
        return gross_profit / abs(gross_loss)
    return gross_profit if gross_profit > 0 else 0.0


def _sharpe_ratio(pnl_values: list[float]) -> float:
    if len(pnl_values) < 2:
        return 0.0
    returns = [value / PAPER_EQUITY for value in pnl_values]
    volatility = stdev(returns)
    if volatility == 0:
        return 0.0
    return (mean(returns) / volatility) * sqrt(len(returns))

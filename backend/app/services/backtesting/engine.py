from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BacktestRun, MarketCandle
from app.schemas.trading import BacktestRunRequest
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

    trades, ending_balance, max_drawdown = simulate_ema_rsi_strategy(
        candles=candles,
        initial_balance=payload.initial_balance,
        exposure=risk_settings.max_symbol_exposure,
    )
    winning_trades = sum(1 for trade in trades if trade.pnl > 0)
    losing_trades = sum(1 for trade in trades if trade.pnl <= 0)
    win_rate = winning_trades / len(trades) if trades else 0.0
    total_return = (ending_balance - payload.initial_balance) / payload.initial_balance
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
        trades_count=len(trades),
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        status="completed",
        summary=summary,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def list_backtest_runs(db: Session, limit: int = 10) -> list[BacktestRun]:
    statement = select(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(limit)
    return list(db.scalars(statement).all())


def simulate_ema_rsi_strategy(
    candles: list[MarketCandle],
    initial_balance: float,
    exposure: float,
) -> tuple[list[BacktestTrade], float, float]:
    balance = initial_balance
    peak_balance = initial_balance
    max_drawdown = 0.0
    position_entry: float | None = None
    position_size = 0.0
    trades: list[BacktestTrade] = []

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
            position_entry = close
            position_size = balance * min(max(exposure, 0.01), 1.0)
            continue

        if should_exit and position_entry is not None:
            pnl = position_size * ((close - position_entry) / position_entry)
            balance += pnl
            trades.append(BacktestTrade(entry=position_entry, exit=close, pnl=round(pnl, 2)))
            position_entry = None
            position_size = 0.0
            peak_balance = max(peak_balance, balance)
            if peak_balance > 0:
                max_drawdown = max(max_drawdown, (peak_balance - balance) / peak_balance)

    return trades, balance, max_drawdown


def average(values: list[float]) -> float:
    return sum(values) / len(values)


def build_backtest_summary(symbol: str, total_return: float, trades_count: int, win_rate: float) -> str:
    direction = "gain" if total_return >= 0 else "loss"
    return (
        f"{symbol} backtest completed with {trades_count} trades, "
        f"{abs(total_return) * 100:.2f}% {direction}, and {win_rate * 100:.1f}% win rate."
    )

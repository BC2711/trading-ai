from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MarketCandle, Signal
from app.services.indicators.technical import indicator_snapshot
from app.services.repository import ensure_default_strategy, get_symbol, list_candles, seed_defaults


def list_signals(db: Session) -> list[Signal]:
    seed_defaults(db)
    signals = db.scalars(select(Signal).where(Signal.status == "active").order_by(Signal.created_at.desc()).limit(50)).all()

    if not signals:
        return generate_signals(db)

    return list(signals)


def generate_signals(db: Session, symbol: str | None = None, timeframe: str = "15m") -> list[Signal]:
    seed_defaults(db)
    strategy = ensure_default_strategy(db)
    symbols = [get_symbol(db, symbol)] if symbol else [candle_symbol for candle_symbol in _symbols_with_candles(db, timeframe)]

    for symbol_model in symbols:
        if not symbol_model:
            continue

        candles = list_candles(db, symbol_model.symbol, timeframe=timeframe, limit=240)
        if len(candles) < 30:
            continue

        signal = build_signal_from_candles(candles)
        db.add(
            Signal(
                symbol_id=symbol_model.id,
                strategy_id=strategy.id,
                direction=signal["direction"],
                confidence=signal["confidence"],
                timeframe=timeframe,
                reason=signal["reason"],
                status="active",
            )
        )

    db.commit()
    return list(db.scalars(select(Signal).where(Signal.status == "active").order_by(Signal.created_at.desc()).limit(50)).all())


def build_signal_from_candles(candles: list[MarketCandle]) -> dict[str, str | float]:
    closes = [candle.close for candle in candles]
    highs = [candle.high for candle in candles]
    lows = [candle.low for candle in candles]
    snapshot = indicator_snapshot(closes, highs, lows)
    close = snapshot["close"]
    ema_9 = snapshot["ema_9"]
    ema_21 = snapshot["ema_21"]
    ema_200 = snapshot["ema_200"]
    rsi_14 = snapshot["rsi_14"]

    bullish = ema_9 > ema_21 and close > ema_200 and 45 <= rsi_14 <= 70
    bearish = ema_9 < ema_21 and close < ema_200 and 30 <= rsi_14 <= 55

    if bullish:
        direction = "buy"
        confidence = 0.7 + min(0.18, abs(ema_9 - ema_21) / close)
        reason = f"EMA 9 above EMA 21, RSI {rsi_14:.1f}, price above EMA 200."
    elif bearish:
        direction = "sell"
        confidence = 0.7 + min(0.18, abs(ema_9 - ema_21) / close)
        reason = f"EMA 9 below EMA 21, RSI {rsi_14:.1f}, price below EMA 200."
    else:
        direction = "watch"
        confidence = 0.55 + min(0.14, abs(ema_9 - ema_21) / close)
        reason = f"Mixed setup: EMA 9 {ema_9:.2f}, EMA 21 {ema_21:.2f}, RSI {rsi_14:.1f}."

    return {
        "direction": direction,
        "confidence": round(float(min(confidence, 0.92)), 4),
        "reason": reason,
    }


def _symbols_with_candles(db: Session, timeframe: str):
    from app.models import Symbol

    statement = (
        select(Symbol)
        .join(MarketCandle, MarketCandle.symbol_id == Symbol.id)
        .where(MarketCandle.timeframe == timeframe)
        .distinct()
        .order_by(Symbol.symbol)
    )
    return db.scalars(statement).all()

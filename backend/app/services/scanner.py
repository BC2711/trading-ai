from datetime import datetime, timezone

import pandas as pd
from sqlalchemy.orm import Session

from app.models import MarketCandle
from app.schemas.scanner import ScannerRead
from app.services.indicators.technical import indicator_snapshot
from app.services.repository import get_symbol, list_candles, list_symbols, seed_defaults


def get_scanner_results(
    db: Session,
    symbols: list[str] | None = None,
    timeframe: str = "15m",
    lookback: int = 240,
) -> list[ScannerRead]:
    return run_scanner(db, symbols=symbols, timeframe=timeframe, lookback=lookback)


def run_scanner(
    db: Session,
    symbols: list[str] | None = None,
    timeframe: str = "15m",
    lookback: int = 240,
) -> list[ScannerRead]:
    seed_defaults(db)
    scan_time = datetime.now(timezone.utc)
    symbol_values = _scanner_symbols(db, symbols)
    results: list[ScannerRead] = []

    for symbol in symbol_values:
        candles = list_candles(db, symbol, timeframe=timeframe, limit=lookback)
        if len(candles) < 30:
            continue
        results.append(_scan_symbol(symbol, candles, scan_time))

    return sorted(results, key=lambda item: (item.signal == "hold", -item.confidence, item.symbol))


def scanner_signals(
    db: Session,
    min_confidence: float = 0.6,
    timeframe: str = "15m",
) -> list[ScannerRead]:
    results = run_scanner(db, timeframe=timeframe)
    return [
        result
        for result in results
        if result.signal in {"buy", "sell"} and result.confidence >= min_confidence
    ]


def _scanner_symbols(db: Session, symbols: list[str] | None) -> list[str]:
    if symbols:
        return [symbol.upper() for symbol in symbols if get_symbol(db, symbol)]
    return [symbol.symbol for symbol in list_symbols(db)]


def _scan_symbol(symbol: str, candles: list[MarketCandle], created_at: datetime) -> ScannerRead:
    closes = [candle.close for candle in candles]
    highs = [candle.high for candle in candles]
    lows = [candle.low for candle in candles]
    snapshot = indicator_snapshot(closes, highs, lows)
    macd = _macd_snapshot(closes)
    volatility = _volatility(closes, snapshot["atr_14"])
    trend_direction = _trend_direction(snapshot["ema_9"], snapshot["ema_21"], snapshot["ema_200"], closes)
    macd_signal = _macd_signal(macd["macd"], macd["signal"], macd["histogram"])
    risk_level = _risk_level(volatility, snapshot["rsi_14"])
    signal = _scanner_signal(trend_direction, macd_signal, snapshot["rsi_14"])
    confidence = _confidence(signal, trend_direction, macd_signal, snapshot["rsi_14"], volatility)

    return ScannerRead(
        symbol=symbol,
        current_price=snapshot["close"],
        signal=signal,
        confidence=confidence,
        risk_level=risk_level,
        rsi=round(snapshot["rsi_14"], 2),
        macd_signal=macd_signal,
        trend_direction=trend_direction,
        volatility=round(volatility, 4),
        recommended_action=_recommended_action(signal, confidence, risk_level),
        created_at=created_at,
    )


def _macd_snapshot(closes: list[float]) -> dict[str, float]:
    series = pd.Series(closes, dtype="float64")
    macd_line = series.ewm(span=12, adjust=False).mean() - series.ewm(span=26, adjust=False).mean()
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    return {
        "macd": round(float(macd_line.iloc[-1]), 6),
        "signal": round(float(signal_line.iloc[-1]), 6),
        "histogram": round(float(histogram.iloc[-1]), 6),
    }


def _macd_signal(macd: float, signal: float, histogram: float) -> str:
    if macd > signal and histogram > 0:
        return "bullish"
    if macd < signal and histogram < 0:
        return "bearish"
    return "neutral"


def _trend_direction(ema_9: float, ema_21: float, ema_200: float, closes: list[float]) -> str:
    latest = closes[-1]
    previous = closes[-8] if len(closes) >= 8 else closes[0]
    slope = (latest - previous) / max(abs(previous), 1)
    if ema_9 > ema_21 and latest >= ema_200 and slope > -0.002:
        return "uptrend"
    if ema_9 < ema_21 and latest <= ema_200 and slope < 0.002:
        return "downtrend"
    return "sideways"


def _volatility(closes: list[float], atr_14: float) -> float:
    latest = closes[-1]
    atr_volatility = atr_14 / max(abs(latest), 1)
    returns = pd.Series(closes, dtype="float64").pct_change().dropna()
    realized = float(returns.tail(30).std()) if len(returns) >= 2 else 0.0
    return max(atr_volatility, realized)


def _risk_level(volatility: float, rsi_14: float) -> str:
    if volatility >= 0.035 or rsi_14 >= 76 or rsi_14 <= 24:
        return "high"
    if volatility >= 0.018 or rsi_14 >= 70 or rsi_14 <= 30:
        return "medium"
    return "low"


def _scanner_signal(trend_direction: str, macd_signal: str, rsi_14: float) -> str:
    if trend_direction == "uptrend" and macd_signal == "bullish" and 38 <= rsi_14 <= 72:
        return "buy"
    if trend_direction == "downtrend" and macd_signal == "bearish" and 28 <= rsi_14 <= 62:
        return "sell"
    return "hold"


def _confidence(signal: str, trend_direction: str, macd_signal: str, rsi_14: float, volatility: float) -> float:
    score = 0.5
    if signal == "buy" and trend_direction == "uptrend":
        score += 0.18
    if signal == "sell" and trend_direction == "downtrend":
        score += 0.18
    if macd_signal in {"bullish", "bearish"}:
        score += 0.1
    if 42 <= rsi_14 <= 64:
        score += 0.08
    elif 30 <= rsi_14 <= 72:
        score += 0.04
    if volatility <= 0.02:
        score += 0.06
    elif volatility >= 0.04:
        score -= 0.08
    if signal == "hold":
        score = min(score, 0.64)
    return round(max(0.35, min(score, 0.94)), 4)


def _recommended_action(signal: str, confidence: float, risk_level: str) -> str:
    if risk_level == "high":
        return "Wait for risk to normalize"
    if signal == "buy" and confidence >= 0.7:
        return "Consider long setup"
    if signal == "sell" and confidence >= 0.7:
        return "Consider short setup"
    if signal in {"buy", "sell"}:
        return "Watch for confirmation"
    return "Hold and monitor"

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AIAnalysisRecord, BacktestRun, Signal
from app.schemas.trading import AIAnalysisRequest, AIAnalysisResponse
from app.services.audit import record_event
from app.services.indicators.technical import indicator_snapshot
from app.services.repository import ensure_default_risk_settings, ensure_default_strategy, list_candles, seed_defaults
from app.services.signals import build_signal_from_candles, generate_signals


def analyze_signal(db: Session, payload: AIAnalysisRequest) -> AIAnalysisResponse:
    seed_defaults(db)
    signal = resolve_signal(db, payload)
    symbol = signal.symbol_ref.symbol if signal else payload.symbol.upper()
    timeframe = signal.timeframe if signal else payload.timeframe
    candles = list_candles(db, symbol, timeframe, payload.lookback)

    if len(candles) < 30:
        raise ValueError(f"At least 30 candles are required to analyze {symbol}")

    snapshot = indicator_snapshot(
        closes=[candle.close for candle in candles],
        highs=[candle.high for candle in candles],
        lows=[candle.low for candle in candles],
    )
    derived_signal = build_signal_from_candles(candles)
    strategy = ensure_default_strategy(db)
    risk_settings = ensure_default_risk_settings(db)
    latest_backtest = get_latest_backtest(db, symbol, timeframe)

    direction = signal.direction if signal else str(derived_signal["direction"])
    confidence = signal.confidence if signal else float(derived_signal["confidence"])
    reason = signal.reason if signal else str(derived_signal["reason"])
    reasoning = build_reasoning(direction, confidence, reason, snapshot, strategy.name)
    risk_notes = build_risk_notes(direction, confidence, snapshot, risk_settings)
    backtest_summary = latest_backtest.summary if latest_backtest else None

    record = AIAnalysisRecord(
        signal_id=signal.id if signal else None,
        provider="rules-fallback",
        symbol=symbol,
        timeframe=timeframe,
        direction=direction,
        confidence=round(confidence, 4),
        explanation=build_explanation(symbol, direction, confidence, reason, snapshot, backtest_summary),
        reasoning=reasoning,
        risk_notes=risk_notes,
        suggested_action=build_suggested_action(direction, confidence, risk_notes),
        indicators={key: round(value, 4) for key, value in snapshot.items()},
        backtest_summary=backtest_summary,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    record_event(
        db,
        event_type="ai.analysis.generated",
        entity_type="ai_analysis",
        entity_id=record.id,
        severity="info",
        message=f"Generated AI analysis for {record.symbol} {record.direction.upper()} at {record.confidence * 100:.1f}% confidence.",
        metadata={"symbol": record.symbol, "timeframe": record.timeframe, "direction": record.direction, "signal_id": record.signal_id},
        commit=True,
    )
    return analysis_to_response(record)


def list_ai_analyses(db: Session, limit: int = 10) -> list[AIAnalysisRecord]:
    statement = select(AIAnalysisRecord).order_by(AIAnalysisRecord.created_at.desc()).limit(limit)
    return list(db.scalars(statement).all())


def get_ai_analysis(db: Session, analysis_id: int) -> AIAnalysisRecord | None:
    return db.get(AIAnalysisRecord, analysis_id)


def analysis_to_response(record: AIAnalysisRecord) -> AIAnalysisResponse:
    return AIAnalysisResponse(
        id=record.id,
        signal_id=record.signal_id,
        provider=record.provider,
        symbol=record.symbol,
        timeframe=record.timeframe,
        direction=record.direction,
        confidence=record.confidence,
        explanation=record.explanation,
        reasoning=record.reasoning,
        risk_notes=record.risk_notes,
        suggested_action=record.suggested_action,
        indicators=record.indicators,
        backtest_summary=record.backtest_summary,
        generated_at=record.created_at,
    )


def resolve_signal(db: Session, payload: AIAnalysisRequest) -> Signal | None:
    if payload.signal_id is not None:
        return db.get(Signal, payload.signal_id)

    statement = (
        select(Signal)
        .join(Signal.symbol_ref)
        .where(Signal.timeframe == payload.timeframe, Signal.status == "active")
        .order_by(Signal.created_at.desc())
    )
    signals = db.scalars(statement).all()
    for signal in signals:
        if signal.symbol_ref.symbol == payload.symbol.upper():
            return signal

    generated = generate_signals(db, payload.symbol, payload.timeframe)
    for signal in generated:
        if signal.symbol_ref.symbol == payload.symbol.upper() and signal.timeframe == payload.timeframe:
            return signal
    return None


def get_latest_backtest(db: Session, symbol: str, timeframe: str) -> BacktestRun | None:
    statement = (
        select(BacktestRun)
        .join(BacktestRun.symbol_ref)
        .where(BacktestRun.timeframe == timeframe)
        .order_by(BacktestRun.created_at.desc())
    )
    for run in db.scalars(statement).all():
        if run.symbol_ref.symbol == symbol:
            return run
    return None


def build_reasoning(direction: str, confidence: float, reason: str, indicators: dict[str, float], strategy_name: str) -> list[str]:
    return [
        f"{strategy_name} classified the setup as {direction.upper()} with {confidence * 100:.1f}% confidence.",
        reason,
        f"Price is {indicators['close']:.2f}, EMA 9 is {indicators['ema_9']:.2f}, EMA 21 is {indicators['ema_21']:.2f}, and RSI 14 is {indicators['rsi_14']:.1f}.",
        f"ATR 14 is {indicators['atr_14']:.2f}, which helps frame near-term volatility and stop distance.",
    ]


def build_risk_notes(direction: str, confidence: float, indicators: dict[str, float], risk_settings) -> list[str]:
    notes = [
        f"Risk per trade is capped at {risk_settings.max_risk_per_trade * 100:.1f}% with {risk_settings.max_open_trades} max open trades.",
        f"Symbol exposure limit is {risk_settings.max_symbol_exposure * 100:.1f}% and daily loss limit is {risk_settings.max_daily_loss * 100:.1f}%.",
    ]

    if direction == "watch":
        notes.append("Signal is observational; wait for clearer trend confirmation before adding exposure.")
    if confidence < 0.65:
        notes.append("Confidence is moderate, so position size should stay below normal deployment size.")
    if indicators["rsi_14"] > 72:
        notes.append("RSI is elevated; avoid chasing a late long entry without a pullback.")
    if indicators["rsi_14"] < 30:
        notes.append("RSI is compressed; short entries may be vulnerable to a relief bounce.")

    return notes


def build_explanation(
    symbol: str,
    direction: str,
    confidence: float,
    reason: str,
    indicators: dict[str, float],
    backtest_summary: str | None,
) -> str:
    bias = "bullish" if direction == "buy" else "bearish" if direction == "sell" else "neutral"
    explanation = (
        f"{symbol} currently has a {bias} {direction.upper()} read with {confidence * 100:.1f}% confidence. "
        f"The main driver is: {reason} The latest close is {indicators['close']:.2f}, with RSI at {indicators['rsi_14']:.1f}."
    )
    if backtest_summary:
        explanation = f"{explanation} Latest backtest context: {backtest_summary}"
    return explanation


def build_suggested_action(direction: str, confidence: float, risk_notes: list[str]) -> str:
    if direction == "buy" and confidence >= 0.7:
        return "Consider a staged long entry within configured risk limits."
    if direction == "sell" and confidence >= 0.7:
        return "Consider reducing long exposure or testing a staged short setup within configured risk limits."
    if any("moderate" in note for note in risk_notes):
        return "Keep this on watch and require confirmation before execution."
    return "Monitor the setup and wait for stronger confirmation."

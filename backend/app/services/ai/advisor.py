from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AIAnalysisRecord, BacktestRun, Signal, Symbol
from app.schemas.trading import AIAnalysisRequest, AIAnalysisResponse
from app.services.ai.provider import get_ai_provider
from app.services.audit import record_event
from app.services.repository import ensure_default_risk_settings, ensure_default_strategy, list_candles, seed_defaults
from app.services.signals import generate_signals


def analyze_signal(db: Session, payload: AIAnalysisRequest) -> AIAnalysisResponse:
    seed_defaults(db)
    signal = resolve_signal(db, payload)
    symbol = signal.symbol_ref.symbol if signal else payload.symbol.upper()
    timeframe = signal.timeframe if signal else payload.timeframe
    candles = list_candles(db, symbol, timeframe, payload.lookback)

    if len(candles) < 30:
        raise ValueError(f"At least 30 candles are required to analyze {symbol}")

    strategy = ensure_default_strategy(db)
    risk_settings = ensure_default_risk_settings(db)
    latest_backtest = get_latest_backtest(db, symbol, timeframe)
    ai_provider = get_ai_provider()
    analysis = ai_provider.analyze(payload, signal, candles, strategy, risk_settings, latest_backtest)

    record = AIAnalysisRecord(
        signal_id=signal.id if signal else None,
        provider=analysis.provider,
        symbol=analysis.symbol,
        timeframe=analysis.timeframe,
        direction=analysis.direction,
        confidence=analysis.confidence,
        explanation=analysis.explanation,
        reasoning=analysis.reasoning,
        risk_notes=analysis.risk_notes,
        suggested_action=analysis.suggested_action,
        indicators=analysis.indicators,
        backtest_summary=analysis.backtest_summary,
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
        .where(
            Signal.timeframe == payload.timeframe,
            Signal.status == "active",
            Symbol.symbol == payload.symbol.upper()
        )
        .order_by(Signal.created_at.desc())
    )
    signal = db.scalars(statement).first()
    if signal:
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
        .where(
            BacktestRun.timeframe == timeframe,
            Symbol.symbol == symbol.upper()
        )
        .order_by(BacktestRun.created_at.desc())
    )
    return db.scalars(statement).first()

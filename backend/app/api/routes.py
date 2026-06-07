from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.models import MarketCandle, Signal
from app.schemas.trading import (
    AIAnalysisRequest,
    AIAnalysisResponse,
    BacktestRunRead,
    BacktestRunRequest,
    MarketCandleRead,
    MarketDataRefreshRequest,
    MarketDataRefreshResponse,
    MarketDataScheduleResponse,
    MarketDataSyncRequest,
    MarketDataSyncResponse,
    MarketDataTaskResponse,
    PaperOrderRead,
    PaperOrderRequest,
    PaperPositionRead,
    RiskSettingRead,
    RiskSettingUpdate,
    SignalGenerateRequest,
    SignalRead,
    StrategyRead,
    StrategyUpdate,
    SymbolCreate,
    SymbolRead,
)
from app.core.config import settings
from app.services.indicators.technical import moving_average_snapshot
from app.services.repository import (
    create_symbol,
    ensure_default_risk_settings,
    ensure_default_strategy,
    list_candles,
    list_symbols,
    update_risk_settings,
    update_strategy,
)
from app.services.market_data.binance import MarketDataProviderError
from app.services.market_data.jobs import run_market_data_refresh
from app.services.market_data.sync import sync_market_data
from app.services.ai.advisor import analyze_signal, analysis_to_response, get_ai_analysis, list_ai_analyses
from app.services.backtesting.engine import list_backtest_runs, run_backtest
from app.services.execution.paper import (
    create_paper_order,
    list_paper_orders,
    list_paper_positions,
    order_to_schema,
    position_to_schema,
)
from app.services.signals import generate_signals, list_signals
from app.workers.tasks import refresh_market_data

router = APIRouter()


@router.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "trading-ai-backend"}


@router.get("/symbols", response_model=list[SymbolRead], tags=["symbols"])
def get_symbols(db: Session = Depends(get_db)) -> list[SymbolRead]:
    return [SymbolRead.model_validate(symbol) for symbol in list_symbols(db)]


@router.post("/symbols", response_model=SymbolRead, tags=["symbols"])
def post_symbol(payload: SymbolCreate, db: Session = Depends(get_db)) -> SymbolRead:
    return SymbolRead.model_validate(create_symbol(db, payload))


@router.get("/candles", response_model=list[MarketCandleRead], tags=["market-data"])
def get_candles(
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("15m"),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[MarketCandleRead]:
    return [market_candle_to_schema(candle) for candle in list_candles(db, symbol, timeframe, limit)]


@router.post("/market-data/sync", response_model=MarketDataSyncResponse, tags=["market-data"])
def post_market_data_sync(
    payload: MarketDataSyncRequest,
    db: Session = Depends(get_db),
) -> MarketDataSyncResponse:
    try:
        results = sync_market_data(db, payload.symbols, payload.timeframe, payload.limit)
    except MarketDataProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    signals = generate_signals(db, timeframe=payload.timeframe) if payload.regenerate_signals else []

    return MarketDataSyncResponse(
        provider="binance",
        timeframe=payload.timeframe,
        results=results,
        signals=[signal_to_schema(signal) for signal in signals],
    )


@router.post("/market-data/refresh", response_model=MarketDataRefreshResponse, tags=["market-data"])
def post_market_data_refresh(
    payload: MarketDataRefreshRequest | None = None,
    db: Session = Depends(get_db),
) -> MarketDataRefreshResponse:
    payload = payload or MarketDataRefreshRequest()
    return run_market_data_refresh(
        db,
        symbols=payload.symbols,
        timeframe=payload.timeframe,
        limit=payload.limit,
        regenerate_signals=payload.regenerate_signals,
    )


@router.post("/market-data/refresh-task", response_model=MarketDataTaskResponse, tags=["market-data"])
def post_market_data_refresh_task(payload: MarketDataRefreshRequest | None = None) -> MarketDataTaskResponse:
    payload = payload or MarketDataRefreshRequest()
    task = refresh_market_data.delay(
        symbols=payload.symbols,
        timeframe=payload.timeframe,
        limit=payload.limit,
        regenerate_signals=payload.regenerate_signals,
    )
    return MarketDataTaskResponse(task_id=task.id, status="queued")


@router.get("/market-data/schedule", response_model=MarketDataScheduleResponse, tags=["market-data"])
def get_market_data_schedule() -> MarketDataScheduleResponse:
    return MarketDataScheduleResponse(
        enabled=True,
        job_id="market-data-sync",
        interval_minutes=settings.market_sync_interval_minutes,
        symbols=settings.market_sync_symbols,
        timeframe=settings.market_sync_timeframe,
        limit=settings.market_sync_limit,
        regenerate_signals=settings.market_sync_regenerate_signals,
    )


@router.get("/signals", response_model=list[SignalRead], tags=["signals"])
def get_signals(db: Session = Depends(get_db)) -> list[SignalRead]:
    return [signal_to_schema(signal) for signal in list_signals(db)]


@router.post("/signals/generate", response_model=list[SignalRead], tags=["signals"])
def post_generate_signals(
    payload: SignalGenerateRequest | None = None,
    db: Session = Depends(get_db),
) -> list[SignalRead]:
    payload = payload or SignalGenerateRequest()
    return [signal_to_schema(signal) for signal in generate_signals(db, payload.symbol, payload.timeframe)]


@router.get("/strategies", response_model=list[StrategyRead], tags=["strategies"])
def get_strategies(db: Session = Depends(get_db)) -> list[StrategyRead]:
    return [StrategyRead.model_validate(ensure_default_strategy(db))]


@router.patch("/strategies/{strategy_id}", response_model=StrategyRead, tags=["strategies"])
def patch_strategy(
    strategy_id: int,
    payload: StrategyUpdate,
    db: Session = Depends(get_db),
) -> StrategyRead:
    strategy = update_strategy(db, strategy_id, payload)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")

    return StrategyRead.model_validate(strategy)


@router.get("/risk-settings", response_model=list[RiskSettingRead], tags=["risk"])
def get_risk_settings(db: Session = Depends(get_db)) -> list[RiskSettingRead]:
    return [RiskSettingRead.model_validate(ensure_default_risk_settings(db))]


@router.patch("/risk-settings/{risk_setting_id}", response_model=RiskSettingRead, tags=["risk"])
def patch_risk_settings(
    risk_setting_id: int,
    payload: RiskSettingUpdate,
    db: Session = Depends(get_db),
) -> RiskSettingRead:
    settings = update_risk_settings(db, risk_setting_id, payload)
    if settings is None:
        raise HTTPException(status_code=404, detail="Risk settings not found")

    return RiskSettingRead.model_validate(settings)


@router.get("/backtests", response_model=list[BacktestRunRead], tags=["backtests"])
def get_backtests(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[BacktestRunRead]:
    return [backtest_to_schema(run) for run in list_backtest_runs(db, limit)]


@router.post("/backtests/run", response_model=BacktestRunRead, tags=["backtests"])
def post_backtest_run(
    payload: BacktestRunRequest,
    db: Session = Depends(get_db),
) -> BacktestRunRead:
    try:
        run = run_backtest(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return backtest_to_schema(run)


@router.post("/ai/analyze-signal", response_model=AIAnalysisResponse, tags=["ai"])
def post_ai_analyze_signal(
    payload: AIAnalysisRequest,
    db: Session = Depends(get_db),
) -> AIAnalysisResponse:
    try:
        return analyze_signal(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ai/analyses", response_model=list[AIAnalysisResponse], tags=["ai"])
def get_ai_analyses(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[AIAnalysisResponse]:
    return [analysis_to_response(record) for record in list_ai_analyses(db, limit)]


@router.get("/ai/analyses/{analysis_id}", response_model=AIAnalysisResponse, tags=["ai"])
def get_ai_analysis_by_id(
    analysis_id: int,
    db: Session = Depends(get_db),
) -> AIAnalysisResponse:
    record = get_ai_analysis(db, analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="AI analysis not found")

    return analysis_to_response(record)


@router.get("/orders", response_model=list[PaperOrderRead], tags=["paper-trading"])
def get_orders(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[PaperOrderRead]:
    return [order_to_schema(order) for order in list_paper_orders(db, limit)]


@router.post("/orders/paper", response_model=PaperOrderRead, tags=["paper-trading"])
def post_paper_order(
    payload: PaperOrderRequest,
    db: Session = Depends(get_db),
) -> PaperOrderRead:
    try:
        return order_to_schema(create_paper_order(db, payload))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/positions", response_model=list[PaperPositionRead], tags=["paper-trading"])
def get_positions(db: Session = Depends(get_db)) -> list[PaperPositionRead]:
    return [position_to_schema(position) for position in list_paper_positions(db)]


@router.get("/indicators/preview", tags=["indicators"])
def indicator_preview() -> dict[str, float]:
    return moving_average_snapshot([101.2, 102.4, 101.9, 103.1, 104.8, 104.2])


def signal_to_schema(signal: Signal) -> SignalRead:
    return SignalRead(
        id=signal.id,
        symbol=signal.symbol_ref.symbol,
        direction=signal.direction,
        confidence=signal.confidence,
        timeframe=signal.timeframe,
        reason=signal.reason,
        status=signal.status,
        created_at=signal.created_at,
    )


def market_candle_to_schema(candle: MarketCandle) -> MarketCandleRead:
    return MarketCandleRead(
        id=candle.id,
        symbol=candle.symbol_ref.symbol,
        timeframe=candle.timeframe,
        opened_at=candle.opened_at,
        open=candle.open,
        high=candle.high,
        low=candle.low,
        close=candle.close,
        volume=candle.volume,
    )


def backtest_to_schema(run) -> BacktestRunRead:
    return BacktestRunRead(
        id=run.id,
        symbol=run.symbol_ref.symbol,
        strategy=run.strategy_ref.name if run.strategy_ref else None,
        timeframe=run.timeframe,
        initial_balance=run.initial_balance,
        ending_balance=run.ending_balance,
        total_return=run.total_return,
        win_rate=run.win_rate,
        max_drawdown=run.max_drawdown,
        trades_count=run.trades_count,
        winning_trades=run.winning_trades,
        losing_trades=run.losing_trades,
        status=run.status,
        summary=run.summary,
        created_at=run.created_at,
    )

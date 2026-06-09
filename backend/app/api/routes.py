from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.models import MarketCandle, Signal
from app.schemas.trading import (
    AIModelPrediction,
    AIModelRead,
    AIModelTrainRequest,
    AIAnalysisRequest,
    AIAnalysisResponse,
    ApiCredentialCreate,
    ApiCredentialRead,
    ApiCredentialUpdate,
    AuditEventRead,
    BacktestReport,
    BacktestRunRead,
    BacktestRunRequest,
    CurrentUserRead,
    MarketCandleRead,
    MarketDataRefreshRequest,
    MarketDataRefreshResponse,
    MarketDataScheduleResponse,
    MarketDataSyncRequest,
    MarketDataSyncResponse,
    MarketDataTaskResponse,
    NotificationCreate,
    NotificationRead,
    PaperOrderRead,
    PaperOrderRequest,
    PaperPositionRead,
    EquityCurveResponse,
    NavigationItemRead,
    PortfolioSummaryResponse,
    RiskSettingRead,
    RiskSettingUpdate,
    SignalGenerateRequest,
    SignalRead,
    StrategyCreate,
    StrategyRead,
    StrategyUpdate,
    SymbolCreate,
    SymbolRead,
    AIProviderStatusRequest,
    AIProviderStatusResponse,
    SystemLogRead,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserRead,
    UserUpdate,
)
from app.core.config import settings
from app.core.security import create_access_token
from app.db.auth import get_current_user as require_current_user, require_role
from app.services.indicators.technical import moving_average_snapshot
from app.models import User
from app.services.repository import (
    create_strategy,
    create_symbol,
    delete_strategy,
    ensure_default_risk_settings,
    ensure_default_strategy,
    list_candles,
    list_strategies,
    list_symbols,
    update_risk_settings,
    update_strategy,
)
from app.services.market_data.binance import MarketDataProviderError
from app.services.market_data.jobs import run_market_data_refresh
from app.services.market_data.sync import sync_market_data
from app.services.ai.advisor import analyze_signal, analysis_to_response, get_ai_analysis, list_ai_analyses
from app.services.ai.training import predict as predict_ai_model
from app.services.ai.training import train_model
from app.services.admin import (
    authenticate_user,
    create_credential,
    create_notification,
    delete_credential,
    delete_user,
    list_ai_models,
    list_credentials,
    list_notifications,
    list_system_logs,
    list_users,
    mark_notification_read,
    permissions_for_role,
    register_user,
    update_credential,
    update_user,
)
from app.services.audit import audit_event_to_schema, list_audit_events
from app.services.backtesting.engine import get_backtest_run, list_backtest_runs, run_backtest
from app.services.execution.paper import (
    cancel_paper_order,
    close_paper_position,
    create_paper_order,
    list_paper_orders,
    list_paper_positions,
    order_to_schema,
    position_to_schema,
)
from app.services.execution.portfolio import get_equity_curve, get_portfolio_summary
from app.services.signals import generate_signals, list_signals
from app.workers.tasks import refresh_market_data

router = APIRouter()

NAVIGATION_ITEMS = [
    {
        "label": "Overview",
        "href": "#/overview",
        "icon": "layout-dashboard",
        "permission": "dashboard:view",
        "children": [
            {
                "label": "Portfolio",
                "href": "#/overview/portfolio",
                "icon": "wallet",
                "permission": "portfolio:view",
            },
            {
                "label": "Signals",
                "href": "#/overview/signals",
                "icon": "sparkles",
                "permission": "signals:view",
            },
            {
                "label": "Strategy Controls",
                "href": "#/overview/settings",
                "icon": "sliders-horizontal",
                "permission": "strategies:update",
            },
        ],
    },
    {
        "label": "Admin",
        "href": "#/users",
        "icon": "users",
        "permission": "users:manage",
        "children": [
            {"label": "Users", "href": "#/users", "icon": "users", "permission": "users:manage"},
            {"label": "API Keys", "href": "#/api-keys", "icon": "key", "permission": "api-credentials:manage"},
            {"label": "Risk Settings", "href": "#/risk-settings", "icon": "shield-check", "permission": "risk-settings:manage"},
        ],
    },
    {
        "label": "Research",
        "href": "#/strategies",
        "icon": "sparkles",
        "permission": "strategies:view",
        "children": [
            {"label": "Strategies", "href": "#/strategies", "icon": "sliders-horizontal", "permission": "strategies:view"},
            {"label": "Backtests", "href": "#/backtests", "icon": "activity", "permission": "backtests:view"},
            {"label": "AI Models", "href": "#/ai-models", "icon": "brain", "permission": "ai-models:view"},
        ],
    },
    {
        "label": "Trading",
        "href": "#/trading",
        "icon": "trending-up",
        "permission": "orders:view",
        "children": [
            {
                "label": "Orders",
                "href": "#/trading/orders",
                "icon": "activity",
                "permission": "orders:view",
            },
            {
                "label": "Positions",
                "href": "#/trading/positions",
                "icon": "wallet",
                "permission": "positions:view",
            },
            {
                "label": "Trade History",
                "href": "#/trade-history",
                "icon": "clock",
                "permission": "orders:view",
            },
        ],
    },
    {
        "label": "Activity",
        "href": "#/activity",
        "icon": "activity",
        "permission": "audit:view",
        "children": [
            {
                "label": "Timeline",
                "href": "#/activity",
                "icon": "clock",
                "permission": "audit:view",
            },
            {
                "label": "Audit Log",
                "href": "#/activity/audit",
                "icon": "users",
                "permission": "audit:view",
            },
            {"label": "Logs", "href": "#/logs", "icon": "activity", "permission": "logs:view"},
            {"label": "Notifications", "href": "#/notifications", "icon": "bell", "permission": "notifications:view"},
        ],
    },
]


@router.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "trading-ai-backend"}


@router.post("/auth/register", response_model=UserRead, tags=["auth"])
def post_register(payload: UserCreate, db: Session = Depends(get_db)) -> UserRead:
    try:
        return UserRead.model_validate(register_user(db, payload))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/auth/login", response_model=TokenResponse, tags=["auth"])
def post_login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return TokenResponse(access_token=create_access_token(str(user.id), user.role))


@router.get("/me", response_model=CurrentUserRead, tags=["auth"])
def get_current_user(user: User = Depends(require_current_user)) -> CurrentUserRead:
    return CurrentUserRead(
        id=user.id,
        name=user.full_name,
        role=user.role,
        permissions=permissions_for_role(user.role),
    )


@router.get("/navigation", response_model=list[NavigationItemRead], tags=["auth"])
def get_navigation(user: User = Depends(require_current_user)) -> list[NavigationItemRead]:
    permissions = set(permissions_for_role(user.role))
    items = []
    for item in NAVIGATION_ITEMS:
        if item["permission"] not in permissions:
            continue
        filtered = {**item, "children": [child for child in item["children"] if child["permission"] in permissions]}
        items.append(NavigationItemRead.model_validate(filtered))
    return items


@router.get("/users", response_model=list[UserRead], tags=["users"])
def get_users(
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin")),
) -> list[UserRead]:
    return [UserRead.model_validate(user) for user in list_users(db)]


@router.patch("/users/{user_id}", response_model=UserRead, tags=["users"])
def patch_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin")),
) -> UserRead:
    user = update_user(db, user_id, payload)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserRead.model_validate(user)


@router.delete("/users/{user_id}", tags=["users"])
def delete_user_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin")),
) -> dict[str, bool]:
    if not delete_user(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return {"deleted": True}


@router.get("/api-credentials", response_model=list[ApiCredentialRead], tags=["api-credentials"])
def get_api_credentials(
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin")),
) -> list[ApiCredentialRead]:
    return [ApiCredentialRead.model_validate(credential) for credential in list_credentials(db)]


@router.post("/api-credentials", response_model=ApiCredentialRead, tags=["api-credentials"])
def post_api_credential(
    payload: ApiCredentialCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin")),
) -> ApiCredentialRead:
    if payload.mode == "live":
        risk = ensure_default_risk_settings(db)
        if not risk.live_trading_enabled or risk.emergency_stop:
            raise HTTPException(status_code=400, detail="Live credentials require live trading enabled and emergency stop disabled")
    return ApiCredentialRead.model_validate(create_credential(db, payload))


@router.patch("/api-credentials/{credential_id}", response_model=ApiCredentialRead, tags=["api-credentials"])
def patch_api_credential(
    credential_id: int,
    payload: ApiCredentialUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin")),
) -> ApiCredentialRead:
    credential = update_credential(db, credential_id, payload)
    if credential is None:
        raise HTTPException(status_code=404, detail="API credential not found")
    return ApiCredentialRead.model_validate(credential)


@router.delete("/api-credentials/{credential_id}", tags=["api-credentials"])
def delete_api_credential(
    credential_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin")),
) -> dict[str, bool]:
    if not delete_credential(db, credential_id):
        raise HTTPException(status_code=404, detail="API credential not found")
    return {"deleted": True}


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
    return [StrategyRead.model_validate(strategy) for strategy in list_strategies(db)]


@router.post("/strategies", response_model=StrategyRead, tags=["strategies"])
def post_strategy(
    payload: StrategyCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin")),
) -> StrategyRead:
    return StrategyRead.model_validate(create_strategy(db, payload))


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


@router.post("/strategies/{strategy_id}/enable", response_model=StrategyRead, tags=["strategies"])
def post_enable_strategy(
    strategy_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin")),
) -> StrategyRead:
    strategy = update_strategy(db, strategy_id, StrategyUpdate(enabled=True, status="active"))
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return StrategyRead.model_validate(strategy)


@router.post("/strategies/{strategy_id}/disable", response_model=StrategyRead, tags=["strategies"])
def post_disable_strategy(
    strategy_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin")),
) -> StrategyRead:
    strategy = update_strategy(db, strategy_id, StrategyUpdate(enabled=False, status="paused"))
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return StrategyRead.model_validate(strategy)


@router.delete("/strategies/{strategy_id}", tags=["strategies"])
def delete_strategy_endpoint(
    strategy_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin")),
) -> dict[str, bool]:
    if not delete_strategy(db, strategy_id):
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {"deleted": True}


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


@router.get("/backtests/{run_id}/report", response_model=BacktestReport, tags=["backtests"])
def get_backtest_report(run_id: int, db: Session = Depends(get_db)) -> BacktestReport:
    run = get_backtest_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Backtest not found")
    schema = backtest_to_schema(run)
    return BacktestReport(
        run=schema,
        equity_curve=schema.equity_curve,
        metrics={
            "total_return": schema.total_return,
            "max_drawdown": schema.max_drawdown,
            "profit_factor": schema.profit_factor,
            "sharpe_ratio": schema.sharpe_ratio,
            "win_rate": schema.win_rate,
            "fees": schema.fees,
            "slippage": schema.slippage,
        },
    )


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


@router.get("/ai/provider", response_model=AIProviderStatusResponse, tags=["ai"])
def get_ai_provider_status() -> AIProviderStatusResponse:
    available = ["rules"]
    if settings.openai_api_key:
        available.append("openai")
    if settings.ollama_base_url:
        available.append("ollama")
    if settings.local_model_path:
        available.append("local-llama")

    return AIProviderStatusResponse(
        provider=settings.ai_provider,
        openai_available=bool(settings.openai_api_key),
        available_providers=available,
    )


@router.patch("/ai/provider", response_model=AIProviderStatusResponse, tags=["ai"])
def patch_ai_provider(payload: AIProviderStatusRequest) -> AIProviderStatusResponse:
    provider = payload.provider.lower()
    if provider not in {"rules", "openai", "ollama", "local-llama"}:
        raise HTTPException(status_code=400, detail="Unsupported AI provider")
    if provider == "openai" and not settings.openai_api_key:
        raise HTTPException(status_code=400, detail="OpenAI provider requires OPENAI_API_KEY")

    settings.ai_provider = provider
    return AIProviderStatusResponse(
        provider=settings.ai_provider,
        openai_available=bool(settings.openai_api_key),
        available_providers=["rules", "openai", "ollama", "local-llama"],
    )


@router.get("/ai/analyses/{analysis_id}", response_model=AIAnalysisResponse, tags=["ai"])
def get_ai_analysis_by_id(
    analysis_id: int,
    db: Session = Depends(get_db),
) -> AIAnalysisResponse:
    record = get_ai_analysis(db, analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="AI analysis not found")

    return analysis_to_response(record)


@router.get("/ai/models", response_model=list[AIModelRead], tags=["ai"])
def get_ai_models(db: Session = Depends(get_db)) -> list[AIModelRead]:
    return [AIModelRead.model_validate(model) for model in list_ai_models(db)]


@router.post("/ai/models/train", response_model=AIModelRead, tags=["ai"])
def post_ai_model_train(
    payload: AIModelTrainRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin")),
) -> AIModelRead:
    try:
        return AIModelRead.model_validate(train_model(db, name=payload.name, symbol=payload.symbol, timeframe=payload.timeframe, lookback=payload.lookback))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ai/models/{model_id}/predict", response_model=AIModelPrediction, tags=["ai"])
def post_ai_model_predict(model_id: int, db: Session = Depends(get_db)) -> AIModelPrediction:
    try:
        return AIModelPrediction.model_validate(predict_ai_model(db, model_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/orders", response_model=list[PaperOrderRead], tags=["paper-trading"])
def get_orders(
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, pattern="^(filled|rejected|cancelled|all)$"),
    db: Session = Depends(get_db),
) -> list[PaperOrderRead]:
    return [order_to_schema(order) for order in list_paper_orders(db, limit, status)]


@router.post("/orders/paper", response_model=PaperOrderRead, tags=["paper-trading"])
def post_paper_order(
    payload: PaperOrderRequest,
    db: Session = Depends(get_db),
) -> PaperOrderRead:
    try:
        return order_to_schema(create_paper_order(db, payload))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/orders/{order_id}/cancel", response_model=PaperOrderRead, tags=["paper-trading"])
def post_cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
) -> PaperOrderRead:
    try:
        order = cancel_paper_order(db, order_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if order is None:
        raise HTTPException(status_code=404, detail="Paper order not found")

    return order_to_schema(order)


@router.get("/positions", response_model=list[PaperPositionRead], tags=["paper-trading"])
def get_positions(
    status: str = Query("open", pattern="^(open|closed|all)$"),
    db: Session = Depends(get_db),
) -> list[PaperPositionRead]:
    return [position_to_schema(position) for position in list_paper_positions(db, status)]


@router.post("/positions/{position_id}/close", response_model=PaperPositionRead, tags=["paper-trading"])
def post_close_position(
    position_id: int,
    db: Session = Depends(get_db),
) -> PaperPositionRead:
    try:
        position = close_paper_position(db, position_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if position is None:
        raise HTTPException(status_code=404, detail="Paper position not found")

    return position_to_schema(position)


@router.get("/portfolio/summary", response_model=PortfolioSummaryResponse, tags=["portfolio"])
def get_portfolio_summary_endpoint(db: Session = Depends(get_db)) -> PortfolioSummaryResponse:
    return get_portfolio_summary(db)


@router.get("/portfolio/equity-curve", response_model=EquityCurveResponse, tags=["portfolio"])
def get_equity_curve_endpoint(db: Session = Depends(get_db)) -> EquityCurveResponse:
    return get_equity_curve(db)


@router.get("/audit/events", response_model=list[AuditEventRead], tags=["audit"])
def get_audit_events(
    limit: int = Query(50, ge=1, le=200),
    event_type: str | None = Query(None),
    severity: str | None = Query(None, pattern="^(info|warning|error)$"),
    entity_type: str | None = Query(None),
    db: Session = Depends(get_db),
) -> list[AuditEventRead]:
    return [
        audit_event_to_schema(event)
        for event in list_audit_events(
            db,
            limit=limit,
            event_type=event_type,
            severity=severity,
            entity_type=entity_type,
        )
    ]


@router.get("/notifications", response_model=list[NotificationRead], tags=["notifications"])
def get_notifications(
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
) -> list[NotificationRead]:
    return [NotificationRead.model_validate(notification) for notification in list_notifications(db, unread_only)]


@router.post("/notifications", response_model=NotificationRead, tags=["notifications"])
def post_notification(
    payload: NotificationCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_role("admin")),
) -> NotificationRead:
    return NotificationRead.model_validate(create_notification(db, payload))


@router.post("/notifications/{notification_id}/read", response_model=NotificationRead, tags=["notifications"])
def post_notification_read(notification_id: int, db: Session = Depends(get_db)) -> NotificationRead:
    notification = mark_notification_read(db, notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return NotificationRead.model_validate(notification)


@router.get("/logs", response_model=list[SystemLogRead], tags=["logs"])
def get_logs(
    limit: int = Query(100, ge=1, le=500),
    level: str | None = Query(None, pattern="^(info|warning|error)$"),
    db: Session = Depends(get_db),
) -> list[SystemLogRead]:
    return [SystemLogRead.model_validate(log) for log in list_system_logs(db, limit, level)]


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
        fees=run.fees,
        slippage=run.slippage,
        spread=run.spread,
        profit_factor=run.profit_factor,
        sharpe_ratio=run.sharpe_ratio,
        equity_curve=run.equity_curve,
        trades_count=run.trades_count,
        winning_trades=run.winning_trades,
        losing_trades=run.losing_trades,
        status=run.status,
        summary=run.summary,
        created_at=run.created_at,
    )

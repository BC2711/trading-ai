from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.db.session import SessionLocal
from app.models import MarketCandle, MarketOrderBookSnapshot, MarketTick, MarketTrade, Signal
from app.schemas.trading import (
    AIModelPrediction,
    AIPredictionRequest,
    AIModelEvaluationRead,
    AIModelRead,
    AIModelCompareRequest,
    AIModelComparison,
    AIModelRetrainRequest,
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
    WalkForwardRequest,
    WalkForwardRunRead,
    CurrentUserRead,
    MarketCandleRead,
    MarketDataImportRequest,
    MarketDataImportResponse,
    MarketDataRefreshRequest,
    MarketDataRefreshResponse,
    MarketDataRepairRequest,
    MarketDataRepairResponse,
    MarketDataScheduleResponse,
    MarketDataStreamEvent,
    MarketDataSyncRequest,
    MarketDataSyncResponse,
    MarketDataTaskResponse,
    MarketDataValidationResponse,
    MarketHistoryResponse,
    MarketOrderBookRead,
    MarketTickRead,
    MarketTradeRead,
    NotificationCreate,
    NotificationRead,
    PaperOrderRead,
    PaperOrderRequest,
    PaperPositionRead,
    PermissionRead,
    NavigationItemRead,
    RefreshTokenRequest,
    RiskSettingRead,
    RiskSettingUpdate,
    RoleCreate,
    RoleRead,
    RoleUpdate,
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
    UserRolesUpdate,
    UserUpdate,
    WarehouseCandleRead,
)
from app.schemas.portfolio import (
    EquityCurveResponse,
    PortfolioAllocationResponse,
    PortfolioExposureResponse,
    PortfolioPerformanceResponse,
    PortfolioPnlResponse,
    PortfolioSummaryResponse,
)
from app.schemas.analytics import (
    AnalyticsEquityCurveResponse,
    AnalyticsTradeRead,
    PerformanceSummaryResponse,
    StrategyComparisonResponse,
)
from app.schemas.brokers import (
    BrokerBalanceResponse,
    BrokerCancelResponse,
    BrokerConnectRequest,
    BrokerConnectionResponse,
    BrokerDisconnectRequest,
    BrokerOrderCreate,
    BrokerOrderRead,
    BrokerOrdersResponse,
    BrokerPositionsResponse,
    BrokerStatusRead,
)
from app.schemas.calendar import EconomicCalendarEventCreate, EconomicCalendarEventRead
from app.schemas.copilot import CopilotChatRequest, CopilotChatResponse, CopilotMessage
from app.schemas.features import FeatureCalculationRequest, FeatureCalculationResponse, FeatureSetRead, MarketFeatureRead
from app.schemas.notifications import (
    NotificationMarkReadRequest,
    NotificationMarkReadResponse,
    NotificationSettingsRead,
    NotificationSettingsUpdate,
)
from app.schemas.risk import (
    PositionSizeRequest,
    PositionSizeResponse,
    RiskLimitsRead,
    RiskLimitsUpdate,
    MonteCarloRequest,
    MonteCarloResponse,
    RiskSummaryResponse,
    RiskTradeValidationRequest,
    RiskTradeValidationResponse,
)
from app.schemas.paper_trading import (
    PaperTradingAccountRead,
    PaperTradingOrderCreate,
    PaperTradingOrderRead,
    PaperTradingPerformanceResponse,
    PaperTradingPositionRead,
    PaperTradingResetRequest,
    PaperTradingResetResponse,
)
from app.schemas.strategy_builder import (
    StrategyBuilderCreate,
    StrategyBuilderRead,
    StrategyEvaluationRequest,
    StrategyEvaluationResponse,
    StrategyRuleRead,
    StrategyRulesUpdate,
)
from app.schemas.scanner import ScannerRead, ScannerRunRequest
from app.schemas.sentiment import SentimentAnalyzeRequest, SentimentResponse
from app.core.config import settings
from app.core.security import create_access_token, decode_jwt
from app.db.auth import get_current_user as require_current_user, require_permission
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
from app.services.market_data.repository import MarketDataRepository
from app.services.market_data.service import MarketDataService
from app.services.market_data.sync import sync_market_data
from app.services.market_data.warehouse import MarketWarehouseService
from app.services.market_data.websocket import market_data_websocket
from app.services.ai.features import FeatureService
from app.services.ai.advisor import analyze_signal, analysis_to_response, get_ai_analysis, list_ai_analyses
from app.services.ai.training import predict as predict_ai_model
from app.services.ai.training import train_model
from app.services.ai.training import compare_models, deploy_model, disable_model, retrain_model
from app.services.ai.inference import PredictionService
from app.services.ai.registry import ModelRegistryService
from app.services.analytics import (
    get_analytics_trades,
    get_equity_curve as get_analytics_equity_curve,
    get_performance_summary,
    get_strategy_comparison,
)
from app.services.admin import (
    assign_roles_to_user,
    authenticate_user,
    clear_login_attempts,
    consume_refresh_token,
    create_credential,
    create_notification,
    create_role,
    delete_credential,
    delete_role as delete_rbac_role,
    delete_user,
    list_credentials,
    list_notifications,
    list_permissions,
    list_roles,
    list_system_logs,
    list_users,
    issue_refresh_token,
    login_retry_after_seconds,
    login_throttle_key,
    mark_notification_read,
    permissions_for_user,
    record_failed_login_attempt,
    register_user,
    revoke_refresh_token,
    revoke_user_refresh_tokens,
    roles_for_user,
    update_credential,
    update_role,
    update_user,
)
from app.services.audit import audit_event_to_schema, list_audit_events, record_compliance_event
from app.services.backtesting.engine import get_backtest_run, list_backtest_runs, run_backtest
from app.services.backtesting.walk_forward import get_walk_forward_run, run_walk_forward
from app.services.calendar import create_event as create_calendar_event, high_impact_events, list_events as list_calendar_events
from app.services.copilot import chat as copilot_chat, history as copilot_history
from app.services.execution.paper import (
    cancel_paper_order,
    close_paper_position,
    create_paper_order,
    list_paper_orders,
    list_paper_positions,
    order_to_schema,
    position_to_schema,
)
from app.services.portfolio import (
    get_equity_curve,
    get_portfolio_allocation,
    get_portfolio_exposure,
    get_portfolio_performance,
    get_portfolio_pnl,
    get_portfolio_summary,
)
from app.services.paper_trading import PaperTradingService
from app.services.risk import (
    get_limits as get_risk_limits,
    position_size as calculate_position_size,
    risk_summary,
    set_circuit_breaker,
    update_limits as update_risk_limits,
    validate_trade_request,
)
from app.services.risk.monte_carlo import get_monte_carlo_run, run_monte_carlo
from app.services.scanner import get_scanner_results, run_scanner, scanner_signals
from app.services.sentiment import analyze_sentiment, get_market_sentiment, get_symbol_sentiment
from app.services.notifications import (
    get_notification_settings,
    mark_notifications_read,
    update_notification_settings,
)
from app.services.strategy_builder import (
    create_strategy_builder,
    evaluate_strategy,
    get_strategy_rules,
    list_strategy_builders,
    update_strategy_rules,
)
from app.services.execution.brokers import BrokerAdapterError, BrokerNotImplementedError, BrokerService
from app.services.signals import generate_signals, list_signals
from app.websockets.manager import websocket_manager
from app.workers.tasks import refresh_market_data

router = APIRouter()


def client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.client.host if request.client else None


def audit_route_event(
    db: Session,
    request: Request,
    *,
    action: str,
    module: str,
    status: str,
    message: str,
    user: User | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    severity: str | None = None,
    details: dict | None = None,
) -> None:
    record_compliance_event(
        db,
        action=action,
        module=module,
        status=status,
        message=message,
        user_id=user.id if user else None,
        user_email=user.email if user else None,
        user_name=user.full_name if user else None,
        ip_address=client_ip(request),
        entity_type=entity_type,
        entity_id=entity_id,
        severity=severity,
        details=details,
        commit=True,
    )

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
        "label": "Administration",
        "href": "#/users",
        "icon": "users",
        "permission": "users:manage",
        "children": [
            {"label": "Users", "href": "#/users", "icon": "users", "permission": "users:manage"},
            {
                "label": "Roles & Permissions",
                "href": "#/administration/roles-permissions",
                "icon": "shield-check",
                "permission": "manage_users",
            },
            {
                "label": "Audit Logs",
                "href": "#/administration/audit-logs",
                "icon": "activity",
                "permission": "audit:view",
            },
            {"label": "API Keys", "href": "#/api-keys", "icon": "key", "permission": "api-credentials:manage"},
            {
                "label": "Notification Settings",
                "href": "#/administration/notification-settings",
                "icon": "bell",
                "permission": "notifications:manage",
            },
            {
                "label": "System Monitoring",
                "href": "#/administration/system-monitoring",
                "icon": "activity",
                "permission": "logs:view",
            },
        ],
    },
    {
        "label": "Research",
        "href": "#/strategies",
        "icon": "sparkles",
        "permission": "strategies:view",
        "children": [
            {"label": "Strategies", "href": "#/strategies", "icon": "sliders-horizontal", "permission": "strategies:view"},
            {"label": "Strategy Builder", "href": "#/strategies/builder", "icon": "activity", "permission": "strategies:update"},
            {"label": "Backtests", "href": "#/backtests", "icon": "activity", "permission": "backtests:view"},
            {"label": "Walk-Forward Testing", "href": "#/backtests/walk-forward", "icon": "activity", "permission": "backtests:run"},
            {"label": "AI Models", "href": "#/ai-models", "icon": "brain", "permission": "ai-models:view"},
        ],
    },
    {
        "label": "Market",
        "href": "#/market/scanner",
        "icon": "scan-search",
        "permission": "signals:view",
        "children": [
            {"label": "Market Scanner", "href": "#/market/scanner", "icon": "scan-search", "permission": "signals:view"},
            {"label": "News Sentiment", "href": "#/market/sentiment", "icon": "newspaper", "permission": "signals:view"},
            {"label": "Economic Calendar", "href": "#/market/calendar", "icon": "calendar-days", "permission": "signals:view"},
        ],
    },
    {
        "label": "AI",
        "href": "#/ai/copilot",
        "icon": "brain",
        "permission": "ai-models:view",
        "children": [
            {"label": "AI Copilot", "href": "#/ai/copilot", "icon": "message-circle", "permission": "ai-analyses:view"},
            {"label": "Model Training", "href": "#/ai/model-training", "icon": "activity", "permission": "ai-models:manage"},
            {"label": "Model Registry", "href": "#/ai/model-registry", "icon": "brain", "permission": "ai-models:view"},
        ],
    },
    {
        "label": "Trading",
        "href": "#/trading",
        "icon": "trending-up",
        "permission": "orders:view",
        "children": [
            {
                "label": "Portfolio",
                "href": "#/trading/portfolio",
                "icon": "wallet",
                "permission": "portfolio:view",
            },
            {
                "label": "Paper Trading",
                "href": "#/trading/paper",
                "icon": "activity",
                "permission": "orders:create",
            },
            {
                "label": "Broker Connections",
                "href": "#/trading/brokers",
                "icon": "key",
                "permission": "api-credentials:manage",
            },
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
        "label": "Analytics",
        "href": "#/analytics/performance",
        "icon": "bar-chart-3",
        "permission": "portfolio:view",
        "children": [
            {
                "label": "Performance",
                "href": "#/analytics/performance",
                "icon": "bar-chart-3",
                "permission": "portfolio:view",
            },
        ],
    },
    {
        "label": "Risk",
        "href": "#/risk-analytics",
        "icon": "shield-check",
        "permission": "risk-settings:view",
        "children": [
            {
                "label": "Risk Settings",
                "href": "#/risk-settings",
                "icon": "sliders-horizontal",
                "permission": "risk-settings:view",
            },
            {
                "label": "Risk Analytics",
                "href": "#/risk-analytics",
                "icon": "activity",
                "permission": "risk-settings:view",
            },
            {
                "label": "Monte Carlo",
                "href": "#/risk/monte-carlo",
                "icon": "activity",
                "permission": "risk-settings:view",
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


@router.websocket("/ws/market-data")
async def websocket_market_data(websocket: WebSocket, channels: str | None = None, token: str | None = None):
    if token and not decode_jwt(token):
        await websocket.close(code=1008)
        return
    selected_channels = channels.split(",") if channels else None
    await market_data_websocket.connect(websocket, selected_channels)
    try:
        while True:
            message = await websocket.receive_json()
            if isinstance(message, dict) and message.get("type") == "subscribe":
                requested = message.get("channels")
                if isinstance(requested, list):
                    await market_data_websocket.subscribe(websocket, [str(channel) for channel in requested])
    except WebSocketDisconnect:
        market_data_websocket.disconnect(websocket)


@router.websocket("/ws/prices")
async def websocket_prices(websocket: WebSocket, token: str | None = None):
    if not await _websocket_token_allowed(websocket, token):
        return
    try:
        await websocket_manager.stream(websocket, "prices", _prices_stream_payload, interval_seconds=5)
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, "prices")


@router.websocket("/ws/signals")
async def websocket_signals(websocket: WebSocket, token: str | None = None):
    if not await _websocket_token_allowed(websocket, token):
        return
    try:
        await websocket_manager.stream(websocket, "signals", _signals_stream_payload, interval_seconds=8)
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, "signals")


@router.websocket("/ws/orders")
async def websocket_orders(websocket: WebSocket, token: str | None = None):
    if not await _websocket_token_allowed(websocket, token):
        return
    try:
        await websocket_manager.stream(websocket, "orders", _orders_stream_payload, interval_seconds=6)
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, "orders")


@router.websocket("/ws/positions")
async def websocket_positions(websocket: WebSocket, token: str | None = None):
    if not await _websocket_token_allowed(websocket, token):
        return
    try:
        await websocket_manager.stream(websocket, "positions", _positions_stream_payload, interval_seconds=6)
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, "positions")


@router.websocket("/ws/portfolio")
async def websocket_portfolio(websocket: WebSocket, token: str | None = None):
    if not await _websocket_token_allowed(websocket, token):
        return
    try:
        await websocket_manager.stream(websocket, "portfolio", _portfolio_stream_payload, interval_seconds=8)
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, "portfolio")


@router.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket, token: str | None = None):
    if not await _websocket_token_allowed(websocket, token):
        return
    try:
        await websocket_manager.stream(websocket, "notifications", _notifications_stream_payload, interval_seconds=10)
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, "notifications")


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
def post_login(payload: UserLogin, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    throttle_key = login_throttle_key(payload.email, client_ip(request))
    retry_after = login_retry_after_seconds(throttle_key)
    if retry_after is not None:
        raise HTTPException(
            status_code=429,
            detail="Too many failed login attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        audit_route_event(
            db,
            request,
            action="failed_login",
            module="users",
            status="failed",
            message=f"Failed login attempt for {payload.email.lower()}.",
            severity="warning",
            details={"email": payload.email.lower()},
        )
        retry_after = record_failed_login_attempt(throttle_key)
        if retry_after is not None:
            raise HTTPException(
                status_code=429,
                detail="Too many failed login attempts. Try again later.",
                headers={"Retry-After": str(retry_after)},
            )
        raise HTTPException(status_code=401, detail="Invalid email or password")
    clear_login_attempts(throttle_key)
    audit_route_event(
        db,
        request,
        action="login",
        module="users",
        status="success",
        message=f"{user.email} logged in.",
        user=user,
    )
    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role),
        refresh_token=issue_refresh_token(db, user),
        token_type="bearer",
    )


@router.post("/auth/logout", tags=["auth"])
def post_logout(
    request: Request,
    payload: RefreshTokenRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_current_user),
) -> dict[str, bool]:
    if payload and payload.refresh_token:
        revoke_refresh_token(db, payload.refresh_token, user.id)
    else:
        revoke_user_refresh_tokens(db, user.id)
    audit_route_event(
        db,
        request,
        action="logout",
        module="users",
        status="success",
        message=f"{user.email} logged out.",
        user=user,
    )
    return {"logged_out": True}


@router.post("/auth/refresh", response_model=TokenResponse, tags=["auth"])
def post_refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = consume_refresh_token(db, payload.refresh_token)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role),
        refresh_token=issue_refresh_token(db, user),
        token_type="bearer",
    )


@router.get("/me", response_model=CurrentUserRead, tags=["auth"])
def get_current_user(db: Session = Depends(get_db), user: User = Depends(require_current_user)) -> CurrentUserRead:
    return CurrentUserRead(
        id=user.id,
        name=user.full_name,
        role=user.role,
        permissions=permissions_for_user(db, user),
    )


@router.get("/navigation", response_model=list[NavigationItemRead], tags=["auth"])
def get_navigation(db: Session = Depends(get_db), user: User = Depends(require_current_user)) -> list[NavigationItemRead]:
    permissions = set(permissions_for_user(db, user))
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
    _user: User = Depends(require_permission("manage_users")),
) -> list[UserRead]:
    return [UserRead.model_validate(user) for user in list_users(db)]


@router.patch("/users/{user_id}", response_model=UserRead, tags=["users"])
def patch_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("manage_users")),
) -> UserRead:
    user = update_user(db, user_id, payload)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserRead.model_validate(user)


@router.delete("/users/{user_id}", tags=["users"])
def delete_user_endpoint(
    user_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("manage_users")),
) -> dict[str, bool]:
    if not delete_user(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return {"deleted": True}


@router.get("/roles", response_model=list[RoleRead], tags=["roles"])
def get_roles(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("manage_users")),
) -> list[RoleRead]:
    return [role_to_schema(role) for role in list_roles(db)]


@router.post("/roles", response_model=RoleRead, tags=["roles"])
def post_role(
    payload: RoleCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("manage_users")),
) -> RoleRead:
    try:
        return role_to_schema(create_role(db, payload))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/roles/{role_id}", response_model=RoleRead, tags=["roles"])
def put_role(
    role_id: int,
    payload: RoleUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("manage_users")),
) -> RoleRead:
    try:
        role = update_role(db, role_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")
    return role_to_schema(role)


@router.delete("/roles/{role_id}", tags=["roles"])
def delete_role_endpoint(
    role_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("manage_users")),
) -> dict[str, bool]:
    try:
        if not delete_rbac_role(db, role_id):
            raise HTTPException(status_code=404, detail="Role not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"deleted": True}


@router.get("/permissions", response_model=list[PermissionRead], tags=["roles"])
def get_permissions(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("manage_users")),
) -> list[PermissionRead]:
    return [PermissionRead.model_validate(permission) for permission in list_permissions(db)]


@router.post("/users/{user_id}/roles", response_model=UserRead, tags=["roles"])
def post_user_roles(
    user_id: int,
    payload: UserRolesUpdate,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("manage_users")),
) -> UserRead:
    try:
        user = assign_roles_to_user(db, user_id, payload.role_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    assigned_roles = [role.name for role in roles_for_user(db, user.id)]
    audit_route_event(
        db,
        request,
        action="user_role_change",
        module="users",
        status="success",
        message=f"Updated roles for {user.email}.",
        user=actor,
        entity_type="user",
        entity_id=user.id,
        details={"target_user": user.email, "role_ids": payload.role_ids, "roles": assigned_roles},
    )
    return UserRead.model_validate(user)


@router.get("/users/{user_id}/permissions", response_model=list[str], tags=["roles"])
def get_user_permissions(
    user_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("manage_users")),
) -> list[str]:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return permissions_for_user(db, user)


@router.get("/api-credentials", response_model=list[ApiCredentialRead], tags=["api-credentials"])
def get_api_credentials(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("manage_api_keys")),
) -> list[ApiCredentialRead]:
    return [ApiCredentialRead.model_validate(credential) for credential in list_credentials(db)]


@router.post("/api-credentials", response_model=ApiCredentialRead, tags=["api-credentials"])
def post_api_credential(
    payload: ApiCredentialCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("manage_api_keys")),
) -> ApiCredentialRead:
    if payload.mode == "live":
        risk = ensure_default_risk_settings(db)
        if not risk.live_trading_enabled or risk.emergency_stop:
            audit_route_event(
                db,
                request,
                action="api_key_creation",
                module="administration",
                status="rejected",
                message=f"Rejected live API key creation for {payload.exchange.lower()}.",
                user=user,
                severity="warning",
                details={"exchange": payload.exchange.lower(), "mode": payload.mode},
            )
            raise HTTPException(status_code=400, detail="Live credentials require live trading enabled and emergency stop disabled")
    credential = create_credential(db, payload)
    audit_route_event(
        db,
        request,
        action="api_key_creation",
        module="administration",
        status="success",
        message=f"Created API key for {credential.exchange}.",
        user=user,
        entity_type="api_credential",
        entity_id=credential.id,
        details={"exchange": credential.exchange, "mode": credential.mode},
    )
    return ApiCredentialRead.model_validate(credential)


@router.patch("/api-credentials/{credential_id}", response_model=ApiCredentialRead, tags=["api-credentials"])
def patch_api_credential(
    credential_id: int,
    payload: ApiCredentialUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("manage_api_keys")),
) -> ApiCredentialRead:
    credential = update_credential(db, credential_id, payload)
    if credential is None:
        raise HTTPException(status_code=404, detail="API credential not found")
    return ApiCredentialRead.model_validate(credential)


@router.delete("/api-credentials/{credential_id}", tags=["api-credentials"])
def delete_api_credential(
    credential_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("manage_api_keys")),
) -> dict[str, bool]:
    if not delete_credential(db, credential_id):
        raise HTTPException(status_code=404, detail="API credential not found")
    audit_route_event(
        db,
        request,
        action="api_key_deletion",
        module="administration",
        status="success",
        message=f"Deleted API credential {credential_id}.",
        user=user,
        entity_type="api_credential",
        entity_id=credential_id,
    )
    return {"deleted": True}


@router.get("/symbols", response_model=list[SymbolRead], tags=["symbols"])
def get_symbols(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("symbols:view")),
) -> list[SymbolRead]:
    return [SymbolRead.model_validate(symbol) for symbol in list_symbols(db)]


@router.post("/symbols", response_model=SymbolRead, tags=["symbols"])
def post_symbol(
    payload: SymbolCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("symbols:manage")),
) -> SymbolRead:
    return SymbolRead.model_validate(create_symbol(db, payload))


@router.get("/candles", response_model=list[MarketCandleRead], tags=["market-data"])
def get_candles(
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("15m"),
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("market-data:view")),
) -> list[MarketCandleRead]:
    return [market_candle_to_schema(candle) for candle in list_candles(db, symbol, timeframe, limit)]


@router.get("/market/candles", response_model=list[WarehouseCandleRead], tags=["market-warehouse"])
def get_market_warehouse_candles(
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("15m"),
    limit: int = Query(200, ge=1, le=1000),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("market-data:view")),
) -> list[WarehouseCandleRead]:
    return MarketWarehouseService(db).retrieve_market_history(
        symbol,
        timeframe=timeframe,
        limit=limit,
        start=start,
        end=end,
    ).candles


@router.post("/market/candles/import", response_model=MarketDataImportResponse, tags=["market-warehouse"])
def post_market_warehouse_candles_import(
    payload: MarketDataImportRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("market-data:import")),
) -> MarketDataImportResponse:
    try:
        return MarketWarehouseService(db).import_candles(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/market/history/{symbol}", response_model=MarketHistoryResponse, tags=["market-warehouse"])
def get_market_history(
    symbol: str,
    timeframe: str = Query("15m"),
    limit: int = Query(500, ge=1, le=1000),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("market-data:view")),
) -> MarketHistoryResponse:
    return MarketWarehouseService(db).retrieve_market_history(
        symbol,
        timeframe=timeframe,
        limit=limit,
        start=start,
        end=end,
    )


@router.post("/market/history/sync", response_model=MarketDataSyncResponse, tags=["market-warehouse"])
def post_market_history_sync(
    payload: MarketDataSyncRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("market-data:sync")),
) -> MarketDataSyncResponse:
    try:
        response = MarketWarehouseService(db).sync_historical_data(payload)
    except MarketDataProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    signals = generate_signals(db, timeframe=payload.timeframe) if payload.regenerate_signals else []
    response.signals = [signal_to_schema(signal) for signal in signals]
    return response


@router.post("/market-data/import", response_model=MarketDataImportResponse, tags=["market-data"])
def post_market_data_import(
    payload: MarketDataImportRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("market-data:import")),
) -> MarketDataImportResponse:
    try:
        return MarketDataService(db).import_historical_data(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/market-data/validate", response_model=MarketDataValidationResponse, tags=["market-data"])
def get_market_data_validation(
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("15m"),
    limit: int = Query(500, ge=2, le=1000),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("market-data:view")),
) -> MarketDataValidationResponse:
    try:
        return MarketDataService(db).validate_data(symbol, timeframe, limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/market-data/repair", response_model=MarketDataRepairResponse, tags=["market-data"])
def post_market_data_repair(
    payload: MarketDataRepairRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("market-data:repair")),
) -> MarketDataRepairResponse:
    try:
        return MarketDataService(db).repair_data(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/market-data/ticks", response_model=list[MarketTickRead], tags=["market-data"])
def get_market_ticks(
    symbol: str = Query("BTCUSDT"),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("market-data:view")),
) -> list[MarketTickRead]:
    return [tick_to_schema(tick) for tick in MarketDataRepository(db).list_ticks(symbol, limit)]


@router.get("/market-data/trades", response_model=list[MarketTradeRead], tags=["market-data"])
def get_market_trades(
    symbol: str = Query("BTCUSDT"),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("market-data:view")),
) -> list[MarketTradeRead]:
    return [trade_to_schema(trade) for trade in MarketDataRepository(db).list_trades(symbol, limit)]


@router.get("/market-data/order-books", response_model=list[MarketOrderBookRead], tags=["market-data"])
def get_market_order_books(
    symbol: str = Query("BTCUSDT"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("market-data:view")),
) -> list[MarketOrderBookRead]:
    return [order_book_to_schema(snapshot) for snapshot in MarketDataRepository(db).list_order_books(symbol, limit)]


@router.get("/features", response_model=list[MarketFeatureRead], tags=["features"])
def get_features(
    limit: int = Query(100, ge=1, le=500),
    symbol: str | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("market-data:view")),
) -> list[MarketFeatureRead]:
    return FeatureService(db).list_features(limit=limit, symbol=symbol)


@router.post("/features/calculate", response_model=FeatureCalculationResponse, tags=["features"])
def post_features_calculate(
    payload: FeatureCalculationRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("market-data:import")),
) -> FeatureCalculationResponse:
    try:
        return FeatureService(db).calculate(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/features/sets", response_model=list[FeatureSetRead], tags=["features"])
def get_feature_sets(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("market-data:view")),
) -> list[FeatureSetRead]:
    return FeatureService(db).list_feature_sets()


@router.get("/features/{symbol}", response_model=list[MarketFeatureRead], tags=["features"])
def get_features_for_symbol(
    symbol: str,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("market-data:view")),
) -> list[MarketFeatureRead]:
    return FeatureService(db).list_features(limit=limit, symbol=symbol)


@router.post("/market-data/stream", tags=["market-data"])
async def post_market_data_stream_event(
    event: MarketDataStreamEvent,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("market-data:stream")),
) -> dict:
    try:
        result = MarketDataService(db).ingest_stream_event(event)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await market_data_websocket.publish(event.channel, result["payload"])
    return {"status": "ok", **result}


@router.post("/market-data/sync", response_model=MarketDataSyncResponse, tags=["market-data"])
def post_market_data_sync(
    payload: MarketDataSyncRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("market-data:sync")),
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
    _user: User = Depends(require_permission("market-data:sync")),
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
def post_market_data_refresh_task(
    payload: MarketDataRefreshRequest | None = None,
    _user: User = Depends(require_permission("market-data:sync")),
) -> MarketDataTaskResponse:
    payload = payload or MarketDataRefreshRequest()
    task = refresh_market_data.delay(
        symbols=payload.symbols,
        timeframe=payload.timeframe,
        limit=payload.limit,
        regenerate_signals=payload.regenerate_signals,
    )
    return MarketDataTaskResponse(task_id=task.id, status="queued")


@router.get("/market-data/schedule", response_model=MarketDataScheduleResponse, tags=["market-data"])
def get_market_data_schedule(
    _user: User = Depends(require_permission("market-data:view")),
) -> MarketDataScheduleResponse:
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
def get_signals(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("signals:view")),
) -> list[SignalRead]:
    return [signal_to_schema(signal) for signal in list_signals(db)]


@router.post("/signals/generate", response_model=list[SignalRead], tags=["signals"])
def post_generate_signals(
    payload: SignalGenerateRequest | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("signals:generate")),
) -> list[SignalRead]:
    payload = payload or SignalGenerateRequest()
    return [signal_to_schema(signal) for signal in generate_signals(db, payload.symbol, payload.timeframe)]


@router.get("/scanner", response_model=list[ScannerRead], tags=["scanner"])
def get_scanner(
    symbol: str | None = Query(None),
    signal: str | None = Query(None, pattern="^(buy|sell|hold)$"),
    min_confidence: float | None = Query(None, ge=0, le=1),
    risk_level: str | None = Query(None, pattern="^(low|medium|high)$"),
    timeframe: str = Query("15m"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("signals:view")),
) -> list[ScannerRead]:
    results = get_scanner_results(db, symbols=[symbol] if symbol else None, timeframe=timeframe)
    return _filter_scanner_results(results, signal, min_confidence, risk_level)


@router.post("/scanner/run", response_model=list[ScannerRead], tags=["scanner"])
def post_scanner_run(
    payload: ScannerRunRequest | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("signals:generate")),
) -> list[ScannerRead]:
    payload = payload or ScannerRunRequest()
    return run_scanner(db, symbols=payload.symbols, timeframe=payload.timeframe, lookback=payload.lookback)


@router.get("/scanner/signals", response_model=list[ScannerRead], tags=["scanner"])
def get_scanner_signals(
    min_confidence: float = Query(0.6, ge=0, le=1),
    timeframe: str = Query("15m"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("signals:view")),
) -> list[ScannerRead]:
    return scanner_signals(db, min_confidence=min_confidence, timeframe=timeframe)


@router.get("/sentiment", response_model=SentimentResponse, tags=["sentiment"])
def get_sentiment(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("signals:view")),
) -> SentimentResponse:
    return get_market_sentiment(db)


@router.post("/sentiment/analyze", response_model=SentimentResponse, tags=["sentiment"])
def post_sentiment_analyze(
    payload: SentimentAnalyzeRequest | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("signals:generate")),
) -> SentimentResponse:
    payload = payload or SentimentAnalyzeRequest()
    return analyze_sentiment(db, symbol=payload.symbol)


@router.get("/sentiment/{symbol}", response_model=SentimentResponse, tags=["sentiment"])
def get_symbol_sentiment_endpoint(
    symbol: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("signals:view")),
) -> SentimentResponse:
    return get_symbol_sentiment(db, symbol)


@router.get("/calendar/events", response_model=list[EconomicCalendarEventRead], tags=["calendar"])
def get_calendar_events(
    country: str | None = Query(None),
    impact_level: str | None = Query(None, pattern="^(low|medium|high)$"),
    asset: str | None = Query(None),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    _user: User = Depends(require_permission("signals:view")),
) -> list[EconomicCalendarEventRead]:
    return list_calendar_events(
        country=country,
        impact_level=impact_level,
        asset=asset,
        start=start,
        end=end,
    )


@router.get("/calendar/high-impact", response_model=list[EconomicCalendarEventRead], tags=["calendar"])
def get_high_impact_calendar_events(
    _user: User = Depends(require_permission("signals:view")),
) -> list[EconomicCalendarEventRead]:
    return high_impact_events()


@router.post("/calendar/events", response_model=EconomicCalendarEventRead, tags=["calendar"])
def post_calendar_event(
    payload: EconomicCalendarEventCreate,
    _user: User = Depends(require_permission("signals:generate")),
) -> EconomicCalendarEventRead:
    return create_calendar_event(payload)


@router.post("/copilot/chat", response_model=CopilotChatResponse, tags=["copilot"])
def post_copilot_chat(
    payload: CopilotChatRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("ai-analyses:create")),
) -> CopilotChatResponse:
    return copilot_chat(db, payload.message)


@router.get("/copilot/history", response_model=list[CopilotMessage], tags=["copilot"])
def get_copilot_history(
    _user: User = Depends(require_permission("ai-analyses:view")),
) -> list[CopilotMessage]:
    return copilot_history()


@router.get("/strategies", response_model=list[StrategyRead], tags=["strategies"])
def get_strategies(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("strategies:view")),
) -> list[StrategyRead]:
    return [StrategyRead.model_validate(strategy) for strategy in list_strategies(db)]


@router.post("/strategies", response_model=StrategyRead, tags=["strategies"])
def post_strategy(
    payload: StrategyCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("manage_strategies")),
) -> StrategyRead:
    strategy = create_strategy(db, payload)
    audit_route_event(
        db,
        request,
        action="strategy_change",
        module="strategy",
        status="success",
        message=f"Created strategy {strategy.name}.",
        user=user,
        entity_type="strategy",
        entity_id=strategy.id,
        details=payload.model_dump(),
    )
    return StrategyRead.model_validate(strategy)


@router.post("/strategies/builder", response_model=StrategyBuilderRead, tags=["strategies"])
def post_strategy_builder(
    payload: StrategyBuilderCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("strategies:update")),
) -> StrategyBuilderRead:
    try:
        return create_strategy_builder(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/strategies/builder", response_model=list[StrategyBuilderRead], tags=["strategies"])
def get_strategy_builders(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("strategies:view")),
) -> list[StrategyBuilderRead]:
    return list_strategy_builders(db)


@router.patch("/strategies/{strategy_id}", response_model=StrategyRead, tags=["strategies"])
def patch_strategy(
    strategy_id: int,
    payload: StrategyUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("strategies:update")),
) -> StrategyRead:
    strategy = update_strategy(db, strategy_id, payload)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")

    audit_route_event(
        db,
        request,
        action="strategy_change",
        module="strategy",
        status="success",
        message=f"Updated strategy {strategy.name}.",
        user=user,
        entity_type="strategy",
        entity_id=strategy.id,
        details=payload.model_dump(exclude_unset=True),
    )
    return StrategyRead.model_validate(strategy)


@router.get("/strategies/{strategy_id}/rules", response_model=list[StrategyRuleRead], tags=["strategies"])
def get_strategy_rules_endpoint(
    strategy_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("strategies:view")),
) -> list[StrategyRuleRead]:
    rules = get_strategy_rules(db, strategy_id)
    if rules is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return rules


@router.put("/strategies/{strategy_id}/rules", response_model=list[StrategyRuleRead], tags=["strategies"])
def put_strategy_rules_endpoint(
    strategy_id: int,
    payload: StrategyRulesUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("strategies:update")),
) -> list[StrategyRuleRead]:
    rules = update_strategy_rules(db, strategy_id, payload)
    if rules is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    audit_route_event(
        db,
        request,
        action="strategy_change",
        module="strategy",
        status="success",
        message=f"Updated rules for strategy {strategy_id}.",
        user=user,
        entity_type="strategy",
        entity_id=strategy_id,
        details={"rules": len(payload.rules)},
    )
    return rules


@router.post("/strategies/{strategy_id}/evaluate", response_model=StrategyEvaluationResponse, tags=["strategies"])
def post_strategy_evaluate(
    strategy_id: int,
    payload: StrategyEvaluationRequest | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("strategies:view")),
) -> StrategyEvaluationResponse:
    try:
        evaluation = evaluate_strategy(db, strategy_id, payload or StrategyEvaluationRequest())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if evaluation is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return evaluation


@router.post("/strategies/{strategy_id}/enable", response_model=StrategyRead, tags=["strategies"])
def post_enable_strategy(
    strategy_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("manage_strategies")),
) -> StrategyRead:
    strategy = update_strategy(db, strategy_id, StrategyUpdate(enabled=True, status="active"))
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    audit_route_event(
        db,
        request,
        action="strategy_change",
        module="strategy",
        status="success",
        message=f"Enabled strategy {strategy.name}.",
        user=user,
        entity_type="strategy",
        entity_id=strategy.id,
        details={"enabled": True, "status": "active"},
    )
    return StrategyRead.model_validate(strategy)


@router.post("/strategies/{strategy_id}/disable", response_model=StrategyRead, tags=["strategies"])
def post_disable_strategy(
    strategy_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("manage_strategies")),
) -> StrategyRead:
    strategy = update_strategy(db, strategy_id, StrategyUpdate(enabled=False, status="paused"))
    if strategy is None:
        raise HTTPException(status_code=404, detail="Strategy not found")
    audit_route_event(
        db,
        request,
        action="strategy_change",
        module="strategy",
        status="success",
        message=f"Disabled strategy {strategy.name}.",
        user=user,
        entity_type="strategy",
        entity_id=strategy.id,
        details={"enabled": False, "status": "paused"},
    )
    return StrategyRead.model_validate(strategy)


@router.delete("/strategies/{strategy_id}", tags=["strategies"])
def delete_strategy_endpoint(
    strategy_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("manage_strategies")),
) -> dict[str, bool]:
    if not delete_strategy(db, strategy_id):
        raise HTTPException(status_code=404, detail="Strategy not found")
    audit_route_event(
        db,
        request,
        action="strategy_change",
        module="strategy",
        status="success",
        message=f"Deleted strategy {strategy_id}.",
        user=user,
        entity_type="strategy",
        entity_id=strategy_id,
    )
    return {"deleted": True}


@router.get("/risk-settings", response_model=list[RiskSettingRead], tags=["risk"])
def get_risk_settings(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("risk-settings:view")),
) -> list[RiskSettingRead]:
    return [RiskSettingRead.model_validate(ensure_default_risk_settings(db))]


@router.patch("/risk-settings/{risk_setting_id}", response_model=RiskSettingRead, tags=["risk"])
def patch_risk_settings(
    risk_setting_id: int,
    payload: RiskSettingUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("risk-settings:update")),
) -> RiskSettingRead:
    settings = update_risk_settings(db, risk_setting_id, payload)
    if settings is None:
        raise HTTPException(status_code=404, detail="Risk settings not found")

    audit_route_event(
        db,
        request,
        action="risk_setting_change",
        module="risk",
        status="success",
        message=f"Updated risk settings {settings.name}.",
        user=user,
        entity_type="risk_setting",
        entity_id=settings.id,
        details=payload.model_dump(exclude_unset=True),
    )
    return RiskSettingRead.model_validate(settings)


@router.get("/risk/summary", response_model=RiskSummaryResponse, tags=["risk"])
def get_risk_summary(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("risk-settings:view")),
) -> RiskSummaryResponse:
    return risk_summary(db)


@router.post("/risk/validate-trade", response_model=RiskTradeValidationResponse, tags=["risk"])
def post_risk_validate_trade(
    payload: RiskTradeValidationRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("risk-settings:view")),
) -> RiskTradeValidationResponse:
    return validate_trade_request(db, payload)


@router.post("/risk/position-size", response_model=PositionSizeResponse, tags=["risk"])
def post_risk_position_size(
    payload: PositionSizeRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("risk-settings:view")),
) -> PositionSizeResponse:
    return calculate_position_size(db, payload)


@router.get("/risk/limits", response_model=RiskLimitsRead, tags=["risk"])
def get_risk_limits_endpoint(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("risk-settings:view")),
) -> RiskLimitsRead:
    return get_risk_limits(db)


@router.put("/risk/limits", response_model=RiskLimitsRead, tags=["risk"])
def put_risk_limits(
    payload: RiskLimitsUpdate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("risk-settings:update")),
) -> RiskLimitsRead:
    limits = update_risk_limits(db, payload)
    audit_route_event(
        db,
        request,
        action="risk_setting_change",
        module="risk",
        status="success",
        message="Updated risk limits.",
        user=user,
        details=payload.model_dump(exclude_unset=True),
    )
    return limits


@router.post("/risk/circuit-breaker/enable", response_model=RiskLimitsRead, tags=["risk"])
def post_enable_circuit_breaker(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("risk-settings:update")),
) -> RiskLimitsRead:
    limits = set_circuit_breaker(db, True)
    audit_route_event(
        db,
        request,
        action="risk_setting_change",
        module="risk",
        status="success",
        message="Enabled risk circuit breaker.",
        user=user,
        details={"emergency_stop": True},
    )
    return limits


@router.post("/risk/circuit-breaker/disable", response_model=RiskLimitsRead, tags=["risk"])
def post_disable_circuit_breaker(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("risk-settings:update")),
) -> RiskLimitsRead:
    limits = set_circuit_breaker(db, False)
    audit_route_event(
        db,
        request,
        action="risk_setting_change",
        module="risk",
        status="success",
        message="Disabled risk circuit breaker.",
        user=user,
        details={"emergency_stop": False},
    )
    return limits


@router.post("/risk/monte-carlo", response_model=MonteCarloResponse, tags=["risk"])
def post_risk_monte_carlo(
    payload: MonteCarloRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("risk-settings:view")),
) -> MonteCarloResponse:
    return run_monte_carlo(db, payload)


@router.get("/risk/monte-carlo/{run_id}", response_model=MonteCarloResponse, tags=["risk"])
def get_risk_monte_carlo(
    run_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("risk-settings:view")),
) -> MonteCarloResponse:
    run = get_monte_carlo_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Monte Carlo run not found")
    return run


@router.get("/backtests", response_model=list[BacktestRunRead], tags=["backtests"])
def get_backtests(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("backtests:view")),
) -> list[BacktestRunRead]:
    return [backtest_to_schema(run) for run in list_backtest_runs(db, limit)]


@router.post("/backtests/run", response_model=BacktestRunRead, tags=["backtests"])
def post_backtest_run(
    payload: BacktestRunRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("backtests:run")),
) -> BacktestRunRead:
    try:
        run = run_backtest(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return backtest_to_schema(run)


@router.post("/backtests/walk-forward", response_model=WalkForwardRunRead, tags=["backtests"])
def post_walk_forward_backtest(
    payload: WalkForwardRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("backtests:run")),
) -> WalkForwardRunRead:
    try:
        return run_walk_forward(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/backtests/walk-forward/{run_id}", response_model=WalkForwardRunRead, tags=["backtests"])
def get_walk_forward_backtest(
    run_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("backtests:view")),
) -> WalkForwardRunRead:
    run = get_walk_forward_run(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Walk-forward run not found")
    return run


@router.get("/backtests/{run_id}/report", response_model=BacktestReport, tags=["backtests"])
def get_backtest_report(
    run_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("backtests:view")),
) -> BacktestReport:
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
    _user: User = Depends(require_permission("ai-analyses:create")),
) -> AIAnalysisResponse:
    try:
        return analyze_signal(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ai/analyses", response_model=list[AIAnalysisResponse], tags=["ai"])
def get_ai_analyses(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("ai-analyses:view")),
) -> list[AIAnalysisResponse]:
    return [analysis_to_response(record) for record in list_ai_analyses(db, limit)]


@router.get("/ai/provider", response_model=AIProviderStatusResponse, tags=["ai"])
def get_ai_provider_status(
    _user: User = Depends(require_permission("ai-models:view")),
) -> AIProviderStatusResponse:
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
def patch_ai_provider(
    payload: AIProviderStatusRequest,
    _user: User = Depends(require_permission("ai-provider:manage")),
) -> AIProviderStatusResponse:
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
    _user: User = Depends(require_permission("ai-analyses:view")),
) -> AIAnalysisResponse:
    record = get_ai_analysis(db, analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="AI analysis not found")

    return analysis_to_response(record)


@router.get("/ai/models", response_model=list[AIModelRead], tags=["ai"])
def get_ai_models(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("ai-models:view")),
) -> list[AIModelRead]:
    return [AIModelRead.model_validate(model) for model in ModelRegistryService(db).list_models()]


@router.post("/ai/train", response_model=AIModelRead, tags=["ai"])
def post_ai_train(
    payload: AIModelTrainRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("ai-models:manage")),
) -> AIModelRead:
    try:
        model = train_model(
            db,
            name=payload.name,
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            lookback=payload.lookback,
            model_type=payload.model_type,
            training_params=payload.training_params,
            selected_features=payload.selected_features or None,
        )
        audit_route_event(
            db,
            request,
            action="model_training",
            module="ai",
            status="success",
            message=f"Trained AI model {model.name}.",
            user=user,
            entity_type="ai_model",
            entity_id=model.id,
            details={"name": model.name, "symbol": model.symbol, "timeframe": model.timeframe, "model_type": model.model_type},
        )
        return AIModelRead.model_validate(model)
    except ValueError as exc:
        audit_route_event(
            db,
            request,
            action="model_training",
            module="ai",
            status="failed",
            message=f"Failed AI model training for {payload.name}: {exc}",
            user=user,
            severity="error",
            details=payload.model_dump(),
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ai/models/train", response_model=AIModelRead, tags=["ai"])
def post_ai_model_train(
    payload: AIModelTrainRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("train_models")),
) -> AIModelRead:
    try:
        model = train_model(
            db,
            name=payload.name,
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            lookback=payload.lookback,
            model_type=payload.model_type,
            training_params=payload.training_params,
            selected_features=payload.selected_features or None,
        )
        audit_route_event(
            db,
            request,
            action="model_training",
            module="ai",
            status="success",
            message=f"Trained AI model {model.name}.",
            user=user,
            entity_type="ai_model",
            entity_id=model.id,
            details={"name": model.name, "symbol": model.symbol, "timeframe": model.timeframe, "model_type": model.model_type},
        )
        return AIModelRead.model_validate(model)
    except ValueError as exc:
        audit_route_event(
            db,
            request,
            action="model_training",
            module="ai",
            status="failed",
            message=f"Failed AI model training for {payload.name}: {exc}",
            user=user,
            severity="error",
            details=payload.model_dump(),
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ai/models/{model_id}", response_model=AIModelRead, tags=["ai"])
def get_ai_model(
    model_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("ai-models:view")),
) -> AIModelRead:
    try:
        return AIModelRead.model_validate(ModelRegistryService(db).get_model(model_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/ai/models/{model_id}/retrain", response_model=AIModelRead, tags=["ai"])
def post_ai_model_retrain(
    model_id: int,
    payload: AIModelRetrainRequest | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("train_models")),
) -> AIModelRead:
    payload = payload or AIModelRetrainRequest()
    try:
        return AIModelRead.model_validate(
            retrain_model(db, model_id, lookback=payload.lookback, training_params=payload.training_params)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ai/models/{model_id}/deploy", response_model=AIModelRead, tags=["ai"])
def post_ai_model_deploy(
    model_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("train_models")),
) -> AIModelRead:
    try:
        model = deploy_model(db, model_id)
        audit_route_event(
            db,
            request,
            action="model_activation",
            module="ai",
            status="success",
            message=f"Deployed AI model {model.name}.",
            user=user,
            entity_type="ai_model",
            entity_id=model.id,
            details={"name": model.name, "symbol": model.symbol, "status": model.status, "deployed": model.deployed},
        )
        return AIModelRead.model_validate(model)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/ai/models/{model_id}/activate", response_model=AIModelRead, tags=["ai"])
def post_ai_model_activate(
    model_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("ai-models:manage")),
) -> AIModelRead:
    try:
        model = ModelRegistryService(db).activate(model_id)
        audit_route_event(
            db,
            request,
            action="model_activation",
            module="ai",
            status="success",
            message=f"Activated AI model {model.name}.",
            user=user,
            entity_type="ai_model",
            entity_id=model.id,
            details={"name": model.name, "symbol": model.symbol, "status": model.status, "deployed": model.deployed},
        )
        return AIModelRead.model_validate(model)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/ai/models/{model_id}/disable", response_model=AIModelRead, tags=["ai"])
def post_ai_model_disable(
    model_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("train_models")),
) -> AIModelRead:
    try:
        return AIModelRead.model_validate(disable_model(db, model_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/ai/evaluation/{model_id}", response_model=AIModelEvaluationRead, tags=["ai"])
def get_ai_model_evaluation(
    model_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("ai-models:view")),
) -> AIModelEvaluationRead:
    try:
        return AIModelEvaluationRead.model_validate(ModelRegistryService(db).evaluation(model_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/ai/models/compare", response_model=list[AIModelComparison], tags=["ai"])
def post_ai_model_compare(
    payload: AIModelCompareRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("ai-models:view")),
) -> list[AIModelComparison]:
    try:
        return [AIModelComparison.model_validate(item) for item in compare_models(db, payload.model_ids)]
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/ai/models/{model_id}/predict", response_model=AIModelPrediction, tags=["ai"])
def post_ai_model_predict(
    model_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("ai-models:view")),
) -> AIModelPrediction:
    try:
        return AIModelPrediction.model_validate(predict_ai_model(db, model_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ai/predict", response_model=AIModelPrediction, tags=["ai"])
def post_ai_predict(
    payload: AIPredictionRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("ai-models:view")),
) -> AIModelPrediction:
    try:
        return AIModelPrediction.model_validate(
            PredictionService(db).predict(
                symbol=payload.symbol,
                timeframe=payload.timeframe,
                model_id=payload.model_id,
                model_type=payload.model_type,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/brokers", response_model=list[BrokerStatusRead], tags=["brokers"])
def get_brokers(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("api-credentials:manage")),
) -> list[BrokerStatusRead]:
    return BrokerService(db).list_brokers()


@router.post("/brokers/connect", response_model=BrokerConnectionResponse, tags=["brokers"])
def post_broker_connect(
    payload: BrokerConnectRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("api-credentials:manage")),
) -> BrokerConnectionResponse:
    try:
        broker = BrokerService(db).connect(payload.broker)
        audit_route_event(
            db,
            request,
            action="broker_connection",
            module="brokers",
            status="success",
            message=f"Connected broker {payload.broker}.",
            user=user,
            details={"broker": payload.broker},
        )
        return BrokerConnectionResponse(broker=broker)
    except ValueError as exc:
        audit_route_event(
            db,
            request,
            action="broker_connection",
            module="brokers",
            status="failed",
            message=f"Failed broker connection for {payload.broker}: {exc}",
            user=user,
            severity="error",
            details={"broker": payload.broker},
        )
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BrokerAdapterError as exc:
        audit_route_event(
            db,
            request,
            action="broker_connection",
            module="brokers",
            status="failed",
            message=f"Failed broker connection for {payload.broker}: {exc}",
            user=user,
            severity="error",
            details={"broker": payload.broker},
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/brokers/disconnect", response_model=BrokerConnectionResponse, tags=["brokers"])
def post_broker_disconnect(
    payload: BrokerDisconnectRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("api-credentials:manage")),
) -> BrokerConnectionResponse:
    try:
        broker = BrokerService(db).disconnect(payload.broker)
        audit_route_event(
            db,
            request,
            action="broker_disconnection",
            module="brokers",
            status="success",
            message=f"Disconnected broker {payload.broker}.",
            user=user,
            details={"broker": payload.broker},
        )
        return BrokerConnectionResponse(broker=broker)
    except ValueError as exc:
        audit_route_event(
            db,
            request,
            action="broker_disconnection",
            module="brokers",
            status="failed",
            message=f"Failed broker disconnection for {payload.broker}: {exc}",
            user=user,
            severity="error",
            details={"broker": payload.broker},
        )
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/brokers/{broker}/balance", response_model=BrokerBalanceResponse, tags=["brokers"])
def get_broker_balance(
    broker: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("api-credentials:manage")),
) -> BrokerBalanceResponse:
    try:
        return BrokerService(db).balance(broker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BrokerAdapterError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/brokers/{broker}/positions", response_model=BrokerPositionsResponse, tags=["brokers"])
def get_broker_positions(
    broker: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("api-credentials:manage")),
) -> BrokerPositionsResponse:
    try:
        return BrokerService(db).positions(broker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BrokerAdapterError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/brokers/{broker}/orders", response_model=BrokerOrdersResponse, tags=["brokers"])
def get_broker_orders(
    broker: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("api-credentials:manage")),
) -> BrokerOrdersResponse:
    try:
        return BrokerService(db).orders(broker)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BrokerAdapterError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/brokers/{broker}/orders", response_model=BrokerOrderRead, tags=["brokers"])
def post_broker_order(
    broker: str,
    payload: BrokerOrderCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("api-credentials:manage")),
) -> BrokerOrderRead:
    try:
        order = BrokerService(db).place_order(broker, payload)
        audit_route_event(
            db,
            request,
            action="trade_execution",
            module="trading",
            status="success",
            message=f"Submitted {broker} order for {payload.symbol}.",
            user=user,
            details={"broker": broker, "symbol": payload.symbol, "side": payload.side, "quantity": payload.quantity},
        )
        return order
    except ValueError as exc:
        audit_route_event(
            db,
            request,
            action="trade_rejection",
            module="trading",
            status="rejected",
            message=f"Rejected {broker} order for {payload.symbol}: {exc}",
            user=user,
            severity="warning",
            details={"broker": broker, "symbol": payload.symbol, "side": payload.side, "quantity": payload.quantity},
        )
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BrokerNotImplementedError as exc:
        audit_route_event(
            db,
            request,
            action="trade_rejection",
            module="trading",
            status="rejected",
            message=f"Rejected {broker} order for {payload.symbol}: {exc}",
            user=user,
            severity="warning",
            details={"broker": broker, "symbol": payload.symbol, "side": payload.side, "quantity": payload.quantity},
        )
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except BrokerAdapterError as exc:
        audit_route_event(
            db,
            request,
            action="trade_rejection",
            module="trading",
            status="rejected",
            message=f"Rejected {broker} order for {payload.symbol}: {exc}",
            user=user,
            severity="warning",
            details={"broker": broker, "symbol": payload.symbol, "side": payload.side, "quantity": payload.quantity},
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/brokers/{broker}/orders/{order_id}", response_model=BrokerCancelResponse, tags=["brokers"])
def delete_broker_order(
    broker: str,
    order_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("api-credentials:manage")),
) -> BrokerCancelResponse:
    try:
        return BrokerService(db).cancel_order(broker, order_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BrokerNotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except BrokerAdapterError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/paper/account", response_model=PaperTradingAccountRead, tags=["paper-trading"])
def get_paper_account(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("portfolio:view")),
) -> PaperTradingAccountRead:
    return PaperTradingService(db).get_account()


@router.post("/paper/orders", response_model=PaperTradingOrderRead, tags=["paper-trading"])
def post_paper_trading_order(
    payload: PaperTradingOrderCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("orders:create")),
) -> PaperTradingOrderRead:
    try:
        order = PaperTradingService(db).create_order(payload)
        audit_route_event(
            db,
            request,
            action="trade_execution" if order.status != "rejected" else "trade_rejection",
            module="trading",
            status="success" if order.status != "rejected" else "rejected",
            message=f"Paper trading order {order.status} for {order.symbol}.",
            user=user,
            entity_type="paper_order",
            entity_id=order.id,
            severity="info" if order.status != "rejected" else "warning",
            details={"symbol": order.symbol, "side": order.side, "quantity": order.quantity, "status": order.status},
        )
        return order
    except ValueError as exc:
        audit_route_event(
            db,
            request,
            action="trade_rejection",
            module="trading",
            status="rejected",
            message=f"Rejected paper trading order: {exc}",
            user=user,
            severity="warning",
            details=payload.model_dump(),
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/paper/orders", response_model=list[PaperTradingOrderRead], tags=["paper-trading"])
def get_paper_trading_orders(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("orders:view")),
) -> list[PaperTradingOrderRead]:
    return PaperTradingService(db).list_orders(limit)


@router.get("/paper/positions", response_model=list[PaperTradingPositionRead], tags=["paper-trading"])
def get_paper_trading_positions(
    status: str = Query("open", pattern="^(open|closed|all)$"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("positions:view")),
) -> list[PaperTradingPositionRead]:
    return PaperTradingService(db).list_positions(status)


@router.post("/paper/positions/{position_id}/close", response_model=PaperTradingPositionRead, tags=["paper-trading"])
def post_close_paper_trading_position(
    position_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("positions:manage")),
) -> PaperTradingPositionRead:
    try:
        position = PaperTradingService(db).close_position(position_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if position is None:
        raise HTTPException(status_code=404, detail="Paper position not found")
    return position


@router.get("/paper/performance", response_model=PaperTradingPerformanceResponse, tags=["paper-trading"])
def get_paper_trading_performance(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("portfolio:view")),
) -> PaperTradingPerformanceResponse:
    return PaperTradingService(db).performance()


@router.post("/paper/reset", response_model=PaperTradingResetResponse, tags=["paper-trading"])
def post_paper_trading_reset(
    payload: PaperTradingResetRequest | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("orders:manage")),
) -> PaperTradingResetResponse:
    payload = payload or PaperTradingResetRequest()
    return PaperTradingService(db).reset(payload.starting_balance)


@router.get("/orders", response_model=list[PaperOrderRead], tags=["paper-trading"])
def get_orders(
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, pattern="^(filled|rejected|cancelled|all)$"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("orders:view")),
) -> list[PaperOrderRead]:
    return [order_to_schema(order) for order in list_paper_orders(db, limit, status)]


@router.post("/orders/paper", response_model=PaperOrderRead, tags=["paper-trading"])
def post_paper_order(
    payload: PaperOrderRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("orders:create")),
) -> PaperOrderRead:
    try:
        order = create_paper_order(db, payload)
        order_read = order_to_schema(order)
        audit_route_event(
            db,
            request,
            action="trade_execution" if order.status == "filled" else "trade_rejection",
            module="trading",
            status="success" if order.status == "filled" else "rejected",
            message=f"Paper order {order.status} for {order.symbol_ref.symbol}.",
            user=user,
            entity_type="paper_order",
            entity_id=order.id,
            severity="info" if order.status == "filled" else "warning",
            details={
                "symbol": order.symbol_ref.symbol,
                "side": order.side,
                "quantity": order.quantity,
                "status": order.status,
                "risk_status": order.risk_status,
                "risk_message": order.risk_message,
            },
        )
        return order_read
    except ValueError as exc:
        audit_route_event(
            db,
            request,
            action="trade_rejection",
            module="trading",
            status="rejected",
            message=f"Rejected paper order: {exc}",
            user=user,
            severity="warning",
            details=payload.model_dump(),
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/orders/{order_id}/cancel", response_model=PaperOrderRead, tags=["paper-trading"])
def post_cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("orders:manage")),
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
    _user: User = Depends(require_permission("positions:view")),
) -> list[PaperPositionRead]:
    return [position_to_schema(position) for position in list_paper_positions(db, status)]


@router.post("/positions/{position_id}/close", response_model=PaperPositionRead, tags=["paper-trading"])
def post_close_position(
    position_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("positions:manage")),
) -> PaperPositionRead:
    try:
        position = close_paper_position(db, position_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if position is None:
        raise HTTPException(status_code=404, detail="Paper position not found")

    return position_to_schema(position)


@router.get("/analytics/performance", response_model=PerformanceSummaryResponse, tags=["analytics"])
def get_analytics_performance(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("portfolio:view")),
) -> PerformanceSummaryResponse:
    return get_performance_summary(db)


@router.get("/analytics/equity-curve", response_model=AnalyticsEquityCurveResponse, tags=["analytics"])
def get_analytics_equity_curve_endpoint(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("portfolio:view")),
) -> AnalyticsEquityCurveResponse:
    return get_analytics_equity_curve(db)


@router.get("/analytics/strategies", response_model=StrategyComparisonResponse, tags=["analytics"])
def get_analytics_strategies(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("portfolio:view")),
) -> StrategyComparisonResponse:
    return get_strategy_comparison(db)


@router.get("/analytics/trades", response_model=list[AnalyticsTradeRead], tags=["analytics"])
def get_analytics_trades_endpoint(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("portfolio:view")),
) -> list[AnalyticsTradeRead]:
    return list(reversed(get_analytics_trades(db, limit=limit)))


@router.get("/portfolio/summary", response_model=PortfolioSummaryResponse, tags=["portfolio"])
def get_portfolio_summary_endpoint(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("portfolio:view")),
) -> PortfolioSummaryResponse:
    return get_portfolio_summary(db)


@router.get("/portfolio/performance", response_model=PortfolioPerformanceResponse, tags=["portfolio"])
def get_portfolio_performance_endpoint(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("portfolio:view")),
) -> PortfolioPerformanceResponse:
    return get_portfolio_performance(db)


@router.get("/portfolio/exposure", response_model=PortfolioExposureResponse, tags=["portfolio"])
def get_portfolio_exposure_endpoint(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("portfolio:view")),
) -> PortfolioExposureResponse:
    return get_portfolio_exposure(db)


@router.get("/portfolio/allocation", response_model=PortfolioAllocationResponse, tags=["portfolio"])
def get_portfolio_allocation_endpoint(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("portfolio:view")),
) -> PortfolioAllocationResponse:
    return get_portfolio_allocation(db)


@router.get("/portfolio/pnl", response_model=PortfolioPnlResponse, tags=["portfolio"])
def get_portfolio_pnl_endpoint(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("portfolio:view")),
) -> PortfolioPnlResponse:
    return get_portfolio_pnl(db)


@router.get("/portfolio/equity-curve", response_model=EquityCurveResponse, tags=["portfolio"])
def get_equity_curve_endpoint(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("portfolio:view")),
) -> EquityCurveResponse:
    return get_equity_curve(db)


def audit_events_response(
    db: Session,
    *,
    limit: int = Query(50, ge=1, le=200),
    module: str | None = None,
    action_type: str | None = None,
    status: str | None = None,
    user: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    event_type: str | None = None,
    severity: str | None = None,
    entity_type: str | None = None,
) -> list[AuditEventRead]:
    return [
        audit_event_to_schema(event)
        for event in list_audit_events(
            db,
            limit=limit,
            event_type=event_type,
            severity=severity,
            entity_type=entity_type,
            module=module,
            action_type=action_type,
            status=status,
            user=user,
            start_date=start_date,
            end_date=end_date,
        )
    ]


@router.get("/audit", response_model=list[AuditEventRead], tags=["audit"])
def get_audit(
    limit: int = Query(100, ge=1, le=500),
    module: str | None = Query(None),
    action_type: str | None = Query(None),
    status: str | None = Query(None),
    user: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("audit:view")),
) -> list[AuditEventRead]:
    return audit_events_response(
        db,
        limit=limit,
        module=module,
        action_type=action_type,
        status=status,
        user=user,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/audit/trades", response_model=list[AuditEventRead], tags=["audit"])
def get_trade_audit(
    limit: int = Query(100, ge=1, le=500),
    action_type: str | None = Query(None),
    status: str | None = Query(None),
    user: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("audit:view")),
) -> list[AuditEventRead]:
    return audit_events_response(db, limit=limit, module="trading", action_type=action_type, status=status, user=user, start_date=start_date, end_date=end_date)


@router.get("/audit/users", response_model=list[AuditEventRead], tags=["audit"])
def get_user_audit(
    limit: int = Query(100, ge=1, le=500),
    action_type: str | None = Query(None),
    status: str | None = Query(None),
    user: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("audit:view")),
) -> list[AuditEventRead]:
    return audit_events_response(db, limit=limit, module="users", action_type=action_type, status=status, user=user, start_date=start_date, end_date=end_date)


@router.get("/audit/ai", response_model=list[AuditEventRead], tags=["audit"])
def get_ai_audit(
    limit: int = Query(100, ge=1, le=500),
    action_type: str | None = Query(None),
    status: str | None = Query(None),
    user: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("audit:view")),
) -> list[AuditEventRead]:
    return audit_events_response(db, limit=limit, module="ai", action_type=action_type, status=status, user=user, start_date=start_date, end_date=end_date)


@router.get("/audit/risk", response_model=list[AuditEventRead], tags=["audit"])
def get_risk_audit(
    limit: int = Query(100, ge=1, le=500),
    action_type: str | None = Query(None),
    status: str | None = Query(None),
    user: str | None = Query(None),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("audit:view")),
) -> list[AuditEventRead]:
    return audit_events_response(db, limit=limit, module="risk", action_type=action_type, status=status, user=user, start_date=start_date, end_date=end_date)


@router.get("/audit/events", response_model=list[AuditEventRead], tags=["audit"])
def get_audit_events(
    limit: int = Query(50, ge=1, le=200),
    event_type: str | None = Query(None),
    severity: str | None = Query(None, pattern="^(info|warning|error)$"),
    entity_type: str | None = Query(None),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("audit:view")),
) -> list[AuditEventRead]:
    return audit_events_response(db, limit=limit, event_type=event_type, severity=severity, entity_type=entity_type)


@router.get("/notifications", response_model=list[NotificationRead], tags=["notifications"])
def get_notifications(
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("notifications:view")),
) -> list[NotificationRead]:
    return [NotificationRead.model_validate(notification) for notification in list_notifications(db, unread_only)]


@router.post("/notifications", response_model=NotificationRead, tags=["notifications"])
def post_notification(
    payload: NotificationCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("view_logs")),
) -> NotificationRead:
    return NotificationRead.model_validate(create_notification(db, payload))


@router.post("/notifications/mark-read", response_model=NotificationMarkReadResponse, tags=["notifications"])
def post_notifications_mark_read(
    payload: NotificationMarkReadRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("notifications:view")),
) -> NotificationMarkReadResponse:
    return mark_notifications_read(db, payload)


@router.get("/notifications/settings", response_model=NotificationSettingsRead, tags=["notifications"])
def get_notifications_settings(
    _user: User = Depends(require_permission("notifications:view")),
) -> NotificationSettingsRead:
    return get_notification_settings()


@router.put("/notifications/settings", response_model=NotificationSettingsRead, tags=["notifications"])
def put_notifications_settings(
    payload: NotificationSettingsUpdate,
    _user: User = Depends(require_permission("notifications:manage")),
) -> NotificationSettingsRead:
    return update_notification_settings(payload)


@router.post("/notifications/{notification_id}/read", response_model=NotificationRead, tags=["notifications"])
def post_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("notifications:view")),
) -> NotificationRead:
    notification = mark_notification_read(db, notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return NotificationRead.model_validate(notification)


@router.get("/logs", response_model=list[SystemLogRead], tags=["logs"])
def get_logs(
    limit: int = Query(100, ge=1, le=500),
    level: str | None = Query(None, pattern="^(info|warning|error)$"),
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("logs:view")),
) -> list[SystemLogRead]:
    return [SystemLogRead.model_validate(log) for log in list_system_logs(db, limit, level)]


@router.get("/indicators/preview", tags=["indicators"])
def indicator_preview(
    _user: User = Depends(require_permission("market-data:view")),
) -> dict[str, float]:
    return moving_average_snapshot([101.2, 102.4, 101.9, 103.1, 104.8, 104.2])


def role_to_schema(role) -> RoleRead:
    permissions = [
        PermissionRead.model_validate(assignment.permission_ref)
        for assignment in sorted(role.permission_assignments, key=lambda item: item.permission_ref.name)
    ]
    return RoleRead(
        id=role.id,
        name=role.name,
        slug=role.slug,
        description=role.description,
        is_system=role.is_system,
        permissions=permissions,
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


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


async def _websocket_token_allowed(websocket: WebSocket, token: str | None) -> bool:
    if token and not decode_jwt(token):
        await websocket.close(code=1008)
        return False
    return True


def _prices_stream_payload() -> list[dict]:
    with SessionLocal() as db:
        prices = []
        for symbol in list_symbols(db):
            candles = list_candles(db, symbol.symbol, timeframe=settings.market_sync_timeframe, limit=2)
            latest = candles[-1] if candles else None
            previous = candles[-2] if len(candles) > 1 else None
            if latest is None:
                continue
            change_pct = ((latest.close - previous.close) / previous.close) if previous and previous.close else 0.0
            prices.append(
                {
                    "symbol": symbol.symbol,
                    "price": latest.close,
                    "change_pct": round(change_pct, 6),
                    "timeframe": latest.timeframe,
                    "updated_at": latest.opened_at.isoformat(),
                }
            )
        return prices


def _signals_stream_payload() -> list[dict]:
    with SessionLocal() as db:
        return [
            item.model_dump(mode="json")
            for item in get_scanner_results(db, timeframe=settings.market_sync_timeframe)
        ]


def _orders_stream_payload() -> list[dict]:
    with SessionLocal() as db:
        return [order.model_dump(mode="json") for order in PaperTradingService(db).list_orders(limit=100)]


def _positions_stream_payload() -> list[dict]:
    with SessionLocal() as db:
        return [position.model_dump(mode="json") for position in PaperTradingService(db).list_positions(status="all")]


def _portfolio_stream_payload() -> dict:
    with SessionLocal() as db:
        return get_portfolio_summary(db).model_dump(mode="json")


def _notifications_stream_payload() -> list[dict]:
    with SessionLocal() as db:
        return [NotificationRead.model_validate(notification).model_dump(mode="json") for notification in list_notifications(db, unread_only=False)]


def _filter_scanner_results(
    results: list[ScannerRead],
    signal: str | None,
    min_confidence: float | None,
    risk_level: str | None,
) -> list[ScannerRead]:
    filtered = results
    if signal:
        filtered = [result for result in filtered if result.signal == signal]
    if min_confidence is not None:
        filtered = [result for result in filtered if result.confidence >= min_confidence]
    if risk_level:
        filtered = [result for result in filtered if result.risk_level == risk_level]
    return filtered


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
        spread=candle.spread,
    )


def tick_to_schema(tick: MarketTick) -> MarketTickRead:
    return MarketTickRead(
        id=tick.id,
        symbol=tick.symbol_ref.symbol,
        exchange=tick.exchange,
        tick_time=tick.tick_time,
        bid=tick.bid,
        ask=tick.ask,
        price=tick.price,
        volume=tick.volume,
        spread=tick.spread,
        source=tick.source,
    )


def trade_to_schema(trade: MarketTrade) -> MarketTradeRead:
    return MarketTradeRead(
        id=trade.id,
        symbol=trade.symbol_ref.symbol,
        exchange=trade.exchange,
        trade_id=trade.trade_id,
        traded_at=trade.traded_at,
        price=trade.price,
        quantity=trade.quantity,
        side=trade.side,
        source=trade.source,
    )


def order_book_to_schema(snapshot: MarketOrderBookSnapshot) -> MarketOrderBookRead:
    return MarketOrderBookRead(
        id=snapshot.id,
        symbol=snapshot.symbol_ref.symbol,
        exchange=snapshot.exchange,
        captured_at=snapshot.captured_at,
        bids=snapshot.bids,
        asks=snapshot.asks,
        best_bid=snapshot.best_bid,
        best_ask=snapshot.best_ask,
        spread=snapshot.spread,
        depth=snapshot.depth,
        source=snapshot.source,
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

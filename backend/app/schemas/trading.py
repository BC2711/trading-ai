from datetime import datetime

from pydantic import BaseModel, Field


class SymbolCreate(BaseModel):
    symbol: str = Field(..., examples=["BTCUSDT"])
    base_asset: str = Field(..., examples=["BTC"])
    quote_asset: str = Field(..., examples=["USDT"])
    market: str = "crypto"
    exchange: str = "binance_testnet"


class SymbolRead(SymbolCreate):
    id: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MarketCandleCreate(BaseModel):
    symbol: str = Field(..., examples=["BTCUSDT"])
    timeframe: str = "15m"
    opened_at: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketCandleRead(BaseModel):
    id: int
    symbol: str
    timeframe: str
    opened_at: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketDataSyncRequest(BaseModel):
    symbols: list[str] = Field(default_factory=lambda: ["BTCUSDT", "ETHUSDT"])
    timeframe: str = "15m"
    limit: int = Field(default=500, ge=1, le=1000)
    regenerate_signals: bool = True


class MarketDataSyncResult(BaseModel):
    symbol: str
    timeframe: str
    fetched: int
    inserted: int
    updated: int


class MarketDataSyncResponse(BaseModel):
    provider: str
    timeframe: str
    results: list[MarketDataSyncResult]
    signals: list["SignalRead"] = Field(default_factory=list)


class MarketDataRefreshRequest(BaseModel):
    symbols: list[str] | None = None
    timeframe: str | None = None
    limit: int | None = Field(default=None, ge=1, le=1000)
    regenerate_signals: bool | None = None


class MarketDataRefreshResponse(BaseModel):
    status: str
    provider: str
    symbols: list[str]
    timeframe: str
    limit: int
    results: list[MarketDataSyncResult]
    generated_signal_count: int
    error: str | None = None


class MarketDataTaskResponse(BaseModel):
    task_id: str
    status: str


class MarketDataScheduleResponse(BaseModel):
    enabled: bool
    job_id: str
    interval_minutes: int
    symbols: list[str]
    timeframe: str
    limit: int
    regenerate_signals: bool


class SignalRead(BaseModel):
    id: int
    symbol: str
    direction: str
    confidence: float
    timeframe: str
    reason: str
    status: str
    created_at: datetime


class SignalGenerateRequest(BaseModel):
    symbol: str | None = None
    timeframe: str = "15m"


class StrategyRead(BaseModel):
    id: int
    name: str
    description: str
    timeframe: str
    status: str
    parameters: dict = Field(default_factory=dict)
    enabled: bool = True
    performance: dict = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class StrategyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    description: str = Field(default="", max_length=500)
    timeframe: str = Field(default="15m", max_length=8)
    status: str = Field(default="draft", max_length=16)
    parameters: dict = Field(default_factory=dict)
    enabled: bool = True


class StrategyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    timeframe: str | None = Field(default=None, max_length=8)
    status: str | None = Field(default=None, max_length=16)
    parameters: dict | None = None
    enabled: bool | None = None
    performance: dict | None = None


class RiskSettingRead(BaseModel):
    id: int
    name: str
    max_risk_per_trade: float
    max_daily_loss: float
    max_open_trades: int
    max_symbol_exposure: float
    max_consecutive_losses: int
    emergency_stop: bool
    live_trading_enabled: bool
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RiskSettingUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    max_risk_per_trade: float | None = Field(default=None, gt=0, le=1)
    max_daily_loss: float | None = Field(default=None, gt=0, le=1)
    max_open_trades: int | None = Field(default=None, ge=1, le=50)
    max_symbol_exposure: float | None = Field(default=None, gt=0, le=1)
    max_consecutive_losses: int | None = Field(default=None, ge=1, le=20)
    emergency_stop: bool | None = None
    live_trading_enabled: bool | None = None
    status: str | None = Field(default=None, max_length=16)


class BacktestRunRequest(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "15m"
    initial_balance: float = Field(default=10000.0, gt=0)
    lookback: int = Field(default=240, ge=60, le=1000)
    fee_rate: float = Field(default=0.001, ge=0, le=0.05)
    slippage_rate: float = Field(default=0.0005, ge=0, le=0.05)
    spread_rate: float = Field(default=0.0002, ge=0, le=0.05)


class BacktestRunRead(BaseModel):
    id: int
    symbol: str
    strategy: str | None
    timeframe: str
    initial_balance: float
    ending_balance: float
    total_return: float
    win_rate: float
    max_drawdown: float
    fees: float
    slippage: float
    spread: float
    profit_factor: float
    sharpe_ratio: float
    equity_curve: list[dict] = Field(default_factory=list)
    trades_count: int
    winning_trades: int
    losing_trades: int
    status: str
    summary: str
    created_at: datetime


class AIAnalysisRequest(BaseModel):
    signal_id: int | None = None
    symbol: str = "BTCUSDT"
    timeframe: str = "15m"
    lookback: int = Field(default=120, ge=30, le=500)


class AIAnalysisResponse(BaseModel):
    id: int
    signal_id: int | None = None
    provider: str
    symbol: str
    timeframe: str
    direction: str
    confidence: float
    explanation: str
    reasoning: list[str]
    risk_notes: list[str]
    suggested_action: str
    indicators: dict[str, float]
    backtest_summary: str | None = None
    generated_at: datetime


class AIProviderStatusRequest(BaseModel):
    provider: str = Field(default="rules", pattern="^(rules|openai|ollama|local-llama)$")


class AIProviderStatusResponse(BaseModel):
    provider: str
    openai_available: bool
    available_providers: list[str]


class PaperOrderRequest(BaseModel):
    symbol: str = "BTCUSDT"
    side: str | None = Field(default=None, pattern="^(buy|sell)$")
    order_type: str = Field(default="market", pattern="^market$")
    quantity: float | None = Field(default=None, gt=0)
    signal_id: int | None = None
    ai_analysis_id: int | None = None


class PaperOrderRead(BaseModel):
    id: int
    symbol: str
    side: str
    order_type: str
    quantity: float
    requested_price: float
    fill_price: float | None
    status: str
    risk_status: str
    risk_message: str
    execution_mode: str = "paper"
    exchange_order_id: str | None = None
    failure_reason: str | None = None
    signal_id: int | None
    ai_analysis_id: int | None
    created_at: datetime
    filled_at: datetime | None


class PaperPositionRead(BaseModel):
    id: int
    symbol: str
    side: str
    quantity: float
    avg_entry_price: float
    mark_price: float
    unrealized_pnl: float
    realized_pnl: float
    status: str
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None


class PortfolioSummaryResponse(BaseModel):
    total_exposure: float
    open_positions: int
    filled_orders: int
    rejected_orders: int
    cancelled_orders: int
    unrealized_pnl: float
    realized_pnl: float
    closed_positions: int
    winning_positions: int
    losing_positions: int
    win_rate: float
    best_trade_pnl: float | None = None
    worst_trade_pnl: float | None = None


class EquityCurvePoint(BaseModel):
    timestamp: datetime
    equity: float
    realized_pnl: float


class EquityCurveResponse(BaseModel):
    starting_equity: float
    points: list[EquityCurvePoint]


class AuditEventRead(BaseModel):
    id: int
    event_type: str
    entity_type: str
    entity_id: int | None
    severity: str
    message: str
    metadata: dict
    created_at: datetime


class UserCreate(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    full_name: str = Field(..., min_length=2, max_length=160)
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="trader", pattern="^(admin|trader)$")


class UserLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserRead(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    role: str | None = Field(default=None, pattern="^(admin|trader)$")
    is_active: bool | None = None


class ApiCredentialCreate(BaseModel):
    exchange: str = Field(..., min_length=2, max_length=48)
    api_key: str = Field(..., min_length=3, max_length=255)
    api_secret: str = Field(..., min_length=3, max_length=1000)
    mode: str = Field(default="paper", pattern="^(paper|live)$")
    is_active: bool = True


class ApiCredentialRead(BaseModel):
    id: int
    exchange: str
    api_key: str
    mode: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiCredentialUpdate(BaseModel):
    exchange: str | None = Field(default=None, min_length=2, max_length=48)
    api_key: str | None = Field(default=None, min_length=3, max_length=255)
    api_secret: str | None = Field(default=None, min_length=3, max_length=1000)
    mode: str | None = Field(default=None, pattern="^(paper|live)$")
    is_active: bool | None = None


class AIModelTrainRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=160)
    symbol: str = "BTCUSDT"
    timeframe: str = "15m"
    lookback: int = Field(default=240, ge=80, le=1000)


class AIModelRead(BaseModel):
    id: int
    name: str
    symbol: str
    timeframe: str
    model_type: str
    model_path: str
    metrics: dict
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AIModelPrediction(BaseModel):
    model_id: int
    symbol: str
    direction: str
    confidence: float
    features: dict


class BacktestReport(BaseModel):
    run: BacktestRunRead
    equity_curve: list[dict]
    metrics: dict


class NotificationCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=180)
    message: str = Field(..., min_length=2, max_length=800)
    severity: str = Field(default="info", pattern="^(info|warning|error)$")


class NotificationRead(NotificationCreate):
    id: int
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SystemLogRead(BaseModel):
    id: int
    level: str
    source: str
    message: str
    context: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class NavigationChildRead(BaseModel):
    label: str
    href: str
    icon: str
    permission: str
    badge: str | None = None
    badge_color: str | None = None


class NavigationItemRead(BaseModel):
    label: str
    href: str
    icon: str
    permission: str
    children: list[NavigationChildRead] = Field(default_factory=list)


class CurrentUserRead(BaseModel):
    id: int
    name: str
    role: str
    permissions: list[str]

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
    spread: float = Field(default=0.0, ge=0)


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
    spread: float = 0.0


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


class MarketTickCreate(BaseModel):
    symbol: str
    exchange: str = "binance"
    tick_time: datetime
    price: float = Field(..., gt=0)
    volume: float = Field(default=0.0, ge=0)
    bid: float | None = Field(default=None, gt=0)
    ask: float | None = Field(default=None, gt=0)
    spread: float | None = Field(default=None, ge=0)
    source: str = "import"


class MarketTickRead(BaseModel):
    id: int
    symbol: str
    exchange: str
    tick_time: datetime
    bid: float | None
    ask: float | None
    price: float
    volume: float
    spread: float
    source: str


class MarketTradeCreate(BaseModel):
    symbol: str
    exchange: str = "binance"
    trade_id: str
    traded_at: datetime
    price: float = Field(..., gt=0)
    quantity: float = Field(..., gt=0)
    side: str = Field(default="unknown", pattern="^(buy|sell|unknown)$")
    source: str = "import"


class MarketTradeRead(BaseModel):
    id: int
    symbol: str
    exchange: str
    trade_id: str
    traded_at: datetime
    price: float
    quantity: float
    side: str
    source: str


class MarketOrderBookCreate(BaseModel):
    symbol: str
    exchange: str = "binance"
    captured_at: datetime
    bids: list[list[float]] = Field(default_factory=list)
    asks: list[list[float]] = Field(default_factory=list)
    source: str = "stream"


class MarketOrderBookRead(BaseModel):
    id: int
    symbol: str
    exchange: str
    captured_at: datetime
    bids: list[list[float]]
    asks: list[list[float]]
    best_bid: float | None
    best_ask: float | None
    spread: float
    depth: int
    source: str


class MarketDataImportRequest(BaseModel):
    market: str = Field(default="crypto", pattern="^(forex|stock|crypto|commodity|index|indices|commodities|stocks)$")
    exchange: str = "binance"
    timeframe: str = "15m"
    candles: list[MarketCandleCreate] = Field(default_factory=list)
    ticks: list[MarketTickCreate] = Field(default_factory=list)
    trades: list[MarketTradeCreate] = Field(default_factory=list)
    order_books: list[MarketOrderBookCreate] = Field(default_factory=list)


class MarketDataImportResponse(BaseModel):
    status: str
    candle_inserted: int
    candle_updated: int
    tick_inserted: int
    tick_updated: int
    trade_inserted: int
    trade_updated: int
    order_book_inserted: int
    order_book_updated: int


class MarketDataValidationIssue(BaseModel):
    symbol: str
    timeframe: str | None = None
    timestamp: datetime | None = None
    severity: str
    code: str
    message: str


class MissingCandleGap(BaseModel):
    symbol: str
    timeframe: str
    expected_at: datetime


class MarketDataValidationResponse(BaseModel):
    symbol: str
    timeframe: str
    checked_candles: int
    missing_candles: list[MissingCandleGap]
    issues: list[MarketDataValidationIssue]
    valid: bool


class MarketDataRepairRequest(BaseModel):
    symbol: str
    timeframe: str = "15m"
    limit: int = Field(default=500, ge=1, le=1000)
    repair_missing: bool = True
    regenerate_signals: bool = False


class MarketDataRepairResponse(BaseModel):
    status: str
    validation_before: MarketDataValidationResponse
    validation_after: MarketDataValidationResponse | None = None
    sync_result: MarketDataSyncResult | None = None
    error: str | None = None


class MarketDataStreamEvent(BaseModel):
    channel: str = Field(..., pattern="^(candles|ticks|order_books|trades)$")
    payload: MarketCandleCreate | MarketTickCreate | MarketOrderBookCreate | MarketTradeCreate


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
    max_weekly_loss: float = 0.08
    max_drawdown: float = 0.15
    max_open_trades: int
    max_symbol_exposure: float
    max_leverage: float = 1.0
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
    max_weekly_loss: float | None = Field(default=None, gt=0, le=1)
    max_drawdown: float | None = Field(default=None, gt=0, le=1)
    max_open_trades: int | None = Field(default=None, ge=1, le=50)
    max_symbol_exposure: float | None = Field(default=None, gt=0, le=1)
    max_leverage: float | None = Field(default=None, gt=0, le=100)
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
    model_type: str = Field(default="random_forest", pattern="^(random_forest|xgboost|lightgbm|lstm|gru|transformer)$")
    training_params: dict = Field(default_factory=dict)
    selected_features: list[str] = Field(default_factory=list)


class AIModelRetrainRequest(BaseModel):
    lookback: int | None = Field(default=None, ge=80, le=1000)
    training_params: dict = Field(default_factory=dict)


class AIModelRead(BaseModel):
    id: int
    name: str
    symbol: str
    timeframe: str
    model_type: str
    version: int = 1
    parent_model_id: int | None = None
    model_path: str
    metrics: dict
    feature_names: list[str] = Field(default_factory=list)
    training_params: dict = Field(default_factory=dict)
    target: str = "next_close_direction"
    deployed: bool = False
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AIModelPrediction(BaseModel):
    model_id: int
    symbol: str
    direction: str
    confidence: float
    features: dict


class AIPredictionRequest(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str | None = "15m"
    model_id: int | None = None
    model_type: str | None = Field(default=None, pattern="^(random_forest|xgboost|lightgbm|lstm|gru|transformer)$")


class AIModelEvaluationRead(BaseModel):
    model_id: int
    name: str
    symbol: str
    timeframe: str
    algorithm: str
    version: int
    status: str
    deployed: bool
    accuracy: float
    precision: float
    recall: float
    f1: float
    profit_factor: float
    roc_auc: float
    samples: int
    feature_rows: int
    feature_count: int
    metrics: dict = Field(default_factory=dict)


class AIModelCompareRequest(BaseModel):
    model_ids: list[int] = Field(..., min_length=2, max_length=12)


class AIModelComparison(BaseModel):
    id: int
    name: str
    symbol: str
    timeframe: str
    model_type: str
    version: int
    status: str
    deployed: bool
    metrics: dict
    rank: int


class BacktestReport(BaseModel):
    run: BacktestRunRead
    equity_curve: list[dict]
    metrics: dict


class WalkForwardRequest(BaseModel):
    strategy_id: int | None = None
    symbol: str = "BTCUSDT"
    timeframe: str = "15m"
    initial_balance: float = Field(default=10000.0, gt=0)
    training_period: int = Field(default=90, ge=30, le=2000)
    validation_period: int = Field(default=30, ge=10, le=1000)
    test_period: int = Field(default=30, ge=10, le=1000)
    rolling_windows: int = Field(default=3, ge=1, le=50)


class WalkForwardMetrics(BaseModel):
    total_return: float
    ending_balance: float
    win_rate: float
    max_drawdown: float
    trades_count: int
    profit_factor: float
    sharpe_ratio: float


class WalkForwardWindowResult(BaseModel):
    window: int
    train_start: str
    train_end: str
    validation_start: str
    validation_end: str
    test_start: str
    test_end: str
    selected_parameters: dict
    optimization_score: float
    training_metrics: WalkForwardMetrics
    validation_metrics: WalkForwardMetrics
    test_metrics: WalkForwardMetrics


class WalkForwardAggregatedResult(BaseModel):
    windows: int
    cumulative_return: float
    average_test_return: float
    average_validation_return: float
    average_win_rate: float
    max_drawdown: float
    total_trades: int
    profit_factor: float
    sharpe_ratio: float
    robustness_score: float


class WalkForwardRunRead(BaseModel):
    id: int
    symbol: str
    strategy: str | None = None
    strategy_id: int | None = None
    timeframe: str
    training_period: int
    validation_period: int
    test_period: int
    rolling_windows: int
    initial_balance: float
    optimization_results: list[dict] = Field(default_factory=list)
    out_of_sample_results: list[dict] = Field(default_factory=list)
    window_metrics: list[WalkForwardWindowResult] = Field(default_factory=list)
    aggregated_result: WalkForwardAggregatedResult
    status: str
    warning: str | None = None
    created_at: datetime


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

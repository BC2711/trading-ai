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
    created_at: datetime

    model_config = {"from_attributes": True}


class StrategyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    timeframe: str | None = Field(default=None, max_length=8)
    status: str | None = Field(default=None, max_length=16)


class RiskSettingRead(BaseModel):
    id: int
    name: str
    max_risk_per_trade: float
    max_daily_loss: float
    max_open_trades: int
    max_symbol_exposure: float
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RiskSettingUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    max_risk_per_trade: float | None = Field(default=None, gt=0, le=1)
    max_daily_loss: float | None = Field(default=None, gt=0, le=1)
    max_open_trades: int | None = Field(default=None, ge=1, le=50)
    max_symbol_exposure: float | None = Field(default=None, gt=0, le=1)
    status: str | None = Field(default=None, max_length=16)


class BacktestRunRequest(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "15m"
    initial_balance: float = Field(default=10000.0, gt=0)
    lookback: int = Field(default=240, ge=60, le=1000)


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
    provider: str = Field(default="rules", pattern="^(rules|openai)$")


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

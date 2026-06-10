from pydantic import BaseModel, Field


class RiskLimitsRead(BaseModel):
    id: int
    max_risk_per_trade: float
    max_daily_loss: float
    max_weekly_loss: float
    max_drawdown: float
    max_open_trades: int
    max_exposure_per_symbol: float
    max_leverage: float
    max_consecutive_losses: int
    circuit_breaker_enabled: bool
    live_trading_enabled: bool


class RiskLimitsUpdate(BaseModel):
    max_risk_per_trade: float | None = Field(default=None, gt=0, le=1)
    max_daily_loss: float | None = Field(default=None, gt=0, le=1)
    max_weekly_loss: float | None = Field(default=None, gt=0, le=1)
    max_drawdown: float | None = Field(default=None, gt=0, le=1)
    max_open_trades: int | None = Field(default=None, ge=1, le=100)
    max_exposure_per_symbol: float | None = Field(default=None, gt=0, le=1)
    max_leverage: float | None = Field(default=None, gt=0, le=100)
    max_consecutive_losses: int | None = Field(default=None, ge=1, le=50)
    live_trading_enabled: bool | None = None


class RiskTradeValidationRequest(BaseModel):
    symbol: str = "BTCUSDT"
    side: str = Field(..., pattern="^(buy|sell)$")
    price: float = Field(..., gt=0)
    quantity: float = Field(..., gt=0)
    stop_loss: float | None = Field(default=None, gt=0)
    take_profit: float | None = Field(default=None, gt=0)
    leverage: float = Field(default=1.0, gt=0)
    execution_mode: str = Field(default="paper", pattern="^(paper|live)$")


class RiskTradeValidationResponse(BaseModel):
    approved: bool
    message: str
    risk_score: float
    notional_value: float
    risk_amount: float
    risk_pct: float
    projected_symbol_exposure_pct: float
    projected_leverage: float
    warnings: list[str] = Field(default_factory=list)


class PositionSizeRequest(BaseModel):
    symbol: str = "BTCUSDT"
    method: str = Field(..., pattern="^(fixed_amount|fixed_percentage_risk|atr_based|volatility_based|kelly)$")
    entry_price: float = Field(..., gt=0)
    stop_loss: float | None = Field(default=None, gt=0)
    account_equity: float | None = Field(default=None, gt=0)
    fixed_amount: float | None = Field(default=None, gt=0)
    risk_percent: float = Field(default=0.01, gt=0, le=1)
    atr: float | None = Field(default=None, gt=0)
    volatility: float | None = Field(default=None, gt=0, le=5)
    leverage: float = Field(default=1.0, gt=0)


class PositionSizeResponse(BaseModel):
    symbol: str
    method: str
    quantity: float
    notional_value: float
    risk_amount: float
    risk_pct: float
    warnings: list[str] = Field(default_factory=list)


class RiskRejectedTradeRead(BaseModel):
    id: int
    symbol: str
    side: str
    quantity: float
    risk_message: str
    created_at: str


class RiskSummaryResponse(BaseModel):
    risk_score: float
    equity: float
    daily_loss: float
    weekly_loss: float
    daily_loss_usage: float
    weekly_loss_usage: float
    drawdown: float
    drawdown_usage: float
    total_exposure: float
    exposure_usage: float
    max_loss_limit: float
    max_weekly_loss_limit: float
    max_drawdown_limit: float
    open_trades: int
    max_open_trades: int
    leverage: float
    max_leverage: float
    circuit_breaker_enabled: bool
    recent_rejected_trades: list[RiskRejectedTradeRead] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

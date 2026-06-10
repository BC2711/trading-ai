from datetime import datetime

from pydantic import BaseModel, Field


class PaperTradingAccountRead(BaseModel):
    id: int
    name: str
    starting_balance: float
    cash_balance: float
    available_balance: float
    paper_equity: float
    margin_used: float
    margin_available: float
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    open_positions: int
    status: str
    updated_at: datetime


class PaperTradingOrderCreate(BaseModel):
    symbol: str = "BTCUSDT"
    side: str = Field(..., pattern="^(buy|sell)$")
    order_type: str = Field(default="market", pattern="^market$")
    quantity: float = Field(..., gt=0)


class PaperTradingOrderRead(BaseModel):
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
    execution_mode: str
    failure_reason: str | None = None
    created_at: datetime
    filled_at: datetime | None


class PaperTradingPositionRead(BaseModel):
    id: int
    symbol: str
    side: str
    quantity: float
    avg_entry_price: float
    mark_price: float
    notional_value: float
    unrealized_pnl: float
    realized_pnl: float
    status: str
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None


class PaperTradingLedgerRead(BaseModel):
    id: int
    event_type: str
    symbol: str | None = None
    side: str
    quantity: float
    price: float
    realized_pnl: float
    unrealized_pnl: float
    balance_after: float
    equity_after: float
    metadata: dict
    created_at: datetime


class PaperTradingPerformancePoint(BaseModel):
    timestamp: datetime
    paper_equity: float
    cash_balance: float
    realized_pnl: float
    unrealized_pnl: float
    event_type: str


class PaperTradingPerformanceResponse(BaseModel):
    starting_balance: float
    current_equity: float
    realized_pnl: float
    unrealized_pnl: float
    points: list[PaperTradingPerformancePoint] = Field(default_factory=list)


class PaperTradingResetRequest(BaseModel):
    starting_balance: float = Field(default=10000.0, gt=0)


class PaperTradingResetResponse(BaseModel):
    account: PaperTradingAccountRead
    reset_orders: int
    reset_positions: int
    reset_ledger_entries: int

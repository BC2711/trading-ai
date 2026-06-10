from datetime import datetime

from pydantic import BaseModel, Field


class PortfolioExposureItem(BaseModel):
    symbol: str
    side: str
    quantity: float
    mark_price: float
    notional_value: float
    exposure_pct: float
    unrealized_pnl: float


class PortfolioExposureResponse(BaseModel):
    total_exposure: float
    total_equity: float
    items: list[PortfolioExposureItem] = Field(default_factory=list)


class PortfolioAllocationItem(BaseModel):
    asset: str
    value: float
    percentage: float


class OpenPositionAllocationItem(BaseModel):
    id: int
    symbol: str
    side: str
    quantity: float
    value: float
    percentage: float
    unrealized_pnl: float


class PortfolioAllocationResponse(BaseModel):
    total_value: float
    by_asset: list[PortfolioAllocationItem] = Field(default_factory=list)
    open_positions: list[OpenPositionAllocationItem] = Field(default_factory=list)


class PortfolioPerformancePoint(BaseModel):
    timestamp: datetime
    equity: float
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    event: str


class PortfolioPerformanceResponse(BaseModel):
    starting_equity: float
    points: list[PortfolioPerformancePoint] = Field(default_factory=list)


class PortfolioPnlResponse(BaseModel):
    total_realized_pnl: float
    total_unrealized_pnl: float
    total_pnl: float
    daily_pnl: float
    weekly_pnl: float
    monthly_pnl: float
    win_rate: float
    best_trade_pnl: float | None = None
    worst_trade_pnl: float | None = None


class PortfolioSummaryResponse(BaseModel):
    total_equity: float
    available_balance: float
    margin_used: float
    margin_available: float
    total_realized_pnl: float
    total_unrealized_pnl: float
    realized_pnl: float
    unrealized_pnl: float
    daily_pnl: float
    weekly_pnl: float
    monthly_pnl: float
    total_exposure: float
    open_positions: int
    filled_orders: int
    rejected_orders: int
    cancelled_orders: int
    closed_positions: int
    winning_positions: int
    losing_positions: int
    win_rate: float
    best_trade_pnl: float | None = None
    worst_trade_pnl: float | None = None
    exposure_by_symbol: list[PortfolioExposureItem] = Field(default_factory=list)
    allocation_by_asset: list[PortfolioAllocationItem] = Field(default_factory=list)
    open_position_allocation: list[OpenPositionAllocationItem] = Field(default_factory=list)


class EquityCurvePoint(BaseModel):
    timestamp: datetime
    equity: float
    realized_pnl: float


class EquityCurveResponse(BaseModel):
    starting_equity: float
    points: list[EquityCurvePoint]

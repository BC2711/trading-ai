from datetime import datetime

from pydantic import BaseModel, Field


class AnalyticsTradeRead(BaseModel):
    id: int
    symbol: str
    strategy: str | None = None
    side: str
    quantity: float
    entry_price: float
    exit_price: float
    realized_pnl: float
    return_pct: float
    opened_at: datetime
    closed_at: datetime
    outcome: str


class AnalyticsEquityPoint(BaseModel):
    timestamp: datetime
    equity: float
    realized_pnl: float
    drawdown: float
    event: str


class AnalyticsEquityCurveResponse(BaseModel):
    starting_equity: float
    ending_equity: float
    max_drawdown: float
    points: list[AnalyticsEquityPoint] = Field(default_factory=list)


class PerformanceSummaryResponse(BaseModel):
    win_rate: float
    loss_rate: float
    average_win: float
    average_loss: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    best_trade: AnalyticsTradeRead | None = None
    worst_trade: AnalyticsTradeRead | None = None
    net_pnl: float
    gross_profit: float
    gross_loss: float


class StrategyComparisonRead(BaseModel):
    id: str
    strategy_id: int | None = None
    strategy: str
    total_trades: int
    win_rate: float
    total_return: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    best_trade: float | None = None
    worst_trade: float | None = None
    source: str


class StrategyComparisonResponse(BaseModel):
    strategies: list[StrategyComparisonRead] = Field(default_factory=list)

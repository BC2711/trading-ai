from datetime import datetime

from pydantic import BaseModel, Field


class AutomatedTradeDecisionRead(BaseModel):
    signal_id: int | None = None
    symbol: str | None = None
    direction: str | None = None
    status: str
    reason: str
    execution_mode: str
    quantity: float | None = None
    order_id: str | None = None
    created_at: datetime | None = None


class AutomatedTradingRunResponse(BaseModel):
    enabled: bool
    execution_mode: str
    live_enabled: bool
    checked_signals: int = 0
    executed_orders: int = 0
    skipped_signals: int = 0
    decisions: list[AutomatedTradeDecisionRead] = Field(default_factory=list)

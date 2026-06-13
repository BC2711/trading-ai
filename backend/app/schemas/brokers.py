from datetime import datetime

from pydantic import BaseModel, Field


class BrokerStatusRead(BaseModel):
    name: str
    display_name: str
    status: str
    connected: bool
    api_key_configured: bool
    mode: str = "testnet"
    last_sync_at: datetime | None = None
    message: str


class BrokerConnectRequest(BaseModel):
    broker: str = Field(..., min_length=2, max_length=48)


class BrokerDisconnectRequest(BaseModel):
    broker: str = Field(..., min_length=2, max_length=48)


class BrokerConnectionResponse(BaseModel):
    broker: BrokerStatusRead


class BrokerBalanceItem(BaseModel):
    asset: str
    free: float
    locked: float
    total: float


class BrokerBalanceResponse(BaseModel):
    broker: str
    balances: list[BrokerBalanceItem] = Field(default_factory=list)
    last_sync_at: datetime


class BrokerPositionRead(BaseModel):
    id: str
    symbol: str
    side: str
    quantity: float
    entry_price: float | None = None
    mark_price: float | None = None
    unrealized_pnl: float = 0.0


class BrokerOrderRead(BaseModel):
    id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: float | None = None
    status: str
    created_at: datetime | None = None


class BrokerOrderCreate(BaseModel):
    symbol: str = Field(..., min_length=3, max_length=32)
    side: str = Field(..., pattern="^(buy|sell)$")
    order_type: str = Field(default="market", pattern="^(market|limit)$")
    quantity: float = Field(..., gt=0)
    price: float | None = Field(default=None, gt=0)


class BrokerOrdersResponse(BaseModel):
    broker: str
    orders: list[BrokerOrderRead] = Field(default_factory=list)
    last_sync_at: datetime


class BrokerPositionsResponse(BaseModel):
    broker: str
    positions: list[BrokerPositionRead] = Field(default_factory=list)
    last_sync_at: datetime


class BrokerCancelResponse(BaseModel):
    broker: str
    order_id: str
    cancelled: bool
    message: str

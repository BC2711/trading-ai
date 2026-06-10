from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.schemas.brokers import BrokerOrderCreate


class BrokerAdapterError(RuntimeError):
    pass


class BrokerNotImplementedError(BrokerAdapterError):
    pass


@dataclass
class BrokerRuntimeState:
    connected: bool = False
    last_sync_at: datetime | None = None
    message: str = "Not connected"


@dataclass
class BrokerBalance:
    asset: str
    free: float
    locked: float
    total: float


@dataclass
class BrokerPosition:
    id: str
    symbol: str
    side: str
    quantity: float
    entry_price: float | None = None
    mark_price: float | None = None
    unrealized_pnl: float = 0.0


@dataclass
class BrokerOrder:
    id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: float | None
    status: str
    created_at: datetime | None = None


class BrokerAdapter(ABC):
    name: str
    display_name: str

    @abstractmethod
    def connect(self) -> BrokerRuntimeState:
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> BrokerRuntimeState:
        raise NotImplementedError

    @abstractmethod
    def get_balance(self) -> list[BrokerBalance]:
        raise NotImplementedError

    @abstractmethod
    def get_positions(self) -> list[BrokerPosition]:
        raise NotImplementedError

    @abstractmethod
    def get_orders(self) -> list[BrokerOrder]:
        raise NotImplementedError

    @abstractmethod
    def place_order(self, payload: BrokerOrderCreate) -> BrokerOrder:
        raise NotImplementedError

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def close_position(self, position_id: str) -> BrokerPosition:
        raise NotImplementedError

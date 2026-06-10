from datetime import datetime, timezone

from app.schemas.brokers import BrokerOrderCreate
from app.services.execution.brokers.base import (
    BrokerAdapter,
    BrokerBalance,
    BrokerNotImplementedError,
    BrokerOrder,
    BrokerPosition,
    BrokerRuntimeState,
)


class PlaceholderBrokerAdapter(BrokerAdapter):
    def __init__(self, name: str, display_name: str, connected: bool = False) -> None:
        self.name = name
        self.display_name = display_name
        self._state = BrokerRuntimeState(connected=connected, message="Adapter placeholder")

    def connect(self) -> BrokerRuntimeState:
        self._state = BrokerRuntimeState(
            connected=False,
            last_sync_at=datetime.now(timezone.utc),
            message=f"{self.display_name} adapter is registered but execution is not implemented yet.",
        )
        return self._state

    def disconnect(self) -> BrokerRuntimeState:
        self._state = BrokerRuntimeState(
            connected=False,
            last_sync_at=datetime.now(timezone.utc),
            message=f"{self.display_name} disconnected.",
        )
        return self._state

    def get_balance(self) -> list[BrokerBalance]:
        return []

    def get_positions(self) -> list[BrokerPosition]:
        return []

    def get_orders(self) -> list[BrokerOrder]:
        return []

    def place_order(self, payload: BrokerOrderCreate) -> BrokerOrder:
        raise BrokerNotImplementedError(f"{self.display_name} order execution is not implemented.")

    def cancel_order(self, order_id: str) -> bool:
        raise BrokerNotImplementedError(f"{self.display_name} order cancellation is not implemented.")

    def close_position(self, position_id: str) -> BrokerPosition:
        raise BrokerNotImplementedError(f"{self.display_name} position closing is not implemented.")


class BybitAdapter(PlaceholderBrokerAdapter):
    def __init__(self) -> None:
        super().__init__("bybit", "Bybit")


class OKXAdapter(PlaceholderBrokerAdapter):
    def __init__(self) -> None:
        super().__init__("okx", "OKX")


class KuCoinAdapter(PlaceholderBrokerAdapter):
    def __init__(self) -> None:
        super().__init__("kucoin", "KuCoin")


class MetaTrader5Adapter(PlaceholderBrokerAdapter):
    def __init__(self) -> None:
        super().__init__("mt5", "MetaTrader 5")

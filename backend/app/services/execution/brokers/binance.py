from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ApiCredential
from app.schemas.brokers import BrokerOrderCreate
from app.services.execution.brokers.base import (
    BrokerAdapter,
    BrokerAdapterError,
    BrokerBalance,
    BrokerNotImplementedError,
    BrokerOrder,
    BrokerPosition,
    BrokerRuntimeState,
)


class BinanceAdapter(BrokerAdapter):
    name = "binance"
    display_name = "Binance"

    def __init__(self, db: Session, state: BrokerRuntimeState | None = None) -> None:
        self.db = db
        self._state = state or BrokerRuntimeState()

    def connect(self) -> BrokerRuntimeState:
        credential = self.active_credential()
        if credential is None:
            self._state = BrokerRuntimeState(
                connected=False,
                last_sync_at=datetime.now(timezone.utc),
                message="Active Binance API credentials are required before connecting.",
            )
            return self._state

        try:
            response = httpx.get(f"{settings.binance_api_base_url}/api/v3/ping", timeout=8.0)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise BrokerAdapterError(f"Unable to reach Binance: {exc}") from exc

        self._state = BrokerRuntimeState(
            connected=True,
            last_sync_at=datetime.now(timezone.utc),
            message="Connected to Binance public API. Signed trading endpoints are adapter-gated.",
        )
        return self._state

    def disconnect(self) -> BrokerRuntimeState:
        self._state = BrokerRuntimeState(
            connected=False,
            last_sync_at=datetime.now(timezone.utc),
            message="Disconnected from Binance adapter.",
        )
        return self._state

    def get_balance(self) -> list[BrokerBalance]:
        self._require_connected()
        return []

    def get_positions(self) -> list[BrokerPosition]:
        self._require_connected()
        return []

    def get_orders(self) -> list[BrokerOrder]:
        self._require_connected()
        return []

    def place_order(self, payload: BrokerOrderCreate) -> BrokerOrder:
        self._require_connected()
        raise BrokerNotImplementedError("Binance signed order execution is not implemented in this adapter yet.")

    def cancel_order(self, order_id: str) -> bool:
        self._require_connected()
        raise BrokerNotImplementedError("Binance signed order cancellation is not implemented in this adapter yet.")

    def close_position(self, position_id: str) -> BrokerPosition:
        self._require_connected()
        raise BrokerNotImplementedError("Binance signed position closing is not implemented in this adapter yet.")

    def active_credential(self) -> ApiCredential | None:
        return self.db.scalar(
            select(ApiCredential).where(
                ApiCredential.exchange == "binance",
                ApiCredential.mode == "live",
                ApiCredential.is_active.is_(True),
            )
        )

    def _require_connected(self) -> None:
        if not self._state.connected:
            raise BrokerAdapterError("Binance adapter is not connected.")

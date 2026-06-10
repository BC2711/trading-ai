from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ApiCredential
from app.schemas.brokers import (
    BrokerBalanceItem,
    BrokerBalanceResponse,
    BrokerCancelResponse,
    BrokerOrderCreate,
    BrokerOrderRead,
    BrokerOrdersResponse,
    BrokerPositionRead,
    BrokerPositionsResponse,
    BrokerStatusRead,
)
from app.services.execution.brokers.base import BrokerAdapter, BrokerRuntimeState
from app.services.execution.brokers.binance import BinanceAdapter
from app.services.execution.brokers.placeholders import BybitAdapter, KuCoinAdapter, MetaTrader5Adapter, OKXAdapter


BROKER_STATES: dict[str, BrokerRuntimeState] = {}
BROKER_LABELS = {
    "binance": "Binance",
    "bybit": "Bybit",
    "okx": "OKX",
    "kucoin": "KuCoin",
    "mt5": "MetaTrader 5",
}


class BrokerService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_brokers(self) -> list[BrokerStatusRead]:
        return [self.status(name) for name in BROKER_LABELS]

    def connect(self, broker: str) -> BrokerStatusRead:
        adapter = self.adapter(broker)
        state = adapter.connect()
        BROKER_STATES[adapter.name] = state
        return self.status(adapter.name)

    def disconnect(self, broker: str) -> BrokerStatusRead:
        adapter = self.adapter(broker)
        state = adapter.disconnect()
        BROKER_STATES[adapter.name] = state
        return self.status(adapter.name)

    def balance(self, broker: str) -> BrokerBalanceResponse:
        adapter = self.adapter(broker)
        balances = adapter.get_balance()
        state = self._touch(adapter.name)
        return BrokerBalanceResponse(
            broker=adapter.name,
            balances=[BrokerBalanceItem(asset=item.asset, free=item.free, locked=item.locked, total=item.total) for item in balances],
            last_sync_at=state.last_sync_at or datetime.now(timezone.utc),
        )

    def positions(self, broker: str) -> BrokerPositionsResponse:
        adapter = self.adapter(broker)
        positions = adapter.get_positions()
        state = self._touch(adapter.name)
        return BrokerPositionsResponse(
            broker=adapter.name,
            positions=[
                BrokerPositionRead(
                    id=item.id,
                    symbol=item.symbol,
                    side=item.side,
                    quantity=item.quantity,
                    entry_price=item.entry_price,
                    mark_price=item.mark_price,
                    unrealized_pnl=item.unrealized_pnl,
                )
                for item in positions
            ],
            last_sync_at=state.last_sync_at or datetime.now(timezone.utc),
        )

    def orders(self, broker: str) -> BrokerOrdersResponse:
        adapter = self.adapter(broker)
        orders = adapter.get_orders()
        state = self._touch(adapter.name)
        return BrokerOrdersResponse(
            broker=adapter.name,
            orders=[
                BrokerOrderRead(
                    id=item.id,
                    symbol=item.symbol,
                    side=item.side,
                    order_type=item.order_type,
                    quantity=item.quantity,
                    price=item.price,
                    status=item.status,
                    created_at=item.created_at,
                )
                for item in orders
            ],
            last_sync_at=state.last_sync_at or datetime.now(timezone.utc),
        )

    def place_order(self, broker: str, payload: BrokerOrderCreate) -> BrokerOrderRead:
        adapter = self.adapter(broker)
        order = adapter.place_order(payload)
        self._touch(adapter.name)
        return BrokerOrderRead(
            id=order.id,
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            quantity=order.quantity,
            price=order.price,
            status=order.status,
            created_at=order.created_at,
        )

    def cancel_order(self, broker: str, order_id: str) -> BrokerCancelResponse:
        adapter = self.adapter(broker)
        cancelled = adapter.cancel_order(order_id)
        self._touch(adapter.name)
        return BrokerCancelResponse(
            broker=adapter.name,
            order_id=order_id,
            cancelled=cancelled,
            message="Order cancellation request accepted." if cancelled else "Order was not cancelled.",
        )

    def status(self, broker: str) -> BrokerStatusRead:
        broker = self._normalize(broker)
        state = BROKER_STATES.get(broker, BrokerRuntimeState())
        return BrokerStatusRead(
            name=broker,
            display_name=BROKER_LABELS[broker],
            status="connected" if state.connected else "disconnected",
            connected=state.connected,
            api_key_configured=self.has_credentials(broker),
            last_sync_at=state.last_sync_at,
            message=state.message,
        )

    def adapter(self, broker: str) -> BrokerAdapter:
        broker = self._normalize(broker)
        state = BROKER_STATES.get(broker, BrokerRuntimeState())
        if broker == "binance":
            return BinanceAdapter(self.db, state)
        if broker == "bybit":
            return BybitAdapter()
        if broker == "okx":
            return OKXAdapter()
        if broker == "kucoin":
            return KuCoinAdapter()
        return MetaTrader5Adapter()

    def has_credentials(self, broker: str) -> bool:
        exchange_names = {broker}
        if broker == "mt5":
            exchange_names.add("metatrader5")
        return (
            self.db.scalar(
                select(ApiCredential.id).where(
                    ApiCredential.exchange.in_(exchange_names),
                    ApiCredential.mode == "live",
                    ApiCredential.is_active.is_(True),
                )
            )
            is not None
        )

    def _touch(self, broker: str) -> BrokerRuntimeState:
        state = BROKER_STATES.get(broker, BrokerRuntimeState())
        state.last_sync_at = datetime.now(timezone.utc)
        BROKER_STATES[broker] = state
        return state

    def _normalize(self, broker: str) -> str:
        normalized = broker.lower().strip()
        if normalized not in BROKER_LABELS:
            raise ValueError(f"Unsupported broker: {broker}")
        return normalized

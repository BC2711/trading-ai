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
from app.schemas.risk import RiskTradeValidationRequest
from app.services.risk import validate_trade_request


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
        self._validate_order_risk(adapter, payload)
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

    def close_position(self, broker: str, position_id: str) -> BrokerPositionRead:
        adapter = self.adapter(broker)
        position = next((item for item in adapter.get_positions() if item.id == position_id or item.symbol == position_id.upper()), None)
        if position is None:
            raise ValueError(f"Position not found: {position_id}")
        price = position.mark_price or adapter.get_reference_price(position.symbol)
        self._validate_order_risk(
            adapter,
            BrokerOrderCreate(symbol=position.symbol, side="sell", order_type="market", quantity=position.quantity, price=price),
            reduce_only=True,
        )
        closed_position = adapter.close_position(position.id)
        self._touch(adapter.name)
        return BrokerPositionRead(
            id=closed_position.id,
            symbol=closed_position.symbol,
            side=closed_position.side,
            quantity=closed_position.quantity,
            entry_price=closed_position.entry_price,
            mark_price=closed_position.mark_price,
            unrealized_pnl=closed_position.unrealized_pnl,
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
            mode=self.broker_mode(broker),
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
        credential_mode = "live"
        if broker == "binance" and self.broker_mode(broker) == "testnet":
            credential_mode = "paper"
            exchange_names.add("binance_testnet")
        return (
            self.db.scalar(
                select(ApiCredential.id).where(
                    ApiCredential.exchange.in_(exchange_names),
                    ApiCredential.mode == credential_mode,
                    ApiCredential.is_active.is_(True),
                )
            )
            is not None
        )

    def broker_mode(self, broker: str) -> str:
        normalized = self._normalize(broker)
        if normalized == "binance":
            from app.core.config import settings

            return "live" if settings.binance_broker_mode.lower().strip() == "live" else "testnet"
        return "testnet"

    def _validate_order_risk(self, adapter: BrokerAdapter, payload: BrokerOrderCreate, *, reduce_only: bool = False) -> None:
        price = payload.price or adapter.get_reference_price(payload.symbol)
        result = validate_trade_request(
            self.db,
            RiskTradeValidationRequest(
                symbol=payload.symbol.upper(),
                side=payload.side,
                price=price,
                quantity=payload.quantity,
                execution_mode="live" if self.broker_mode(adapter.name) == "live" else "paper",
                reduce_only=reduce_only,
            ),
        )
        if not result.approved:
            raise ValueError(f"Risk validation rejected order: {result.message}")

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

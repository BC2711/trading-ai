from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decrypt_secret
from app.models import ApiCredential
from app.schemas.brokers import BrokerOrderCreate
from app.services.execution.brokers.base import (
    BrokerAdapter,
    BrokerAdapterError,
    BrokerBalance,
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

    @property
    def mode(self) -> str:
        configured_mode = settings.binance_broker_mode.lower().strip()
        return "live" if configured_mode == "live" else "testnet"

    @property
    def base_url(self) -> str:
        if self.mode == "live":
            return settings.binance_api_base_url.rstrip("/")
        return settings.binance_testnet_api_base_url.rstrip("/")

    def connect(self) -> BrokerRuntimeState:
        credential = self.active_credential()
        if credential is None:
            self._state = BrokerRuntimeState(
                connected=False,
                last_sync_at=datetime.now(timezone.utc),
                message=f"Active Binance {self.mode} API credentials are required before connecting.",
            )
            return self._state

        try:
            self._request("GET", "/api/v3/account", signed=True)
        except BrokerAdapterError as exc:
            raise BrokerAdapterError(f"Unable to connect to Binance {self.mode}: {exc}") from exc

        self._state = BrokerRuntimeState(
            connected=True,
            last_sync_at=datetime.now(timezone.utc),
            message=f"Connected to Binance {self.mode} signed API.",
        )
        return self._state

    def disconnect(self) -> BrokerRuntimeState:
        self._state = BrokerRuntimeState(
            connected=False,
            last_sync_at=datetime.now(timezone.utc),
            message=f"Disconnected from Binance {self.mode} adapter.",
        )
        return self._state

    def get_balance(self) -> list[BrokerBalance]:
        self._require_connected()
        account = self._request("GET", "/api/v3/account", signed=True)
        balances = []
        for item in account.get("balances", []):
            free = float(item.get("free") or 0)
            locked = float(item.get("locked") or 0)
            if free or locked:
                balances.append(BrokerBalance(asset=str(item.get("asset")), free=free, locked=locked, total=free + locked))
        return balances

    def get_positions(self) -> list[BrokerPosition]:
        self._require_connected()
        account = self._request("GET", "/api/v3/account", signed=True)
        positions: list[BrokerPosition] = []
        for item in account.get("balances", []):
            asset = str(item.get("asset") or "")
            if not asset or asset in {"USDT", "BUSD", "USDC", "FDUSD", "TUSD"}:
                continue
            quantity = float(item.get("free") or 0) + float(item.get("locked") or 0)
            if quantity <= 0:
                continue
            symbol = f"{asset}USDT"
            positions.append(
                BrokerPosition(
                    id=symbol,
                    symbol=symbol,
                    side="long",
                    quantity=quantity,
                    mark_price=self._safe_reference_price(symbol),
                )
            )
        return positions

    def get_orders(self) -> list[BrokerOrder]:
        self._require_connected()
        orders = self._request("GET", "/api/v3/openOrders", signed=True)
        return [self._order_from_payload(item) for item in orders]

    def place_order(self, payload: BrokerOrderCreate) -> BrokerOrder:
        self._require_connected()
        params: dict[str, str] = {
            "symbol": payload.symbol.upper(),
            "side": payload.side.upper(),
            "type": payload.order_type.upper(),
            "quantity": _format_decimal(payload.quantity),
            "newOrderRespType": "RESULT",
        }
        if payload.order_type == "limit":
            if payload.price is None:
                raise BrokerAdapterError("Limit orders require a price.")
            params["timeInForce"] = "GTC"
            params["price"] = _format_decimal(payload.price)

        result = self._request("POST", "/api/v3/order", params=params, signed=True)
        return self._order_from_payload(result)

    def get_reference_price(self, symbol: str) -> float:
        result = self._request("GET", "/api/v3/ticker/price", params={"symbol": symbol.upper()}, signed=False)
        try:
            return float(result["price"])
        except (KeyError, TypeError, ValueError) as exc:
            raise BrokerAdapterError(f"Unable to read Binance ticker price for {symbol}.") from exc

    def cancel_order(self, order_id: str) -> bool:
        self._require_connected()
        symbol, raw_order_id = self._resolve_order_identifier(order_id)
        params = {"symbol": symbol}
        if raw_order_id.isdigit():
            params["orderId"] = raw_order_id
        else:
            params["origClientOrderId"] = raw_order_id
        self._request("DELETE", "/api/v3/order", params=params, signed=True)
        return True

    def close_position(self, position_id: str) -> BrokerPosition:
        self._require_connected()
        symbol = position_id.upper()
        asset = _base_asset_from_symbol(symbol)
        account = self._request("GET", "/api/v3/account", signed=True)
        quantity = 0.0
        for item in account.get("balances", []):
            if str(item.get("asset") or "").upper() == asset:
                quantity = float(item.get("free") or 0)
                break
        if quantity <= 0:
            raise BrokerAdapterError(f"No free {asset} balance is available to close {symbol}.")

        self.place_order(BrokerOrderCreate(symbol=symbol, side="sell", order_type="market", quantity=quantity))
        return BrokerPosition(id=symbol, symbol=symbol, side="closed", quantity=0.0, mark_price=self._safe_reference_price(symbol))

    def active_credential(self) -> ApiCredential | None:
        credential_mode = "live" if self.mode == "live" else "paper"
        exchanges = ["binance", "binance_testnet"] if credential_mode == "paper" else ["binance"]
        return self.db.scalar(
            select(ApiCredential).where(
                ApiCredential.exchange.in_(exchanges),
                ApiCredential.mode == credential_mode,
                ApiCredential.is_active.is_(True),
            )
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        signed: bool,
    ):
        request_params = dict(params or {})
        headers: dict[str, str] = {}
        if signed:
            credential = self.active_credential()
            if credential is None:
                raise BrokerAdapterError(f"Active Binance {self.mode} credentials are not configured.")
            headers["X-MBX-APIKEY"] = credential.api_key
            request_params["timestamp"] = str(int(time.time() * 1000))
            request_params["recvWindow"] = str(settings.binance_recv_window)
            query_string = urlencode(request_params)
            request_params["signature"] = hmac.new(
                decrypt_secret(credential.encrypted_api_secret).encode("utf-8"),
                query_string.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

        try:
            response = httpx.request(
                method,
                f"{self.base_url}{path}",
                params=request_params,
                headers=headers,
                timeout=8.0,
            )
        except httpx.HTTPError as exc:
            raise BrokerAdapterError(f"Binance request failed: {exc}") from exc

        if response.status_code >= 400:
            raise BrokerAdapterError(_binance_error_message(response))
        try:
            return response.json()
        except ValueError as exc:
            raise BrokerAdapterError("Binance returned an invalid JSON response.") from exc

    def _order_from_payload(self, item: dict) -> BrokerOrder:
        symbol = str(item.get("symbol") or "")
        order_id = str(item.get("orderId") or item.get("clientOrderId") or "")
        executed_quantity = float(item.get("executedQty") or 0)
        original_quantity = float(item.get("origQty") or item.get("quantity") or 0)
        price = float(item.get("price") or 0) or None
        transact_time = item.get("transactTime") or item.get("time") or item.get("updateTime")
        return BrokerOrder(
            id=f"{symbol}:{order_id}" if symbol and order_id else order_id,
            symbol=symbol,
            side=str(item.get("side") or "").lower(),
            order_type=str(item.get("type") or "").lower(),
            quantity=executed_quantity or original_quantity,
            price=price,
            status=str(item.get("status") or "unknown").lower(),
            created_at=datetime.fromtimestamp(float(transact_time) / 1000, tz=timezone.utc) if transact_time else datetime.now(timezone.utc),
        )

    def _resolve_order_identifier(self, order_id: str) -> tuple[str, str]:
        if ":" in order_id:
            symbol, raw_order_id = order_id.split(":", 1)
            return symbol.upper(), raw_order_id

        for order in self.get_orders():
            if order.id.endswith(f":{order_id}") or order.id == order_id:
                symbol, raw_order_id = order.id.split(":", 1)
                return symbol.upper(), raw_order_id
        raise BrokerAdapterError("Binance cancellation requires an order id returned by this API, formatted as SYMBOL:ORDER_ID.")

    def _safe_reference_price(self, symbol: str) -> float | None:
        try:
            return self.get_reference_price(symbol)
        except BrokerAdapterError:
            return None

    def _require_connected(self) -> None:
        if not self._state.connected:
            raise BrokerAdapterError("Binance adapter is not connected.")


def _format_decimal(value: float) -> str:
    return f"{value:.12f}".rstrip("0").rstrip(".")


def _base_asset_from_symbol(symbol: str) -> str:
    for suffix in ("USDT", "BUSD", "USDC", "FDUSD", "TUSD", "USD"):
        if symbol.endswith(suffix):
            return symbol.removesuffix(suffix)
    return symbol


def _binance_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return f"Binance error {response.status_code}: {response.text[:200]}"
    code = payload.get("code")
    message = payload.get("msg") or payload.get("message") or response.text[:200]
    if code is None:
        return f"Binance error {response.status_code}: {message}"
    return f"Binance error {code}: {message}"

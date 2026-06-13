from __future__ import annotations

import os
from typing import Any

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import encrypt_secret
from app.db.session import Base
from app.models import ApiCredential, RiskSetting, Symbol
from app.schemas.brokers import BrokerOrderCreate
from app.services.execution.brokers.service import BROKER_STATES, BrokerService


def test_binance_testnet_connection_order_and_cancellation(monkeypatch, tmp_path) -> None:
    calls: list[dict[str, Any]] = []

    def fake_request(method: str, url: str, **kwargs):
        calls.append({"method": method, "url": url, **kwargs})
        if url.endswith("/api/v3/account"):
            return httpx.Response(200, json={"balances": []})
        if url.endswith("/api/v3/ticker/price"):
            return httpx.Response(200, json={"symbol": "BTCUSDT", "price": "30000"})
        if method == "POST" and url.endswith("/api/v3/order"):
            return httpx.Response(
                200,
                json={
                    "symbol": "BTCUSDT",
                    "orderId": 12345,
                    "side": "BUY",
                    "type": "MARKET",
                    "origQty": "0.001",
                    "executedQty": "0.001",
                    "status": "FILLED",
                    "transactTime": 1_718_000_000_000,
                },
            )
        if method == "DELETE" and url.endswith("/api/v3/order"):
            return httpx.Response(200, json={"symbol": "BTCUSDT", "orderId": 12345, "status": "CANCELED"})
        raise AssertionError(f"Unexpected Binance call: {method} {url}")

    monkeypatch.setattr(httpx, "request", fake_request)
    original_mode = settings.binance_broker_mode
    settings.binance_broker_mode = "testnet"
    BROKER_STATES.clear()
    try:
        with Session(_engine(tmp_path)) as db:
            _seed_binance_test_context(db)
            service = BrokerService(db)

            connected = service.connect("binance")
            order = service.place_order("binance", BrokerOrderCreate(symbol="BTCUSDT", side="buy", order_type="market", quantity=0.001))
            cancelled = service.cancel_order("binance", order.id)
    finally:
        settings.binance_broker_mode = original_mode
        BROKER_STATES.clear()

    assert connected.connected is True
    assert connected.mode == "testnet"
    assert order.id == "BTCUSDT:12345"
    assert order.status == "filled"
    assert cancelled.cancelled is True
    signed_calls = [call for call in calls if call["url"].endswith(("/api/v3/account", "/api/v3/order"))]
    assert signed_calls
    assert all(call["headers"]["X-MBX-APIKEY"] == "testnet-key" for call in signed_calls)
    assert all("signature" in call["params"] for call in signed_calls)
    assert calls[0]["url"].startswith(settings.binance_testnet_api_base_url)


def test_binance_order_rejected_before_signed_request(monkeypatch, tmp_path) -> None:
    calls: list[dict[str, Any]] = []

    def fake_request(method: str, url: str, **kwargs):
        calls.append({"method": method, "url": url, **kwargs})
        if url.endswith("/api/v3/account"):
            return httpx.Response(200, json={"balances": []})
        if url.endswith("/api/v3/ticker/price"):
            return httpx.Response(200, json={"symbol": "BTCUSDT", "price": "30000"})
        if method == "POST" and url.endswith("/api/v3/order"):
            raise AssertionError("Rejected orders must not reach Binance order creation.")
        raise AssertionError(f"Unexpected Binance call: {method} {url}")

    monkeypatch.setattr(httpx, "request", fake_request)
    original_mode = settings.binance_broker_mode
    settings.binance_broker_mode = "testnet"
    BROKER_STATES.clear()
    try:
        with Session(_engine(tmp_path)) as db:
            _seed_binance_test_context(db, max_symbol_exposure=0.001)
            service = BrokerService(db)
            service.connect("binance")

            try:
                service.place_order("binance", BrokerOrderCreate(symbol="BTCUSDT", side="buy", order_type="market", quantity=0.01))
            except ValueError as exc:
                rejection = str(exc)
            else:
                raise AssertionError("Expected risk validation rejection.")
    finally:
        settings.binance_broker_mode = original_mode
        BROKER_STATES.clear()

    assert "Risk validation rejected order" in rejection
    assert not any(call["method"] == "POST" and call["url"].endswith("/api/v3/order") for call in calls)


def test_binance_close_position_submits_market_sell(monkeypatch, tmp_path) -> None:
    calls: list[dict[str, Any]] = []

    def fake_request(method: str, url: str, **kwargs):
        calls.append({"method": method, "url": url, **kwargs})
        if url.endswith("/api/v3/account"):
            return httpx.Response(200, json={"balances": [{"asset": "BTC", "free": "0.002", "locked": "0"}]})
        if url.endswith("/api/v3/ticker/price"):
            return httpx.Response(200, json={"symbol": "BTCUSDT", "price": "30000"})
        if method == "POST" and url.endswith("/api/v3/order"):
            return httpx.Response(
                200,
                json={
                    "symbol": "BTCUSDT",
                    "orderId": 54321,
                    "side": "SELL",
                    "type": "MARKET",
                        "origQty": "0.002",
                        "executedQty": "0.002",
                    "status": "FILLED",
                    "transactTime": 1_718_000_100_000,
                },
            )
        raise AssertionError(f"Unexpected Binance call: {method} {url}")

    monkeypatch.setattr(httpx, "request", fake_request)
    original_mode = settings.binance_broker_mode
    settings.binance_broker_mode = "testnet"
    BROKER_STATES.clear()
    try:
        with Session(_engine(tmp_path)) as db:
            _seed_binance_test_context(db)
            service = BrokerService(db)
            service.connect("binance")
            closed = service.close_position("binance", "BTCUSDT")
    finally:
        settings.binance_broker_mode = original_mode
        BROKER_STATES.clear()

    assert closed.id == "BTCUSDT"
    assert closed.side == "closed"
    close_call = next(call for call in calls if call["method"] == "POST" and call["url"].endswith("/api/v3/order"))
    assert close_call["params"]["side"] == "SELL"
    assert close_call["params"]["type"] == "MARKET"
    assert close_call["params"]["quantity"] == "0.002"


def test_binance_error_message_is_clear(monkeypatch, tmp_path) -> None:
    def fake_request(method: str, url: str, **kwargs):
        return httpx.Response(400, json={"code": -2010, "msg": "Account has insufficient balance."})

    monkeypatch.setattr(httpx, "request", fake_request)
    original_mode = settings.binance_broker_mode
    settings.binance_broker_mode = "testnet"
    BROKER_STATES.clear()
    try:
        with Session(_engine(tmp_path)) as db:
            _seed_binance_test_context(db)
            try:
                BrokerService(db).connect("binance")
            except Exception as exc:
                message = str(exc)
            else:
                raise AssertionError("Expected Binance error.")
    finally:
        settings.binance_broker_mode = original_mode
        BROKER_STATES.clear()

    assert "Binance error -2010: Account has insufficient balance." in message


def _engine(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'broker.sqlite').as_posix()}")
    Base.metadata.create_all(bind=engine)
    return engine


def _seed_binance_test_context(db: Session, max_symbol_exposure: float = 0.2) -> None:
    db.add(Symbol(symbol="BTCUSDT", base_asset="BTC", quote_asset="USDT", market="crypto", exchange="binance_testnet", status="active"))
    db.add(
        RiskSetting(
            name="Default Paper Risk",
            max_risk_per_trade=0.01,
            max_daily_loss=0.03,
            max_weekly_loss=0.08,
            max_drawdown=0.15,
            max_open_trades=3,
            max_symbol_exposure=max_symbol_exposure,
            max_leverage=1.0,
            max_consecutive_losses=3,
            emergency_stop=False,
            live_trading_enabled=False,
            status="active",
        )
    )
    db.add(
        ApiCredential(
            exchange="binance",
            api_key="testnet-key",
            encrypted_api_secret=encrypt_secret("testnet-secret"),
            mode="paper",
            is_active=True,
        )
    )
    db.commit()

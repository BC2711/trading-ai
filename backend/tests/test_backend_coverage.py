import os
from pathlib import Path

test_db_path = Path(".tmp/test_backend_coverage.sqlite")
test_db_path.parent.mkdir(exist_ok=True)
if "PYTEST_CURRENT_TEST" not in os.environ:
    test_db_path.unlink(missing_ok=True)
os.environ.setdefault("DATABASE_URL", f"sqlite:///{test_db_path.as_posix()}")

from fastapi.testclient import TestClient

from app.main import app
from app.services.admin import clear_login_throttles


def auth_headers(client: TestClient) -> dict[str, str]:
    clear_login_throttles()
    email = "admin@example.com"
    response = client.post("/api/auth/login", json={"email": email, "password": "strong-password"})
    if response.status_code != 200:
        client.post(
            "/api/auth/register",
            json={
                "email": email,
                "full_name": "Coverage Admin",
                "password": "strong-password",
                "role": "admin",
            },
        )
        response = client.post("/api/auth/login", json={"email": email, "password": "strong-password"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_auth_users_and_rbac_management_flow() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        register_response = client.post(
            "/api/auth/register",
            json={
                "email": "coverage-user@example.com",
                "full_name": "Coverage User",
                "password": "strong-password",
                "role": "trader",
            },
        )
        users_response = client.get("/api/users", headers=headers)
        target_user = next(user for user in users_response.json() if user["email"] == "coverage-user@example.com")
        patch_response = client.patch(
            f"/api/users/{target_user['id']}",
            headers=headers,
            json={"full_name": "Coverage User Updated"},
        )
        roles_response = client.get("/api/roles", headers=headers)
        permissions_response = client.get("/api/permissions", headers=headers)
        trader_role = next(role for role in roles_response.json() if role["slug"] == "trader")
        assign_response = client.post(
            f"/api/users/{target_user['id']}/roles",
            headers=headers,
            json={"role_ids": [trader_role["id"]]},
        )
        user_permissions_response = client.get(f"/api/users/{target_user['id']}/permissions", headers=headers)
        me_response = client.get("/api/me", headers=headers)

    assert register_response.status_code == 200, register_response.text
    assert users_response.status_code == 200
    assert patch_response.status_code == 200
    assert patch_response.json()["full_name"] == "Coverage User Updated"
    assert roles_response.status_code == 200
    assert permissions_response.status_code == 200
    assert {"execute_trades", "view_orders"}.issubset({permission["name"] for permission in permissions_response.json()})
    assert assign_response.status_code == 200
    assert "orders:create" in user_permissions_response.json()
    assert me_response.json()["role"] in {"admin", "super_admin"}


def test_market_signals_strategies_backtests_and_ai_endpoints() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        symbols_response = client.get("/api/symbols", headers=headers)
        candles_response = client.get("/api/candles", headers=headers, params={"symbol": "BTCUSDT", "limit": 5})
        signal_response = client.post(
            "/api/signals/generate",
            headers=headers,
            json={"symbol": "BTCUSDT", "timeframe": "15m"},
        )
        strategy_response = client.post(
            "/api/strategies",
            headers=headers,
            json={
                "name": "Coverage Strategy",
                "description": "Coverage test strategy",
                "timeframe": "15m",
                "status": "draft",
                "parameters": {"fast_window": 8},
                "enabled": False,
            },
        )
        strategy_id = strategy_response.json()["id"]
        patch_strategy_response = client.patch(
            f"/api/strategies/{strategy_id}",
            headers=headers,
            json={"enabled": True, "status": "active"},
        )
        disable_strategy_response = client.post(f"/api/strategies/{strategy_id}/disable", headers=headers)
        backtest_response = client.post(
            "/api/backtests/run",
            headers=headers,
            json={"symbol": "BTCUSDT", "timeframe": "15m", "initial_balance": 10000, "lookback": 120},
        )
        report_response = client.get(f"/api/backtests/{backtest_response.json()['id']}/report", headers=headers)
        ai_provider_response = client.get("/api/ai/provider", headers=headers)
        ai_models_response = client.get("/api/ai/models", headers=headers)
        ai_analysis_response = client.post(
            "/api/ai/analyze-signal",
            headers=headers,
            json={"symbol": "BTCUSDT", "timeframe": "15m", "lookback": 60},
        )

    assert symbols_response.status_code == 200
    assert {"BTCUSDT", "ETHUSDT"}.issubset({symbol["symbol"] for symbol in symbols_response.json()})
    assert candles_response.status_code == 200
    assert len(candles_response.json()) == 5
    assert signal_response.status_code == 200
    assert signal_response.json()[0]["symbol"] == "BTCUSDT"
    assert strategy_response.status_code == 200
    assert patch_strategy_response.json()["enabled"] is True
    assert disable_strategy_response.json()["enabled"] is False
    assert backtest_response.status_code == 200, backtest_response.text
    assert report_response.status_code == 200
    assert "profit_factor" in report_response.json()["metrics"]
    assert ai_provider_response.status_code == 200
    assert "rules" in ai_provider_response.json()["available_providers"]
    assert ai_models_response.status_code == 200
    assert ai_analysis_response.status_code == 200
    assert ai_analysis_response.json()["symbol"] == "BTCUSDT"


def test_brokers_paper_trading_portfolio_and_risk_endpoints() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        reset_response = client.post("/api/paper/reset", headers=headers, json={"starting_balance": 10000})
        brokers_response = client.get("/api/brokers", headers=headers)
        placeholder_order_response = client.post(
            "/api/brokers/okx/orders",
            headers=headers,
            json={"symbol": "BTCUSDT", "side": "buy", "order_type": "market", "quantity": 0.001},
        )
        order_response = client.post(
            "/api/paper/orders",
            headers=headers,
            json={"symbol": "BTCUSDT", "side": "buy", "order_type": "market", "quantity": 0.001},
        )
        orders_response = client.get("/api/paper/orders", headers=headers, params={"limit": 5})
        positions_response = client.get("/api/paper/positions", headers=headers, params={"status": "all"})
        portfolio_response = client.get("/api/portfolio/summary", headers=headers)
        allocation_response = client.get("/api/portfolio/allocation", headers=headers)
        risk_response = client.post(
            "/api/risk/validate-trade",
            headers=headers,
            json={
                "symbol": "BTCUSDT",
                "side": "buy",
                "price": 65000,
                "quantity": 0.001,
                "stop_loss": 64900,
                "take_profit": 67000,
                "execution_mode": "paper",
            },
        )
        risk_summary_response = client.get("/api/risk/summary", headers=headers)

    assert reset_response.status_code == 200
    assert brokers_response.status_code == 200
    assert {"binance", "okx"}.issubset({broker["name"] for broker in brokers_response.json()})
    assert placeholder_order_response.status_code == 501
    assert order_response.status_code == 200, order_response.text
    assert order_response.json()["risk_status"] == "approved"
    assert orders_response.status_code == 200
    assert positions_response.status_code == 200
    assert portfolio_response.status_code == 200
    assert "total_equity" in portfolio_response.json()
    assert allocation_response.status_code == 200
    assert "by_asset" in allocation_response.json()
    assert risk_response.status_code == 200
    assert risk_response.json()["approved"] is True
    assert risk_summary_response.status_code == 200
    assert "recent_rejected_trades" in risk_summary_response.json()


def test_notifications_audit_and_monitoring_endpoints() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        notification_response = client.post(
            "/api/notifications",
            headers=headers,
            json={"title": "Coverage notice", "message": "Notification coverage", "severity": "info"},
        )
        notifications_response = client.get("/api/notifications", headers=headers)
        mark_response = client.post(
            "/api/notifications/mark-read",
            headers=headers,
            json={"notification_ids": [notification_response.json()["id"]]},
        )
        audit_response = client.get("/api/audit/events", headers=headers, params={"limit": 10})
        health_response = client.get("/api/monitoring/health")
        metrics_response = client.get("/api/monitoring/metrics", headers=headers)
        workers_response = client.get("/api/monitoring/workers", headers=headers)
        system_response = client.get("/api/monitoring/system", headers=headers)

    assert notification_response.status_code == 200, notification_response.text
    assert notifications_response.status_code == 200
    assert any(item["title"] == "Coverage notice" for item in notifications_response.json())
    assert mark_response.status_code == 200
    assert mark_response.json()["updated_count"] == 1
    assert audit_response.status_code == 200
    assert health_response.status_code == 200
    assert health_response.json()["status"] in {"ok", "degraded"}
    assert metrics_response.status_code == 200
    assert workers_response.status_code == 200
    assert system_response.status_code == 200


def test_websocket_streams_accept_tokens_and_subscriptions() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        token = headers["Authorization"].removeprefix("Bearer ")

        with client.websocket_connect(f"/api/ws/prices?token={token}") as websocket:
            connected = websocket.receive_json()
            payload = websocket.receive_json()

        with client.websocket_connect(f"/api/ws/market-data?token={token}&channels=ticks") as websocket:
            subscribed = websocket.receive_json()
            websocket.send_json({"type": "subscribe", "channels": ["order_books"]})
            resubscribed = websocket.receive_json()

    assert connected["type"] == "prices"
    assert connected["payload"]["status"] == "connected"
    assert payload["type"] == "prices"
    assert isinstance(payload["payload"], list)
    assert subscribed == {"type": "subscribed", "channels": ["ticks"]}
    assert resubscribed == {"type": "subscribed", "channels": ["order_books"]}

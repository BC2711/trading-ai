import os
from pathlib import Path

test_db_path = Path(".tmp/test_app.sqlite")
test_db_path.parent.mkdir(exist_ok=True)
test_db_path.unlink(missing_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path.as_posix()}"

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.ai.models import ModelService, is_package_available


def auth_headers(client: TestClient, email: str = "admin@example.com") -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={
            "email": email,
            "full_name": "Admin User",
            "password": "strong-password",
            "role": "admin",
        },
    )
    response = client.post("/api/auth/login", json={"email": email, "password": "strong-password"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def trader_headers(client: TestClient, email: str = "trader@example.com") -> dict[str, str]:
    auth_headers(client)
    client.post(
        "/api/auth/register",
        json={
            "email": email,
            "full_name": "Trader User",
            "password": "strong-password",
            "role": "admin",
        },
    )
    response = client.post("/api/auth/login", json={"email": email, "password": "strong-password"})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_health_is_public() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_security_headers_are_applied() -> None:
    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_navigation_is_backend_driven_and_permissioned() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        me_response = client.get("/api/me", headers=headers)
        navigation_response = client.get("/api/navigation", headers=headers)

    assert me_response.status_code == 200
    assert navigation_response.status_code == 200

    permissions = set(me_response.json()["permissions"])
    navigation = navigation_response.json()

    assert {"#/overview", "#/trading", "#/activity", "#/users", "#/strategies"}.issubset(
        {item["href"] for item in navigation}
    )
    assert all(item["permission"] in permissions for item in navigation)
    assert all(child["permission"] in permissions for item in navigation for child in item["children"])


def test_api_key_protects_api_routes() -> None:
    original_api_key = settings.api_key
    settings.api_key = "test-secret"
    try:
        with TestClient(app) as client:
            headers = auth_headers(client)
            health_response = client.get("/api/health")
            missing_key_response = client.get("/api/signals")
            valid_key_response = client.get("/api/signals", headers={"X-API-Key": "test-secret"})
            valid_key_and_token_response = client.get("/api/signals", headers={**headers, "X-API-Key": "test-secret"})
    finally:
        settings.api_key = original_api_key

    assert health_response.status_code == 200
    assert missing_key_response.status_code == 401
    assert valid_key_response.status_code == 401
    assert valid_key_and_token_response.status_code == 200


def test_api_credentials_do_not_return_secret() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        response = client.post(
            "/api/api-credentials",
            headers=headers,
            json={
                "exchange": "binance",
                "api_key": "public-key",
                "api_secret": "private-secret",
                "mode": "paper",
            },
        )

    assert response.status_code == 200
    assert "api_secret" not in response.json()
    assert "encrypted_api_secret" not in response.json()


def test_refresh_token_renews_access_token() -> None:
    with TestClient(app) as client:
        auth_headers(client)
        login_response = client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "strong-password"},
        )
        refresh_response = client.post(
            "/api/auth/refresh",
            json={"refresh_token": login_response.json()["refresh_token"]},
        )

    assert login_response.status_code == 200
    assert refresh_response.status_code == 200
    assert refresh_response.json()["access_token"]
    assert refresh_response.json()["refresh_token"]


def test_later_public_registration_cannot_self_assign_admin() -> None:
    with TestClient(app) as client:
        auth_headers(client)
        client.post(
            "/api/auth/register",
            json={
                "email": "not-admin@example.com",
                "full_name": "Not Admin",
                "password": "strong-password",
                "role": "admin",
            },
        )
        login_response = client.post(
            "/api/auth/login",
            json={"email": "not-admin@example.com", "password": "strong-password"},
        )
        me_response = client.get(
            "/api/me",
            headers={"Authorization": f"Bearer {login_response.json()['access_token']}"},
        )

    assert login_response.status_code == 200
    assert me_response.status_code == 200
    assert me_response.json()["role"] == "trader"


def test_trader_can_view_but_not_manage_symbols() -> None:
    with TestClient(app) as client:
        headers = trader_headers(client, "symbol-trader@example.com")
        list_response = client.get("/api/symbols", headers=headers)
        create_response = client.post(
            "/api/symbols",
            headers=headers,
            json={
                "symbol": "SOLUSDT",
                "base_asset": "SOL",
                "quote_asset": "USDT",
                "market": "crypto",
                "exchange": "binance",
            },
        )

    assert list_response.status_code == 200
    assert create_response.status_code == 403


def test_market_data_import_stores_spread_and_detects_missing_candles() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        import_response = client.post(
            "/api/market-data/import",
            headers=headers,
            json={
                "market": "crypto",
                "exchange": "binance",
                "timeframe": "1m",
                "candles": [
                    {
                        "symbol": "ADAUSDT",
                        "timeframe": "1m",
                        "opened_at": "2026-06-09T10:00:00Z",
                        "open": 1.0,
                        "high": 1.2,
                        "low": 0.9,
                        "close": 1.1,
                        "volume": 1000,
                        "spread": 0.0002,
                    },
                    {
                        "symbol": "ADAUSDT",
                        "timeframe": "1m",
                        "opened_at": "2026-06-09T10:02:00Z",
                        "open": 1.1,
                        "high": 1.3,
                        "low": 1.0,
                        "close": 1.2,
                        "volume": 1200,
                        "spread": 0.0003,
                    },
                ],
            },
        )
        candles_response = client.get("/api/candles", headers=headers, params={"symbol": "ADAUSDT", "timeframe": "1m", "limit": 10})
        validation_response = client.get("/api/market-data/validate", headers=headers, params={"symbol": "ADAUSDT", "timeframe": "1m", "limit": 10})

    assert import_response.status_code == 200
    assert import_response.json()["candle_inserted"] == 2
    assert candles_response.status_code == 200
    assert candles_response.json()[0]["spread"] == 0.0002
    assert validation_response.status_code == 200
    assert validation_response.json()["valid"] is False
    assert validation_response.json()["missing_candles"][0]["expected_at"].startswith("2026-06-09T10:01:00")


def test_market_data_stream_ingests_and_lists_ticks() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        stream_response = client.post(
            "/api/market-data/stream",
            headers=headers,
            json={
                "channel": "ticks",
                "payload": {
                    "symbol": "EURUSD",
                    "exchange": "oanda",
                    "tick_time": "2026-06-09T11:00:00Z",
                    "bid": 1.081,
                    "ask": 1.0812,
                    "price": 1.0811,
                    "volume": 250000,
                    "source": "stream",
                },
            },
        )
        ticks_response = client.get("/api/market-data/ticks", headers=headers, params={"symbol": "EURUSD", "limit": 5})

    assert stream_response.status_code == 200
    assert stream_response.json()["inserted"] == 1
    assert ticks_response.status_code == 200
    assert ticks_response.json()[0]["symbol"] == "EURUSD"
    assert ticks_response.json()[0]["spread"] == 0.0002


def test_portfolio_management_endpoints_return_aggregate_shapes() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        summary_response = client.get("/api/portfolio/summary", headers=headers)
        performance_response = client.get("/api/portfolio/performance", headers=headers)
        exposure_response = client.get("/api/portfolio/exposure", headers=headers)
        allocation_response = client.get("/api/portfolio/allocation", headers=headers)
        pnl_response = client.get("/api/portfolio/pnl", headers=headers)

    assert summary_response.status_code == 200
    assert performance_response.status_code == 200
    assert exposure_response.status_code == 200
    assert allocation_response.status_code == 200
    assert pnl_response.status_code == 200

    summary = summary_response.json()
    assert {"total_equity", "available_balance", "margin_used", "daily_pnl", "monthly_pnl"}.issubset(summary)
    assert "exposure_by_symbol" in summary
    assert "allocation_by_asset" in summary
    assert "open_position_allocation" in summary
    assert "points" in performance_response.json()
    assert "items" in exposure_response.json()
    assert "by_asset" in allocation_response.json()
    assert "total_pnl" in pnl_response.json()


def test_ai_training_pipeline_versions_deploys_compares_and_predicts() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        train_response = client.post(
            "/api/ai/models/train",
            headers=headers,
            json={
                "name": "Pipeline Test Model",
                "symbol": "BTCUSDT",
                "timeframe": "15m",
                "lookback": 240,
                "model_type": "random_forest",
                "training_params": {"n_estimators": 20, "max_depth": 4, "random_state": 42},
            },
        )
        assert train_response.status_code == 200, train_response.text
        model = train_response.json()

        retrain_response = client.post(
            f"/api/ai/models/{model['id']}/retrain",
            headers=headers,
            json={"lookback": 240, "training_params": {"n_estimators": 20, "max_depth": 4, "random_state": 42}},
        )
        assert retrain_response.status_code == 200, retrain_response.text
        retrained = retrain_response.json()

        deploy_response = client.post(f"/api/ai/models/{retrained['id']}/deploy", headers=headers)
        compare_response = client.post(
            "/api/ai/models/compare",
            headers=headers,
            json={"model_ids": [model["id"], retrained["id"]]},
        )
        predict_response = client.post(f"/api/ai/models/{retrained['id']}/predict", headers=headers)
        disable_response = client.post(f"/api/ai/models/{retrained['id']}/disable", headers=headers)

    assert model["version"] == 1
    assert retrained["version"] == 2
    assert retrained["parent_model_id"] == model["id"]
    assert "rsi_14" in model["feature_names"]
    assert "macd" in model["feature_names"]
    assert "adx_14" in model["feature_names"]
    assert deploy_response.status_code == 200
    assert deploy_response.json()["deployed"] is True
    assert deploy_response.json()["status"] == "deployed"
    assert compare_response.status_code == 200
    assert [item["rank"] for item in compare_response.json()] == [1, 2]
    assert predict_response.status_code == 200
    assert predict_response.json()["direction"] in {"buy", "sell"}
    assert "bb_width" in predict_response.json()["features"]
    assert disable_response.status_code == 200
    assert disable_response.json()["status"] == "disabled"


def test_neural_model_factory_uses_native_pytorch_when_available() -> None:
    service = ModelService()

    for model_type in ["lstm", "gru", "transformer"]:
        _model, params = service.create_model(model_type, {"epochs": 1, "hidden_dim": 8, "sequence_length": 3})
        if is_package_available("torch"):
            assert params["runtime_adapter"] == f"pytorch.{model_type}"
        else:
            assert params["runtime_adapter"] == f"sklearn.mlp_{model_type}_fallback_missing_torch"

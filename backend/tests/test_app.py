import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

test_db_path = Path(".tmp/test_app.sqlite")
test_db_path.parent.mkdir(exist_ok=True)
test_db_path.unlink(missing_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path.as_posix()}"

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import decode_jwt, encode_jwt
from app.main import app
from app.services.ai.models import ModelService, is_package_available
from app.services.admin import clear_login_throttles


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
                "exchange": "redaction-test",
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


def test_refresh_token_rotation_revokes_previous_token() -> None:
    with TestClient(app) as client:
        auth_headers(client, "rotation-admin@example.com")
        login_response = client.post(
            "/api/auth/login",
            json={"email": "rotation-admin@example.com", "password": "strong-password"},
        )
        old_refresh_token = login_response.json()["refresh_token"]
        refresh_response = client.post("/api/auth/refresh", json={"refresh_token": old_refresh_token})
        replay_response = client.post("/api/auth/refresh", json={"refresh_token": old_refresh_token})

    assert login_response.status_code == 200
    assert refresh_response.status_code == 200
    assert refresh_response.json()["refresh_token"] != old_refresh_token
    assert replay_response.status_code == 401


def test_logout_revokes_active_refresh_token() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client, "logout-admin@example.com")
        login_response = client.post(
            "/api/auth/login",
            json={"email": "logout-admin@example.com", "password": "strong-password"},
        )
        refresh_token = login_response.json()["refresh_token"]
        logout_response = client.post("/api/auth/logout", headers={"Authorization": headers["Authorization"]})
        refresh_response = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})

    assert login_response.status_code == 200
    assert logout_response.status_code == 200
    assert logout_response.json()["logged_out"] is True
    assert refresh_response.status_code == 401


def test_expired_access_token_is_rejected() -> None:
    with TestClient(app) as client:
        auth_headers(client, "expired-access@example.com")
        login_response = client.post(
            "/api/auth/login",
            json={"email": "expired-access@example.com", "password": "strong-password"},
        )
        payload = decode_jwt(login_response.json()["access_token"])
        assert payload is not None
        expired_token = encode_jwt(
            {
                "sub": payload["sub"],
                "role": payload["role"],
                "typ": "access",
                "exp": int((datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp()),
            }
        )
        me_response = client.get("/api/me", headers={"Authorization": f"Bearer {expired_token}"})

    assert login_response.status_code == 200
    assert me_response.status_code == 401


def test_expired_refresh_token_is_rejected() -> None:
    expired_refresh_token = encode_jwt(
        {
            "sub": "1",
            "role": "admin",
            "typ": "refresh",
            "jti": "expired-refresh-test",
            "exp": int((datetime.now(timezone.utc) - timedelta(minutes=1)).timestamp()),
        },
        secret=settings.jwt_refresh_secret,
    )

    with TestClient(app) as client:
        response = client.post("/api/auth/refresh", json={"refresh_token": expired_refresh_token})

    assert response.status_code == 401


def test_failed_login_attempts_are_throttled() -> None:
    original_max_attempts = settings.login_throttle_max_attempts
    original_lockout_seconds = settings.login_throttle_lockout_seconds
    original_window_seconds = settings.login_throttle_window_seconds
    clear_login_throttles()
    settings.login_throttle_max_attempts = 3
    settings.login_throttle_lockout_seconds = 60
    settings.login_throttle_window_seconds = 300
    try:
        with TestClient(app) as client:
            auth_headers(client, "throttled-admin@example.com")
            first_response = client.post(
                "/api/auth/login",
                json={"email": "throttled-admin@example.com", "password": "wrong-password"},
            )
            second_response = client.post(
                "/api/auth/login",
                json={"email": "throttled-admin@example.com", "password": "wrong-password"},
            )
            throttled_response = client.post(
                "/api/auth/login",
                json={"email": "throttled-admin@example.com", "password": "wrong-password"},
            )
            locked_response = client.post(
                "/api/auth/login",
                json={"email": "throttled-admin@example.com", "password": "strong-password"},
            )
    finally:
        settings.login_throttle_max_attempts = original_max_attempts
        settings.login_throttle_lockout_seconds = original_lockout_seconds
        settings.login_throttle_window_seconds = original_window_seconds
        clear_login_throttles()

    assert first_response.status_code == 401
    assert second_response.status_code == 401
    assert throttled_response.status_code == 429
    assert locked_response.status_code == 429
    assert "Retry-After" in locked_response.headers


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


def test_market_warehouse_import_and_history_endpoints() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        import_response = client.post(
            "/api/market/candles/import",
            headers=headers,
            json={
                "market": "crypto",
                "exchange": "binance",
                "timeframe": "5m",
                "candles": [
                    {
                        "symbol": "SOLUSDT",
                        "timeframe": "5m",
                        "opened_at": "2026-06-09T12:00:00Z",
                        "open": 150.0,
                        "high": 153.0,
                        "low": 149.5,
                        "close": 152.0,
                        "volume": 25000,
                        "spread": 0.01,
                    }
                ],
                "ticks": [
                    {
                        "symbol": "SOLUSDT",
                        "exchange": "binance",
                        "tick_time": "2026-06-09T12:00:30Z",
                        "bid": 151.99,
                        "ask": 152.01,
                        "price": 152.0,
                        "volume": 80,
                        "source": "import",
                    }
                ],
            },
        )
        candles_response = client.get(
            "/api/market/candles",
            headers=headers,
            params={"symbol": "SOLUSDT", "timeframe": "5m", "limit": 10},
        )
        history_response = client.get(
            "/api/market/history/SOLUSDT",
            headers=headers,
            params={"timeframe": "5m", "limit": 10},
        )

    assert import_response.status_code == 200, import_response.text
    assert import_response.json()["candle_inserted"] == 1
    assert candles_response.status_code == 200
    assert candles_response.json()[0]["source"] == "import"
    assert history_response.status_code == 200
    history = history_response.json()
    assert history["symbol"] == "SOLUSDT"
    assert history["candles"][0]["close"] == 152.0
    assert history["ticks"][0]["spread"] == 0.02
    assert {"signals", "predictions", "trades", "portfolio_snapshots"}.issubset(history)


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


def test_ai_feature_store_calculates_lists_and_exposes_feature_sets() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        calculate_response = client.post(
            "/api/features/calculate",
            headers=headers,
            json={"symbol": "BTCUSDT", "timeframe": "15m", "lookback": 240, "persist_last": 5},
        )
        features_response = client.get("/api/features", headers=headers, params={"limit": 5})
        symbol_response = client.get("/api/features/BTCUSDT", headers=headers, params={"limit": 5})
        sets_response = client.get("/api/features/sets", headers=headers)

    assert calculate_response.status_code == 200, calculate_response.text
    calculated = calculate_response.json()
    assert calculated["rows_calculated"] == 5
    latest_values = calculated["latest"]["values"]
    assert {"rsi_14", "macd", "bb_width", "volume_change", "price_change", "trend_direction"}.issubset(latest_values)
    assert features_response.status_code == 200
    assert features_response.json()
    assert symbol_response.status_code == 200
    assert all(item["symbol"] == "BTCUSDT" for item in symbol_response.json())
    assert sets_response.status_code == 200
    assert "default-ai-trading" in {item["name"] for item in sets_response.json()}


def test_market_scanner_endpoints_return_scan_results() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        scanner_response = client.get("/api/scanner", headers=headers)
        run_response = client.post("/api/scanner/run", headers=headers, json={"timeframe": "15m", "lookback": 240})
        signals_response = client.get("/api/scanner/signals", headers=headers)
        navigation_response = client.get("/api/navigation", headers=headers)

    assert scanner_response.status_code == 200
    rows = scanner_response.json()
    assert rows
    assert {
        "symbol",
        "current_price",
        "signal",
        "confidence",
        "risk_level",
        "rsi",
        "macd_signal",
        "trend_direction",
        "volatility",
        "recommended_action",
        "created_at",
    }.issubset(rows[0])
    assert run_response.status_code == 200
    assert run_response.json()
    assert signals_response.status_code == 200
    navigation = navigation_response.json()
    market = next(item for item in navigation if item["label"] == "Market")
    assert market["children"][0]["label"] == "Market Scanner"


def test_copilot_chat_returns_grounded_answer_and_history() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        chat_response = client.post(
            "/api/copilot/chat",
            headers=headers,
            json={"message": "What is my current portfolio risk?"},
        )
        history_response = client.get("/api/copilot/history", headers=headers)
        navigation_response = client.get("/api/navigation", headers=headers)

    assert chat_response.status_code == 200, chat_response.text
    payload = chat_response.json()
    assert payload["user_message"]["role"] == "user"
    assert payload["assistant_message"]["role"] == "assistant"
    assert payload["assistant_message"]["cards"]
    assert payload["assistant_message"]["suggested_questions"]
    assert history_response.status_code == 200
    assert len(history_response.json()) >= 2
    ai_nav = next(item for item in navigation_response.json() if item["label"] == "AI")
    assert "AI Copilot" in {child["label"] for child in ai_nav["children"]}


def test_sentiment_endpoints_return_market_and_symbol_sentiment() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        market_response = client.get("/api/sentiment", headers=headers)
        symbol_response = client.get("/api/sentiment/BTCUSDT", headers=headers)
        analyze_response = client.post("/api/sentiment/analyze", headers=headers, json={"symbol": "ETHUSDT"})
        navigation_response = client.get("/api/navigation", headers=headers)

    assert market_response.status_code == 200
    market = market_response.json()
    assert {"market_sentiment_score", "market_status", "items"}.issubset(market)
    assert market["items"]
    assert {
        "symbol",
        "sentiment_score",
        "status",
        "headline",
        "source",
        "date",
        "impact_level",
        "related_asset",
    }.issubset(market["items"][0])
    assert symbol_response.status_code == 200
    assert all(item["symbol"] == "BTCUSDT" for item in symbol_response.json()["items"])
    assert analyze_response.status_code == 200
    assert all(item["symbol"] == "ETHUSDT" for item in analyze_response.json()["items"])
    market_nav = next(item for item in navigation_response.json() if item["label"] == "Market")
    assert "News Sentiment" in {child["label"] for child in market_nav["children"]}


def test_economic_calendar_endpoints_filter_and_create_events() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        events_response = client.get("/api/calendar/events", headers=headers)
        high_impact_response = client.get("/api/calendar/high-impact", headers=headers)
        create_response = client.post(
            "/api/calendar/events",
            headers=headers,
            json={
                "event_name": "Canada Jobs Report",
                "country": "Canada",
                "impact_level": "medium",
                "event_datetime": "2026-06-12T12:30:00Z",
                "affected_assets": ["CAD", "USDCAD"],
                "previous_value": "22K",
                "forecast_value": "18K",
                "actual_value": None,
            },
        )
        filtered_response = client.get("/api/calendar/events", headers=headers, params={"country": "Canada", "asset": "CAD"})
        navigation_response = client.get("/api/navigation", headers=headers)

    assert events_response.status_code == 200
    events = events_response.json()
    assert events
    assert {
        "event_name",
        "country",
        "impact_level",
        "event_datetime",
        "affected_assets",
        "previous_value",
        "forecast_value",
        "actual_value",
        "trading_blackout_warning",
        "high_impact",
    }.issubset(events[0])
    assert high_impact_response.status_code == 200
    assert all(event["high_impact"] is True for event in high_impact_response.json())
    assert create_response.status_code == 200
    assert create_response.json()["event_name"] == "Canada Jobs Report"
    assert filtered_response.status_code == 200
    assert any(event["country"] == "Canada" for event in filtered_response.json())
    market_nav = next(item for item in navigation_response.json() if item["label"] == "Market")
    assert "Economic Calendar" in {child["label"] for child in market_nav["children"]}


def test_websocket_stream_routes_emit_payloads() -> None:
    with TestClient(app) as client:
        for path in [
            "/api/ws/prices",
            "/api/ws/signals",
            "/api/ws/orders",
            "/api/ws/positions",
            "/api/ws/portfolio",
            "/api/ws/notifications",
            "/ws/prices",
            "/ws/signals",
            "/ws/orders",
            "/ws/positions",
            "/ws/portfolio",
            "/ws/notifications",
        ]:
            with client.websocket_connect(path) as websocket:
                connected = websocket.receive_json()
                payload = websocket.receive_json()

            assert connected["type"] == path.rsplit("/", 1)[-1]
            assert connected["payload"]["status"] == "connected"
            assert payload["type"] == path.rsplit("/", 1)[-1]
            assert "payload" in payload


def test_notification_settings_and_bulk_mark_read() -> None:
    original_provider_settings = {
        "notification_email_smtp_host": settings.notification_email_smtp_host,
        "notification_email_from": settings.notification_email_from,
        "notification_email_to": settings.notification_email_to,
        "telegram_bot_token": settings.telegram_bot_token,
        "telegram_chat_id": settings.telegram_chat_id,
        "whatsapp_access_token": settings.whatsapp_access_token,
        "whatsapp_phone_number_id": settings.whatsapp_phone_number_id,
        "whatsapp_to_number": settings.whatsapp_to_number,
        "discord_webhook_url": settings.discord_webhook_url,
    }
    settings.notification_email_smtp_host = None
    settings.notification_email_from = None
    settings.notification_email_to = []
    settings.telegram_bot_token = None
    settings.telegram_chat_id = None
    settings.whatsapp_access_token = None
    settings.whatsapp_phone_number_id = None
    settings.whatsapp_to_number = None
    settings.discord_webhook_url = None
    try:
        with TestClient(app) as client:
            headers = auth_headers(client)
            settings_response = client.get("/api/notifications/settings", headers=headers)
            update_response = client.put(
                "/api/notifications/settings",
                headers=headers,
                json={
                    "email_enabled": True,
                    "telegram_enabled": True,
                    "trade_alerts": False,
                    "risk_alerts": True,
                    "ai_alerts": True,
                    "system_alerts": True,
                },
            )
            notification_response = client.post(
                "/api/notifications",
                headers=headers,
                json={"title": "Broker disconnected", "message": "Binance paper adapter disconnected.", "severity": "warning"},
            )
            mark_response = client.post(
                "/api/notifications/mark-read",
                headers=headers,
                json={"notification_ids": [notification_response.json()["id"]]},
            )
            navigation_response = client.get("/api/navigation", headers=headers)
    finally:
        for key, value in original_provider_settings.items():
            setattr(settings, key, value)

    assert settings_response.status_code == 200
    settings_payload = settings_response.json()
    assert {"channels", "events", "in_app_enabled", "email_enabled"}.issubset(settings_payload)
    assert {"trade_executed", "trade_rejected", "stop_loss_hit", "take_profit_hit", "ai_signal_generated"}.issubset(
        {event["key"] for event in settings_payload["events"]}
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["email_enabled"] is True
    assert updated["telegram_enabled"] is True
    email_channel = next(channel for channel in updated["channels"] if channel["key"] == "email")
    assert email_channel["placeholder"] is False
    assert email_channel["configured"] is False
    assert any(event["category"] == "trade" and event["enabled"] is False for event in updated["events"])
    assert notification_response.status_code == 200
    notification = notification_response.json()
    assert {"in_app", "email", "telegram", "whatsapp", "discord"}.issubset(notification["delivery_status"])
    assert notification["delivery_status"]["in_app"]["status"] == "delivered"
    assert notification["delivery_status"]["email"]["status"] == "not_configured"
    assert "delivery_attempted_at" in notification
    assert mark_response.status_code == 200
    assert mark_response.json()["updated_count"] == 1
    assert mark_response.json()["notifications"][0]["is_read"] is True
    administration = next(item for item in navigation_response.json() if item["label"] == "Administration")
    assert "Notification Settings" in {child["label"] for child in administration["children"]}


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


def test_paper_trading_engine_simulates_orders_positions_and_reset() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        account_response = client.get("/api/paper/account", headers=headers)
        order_response = client.post(
            "/api/paper/orders",
            headers=headers,
            json={"symbol": "BTCUSDT", "side": "buy", "order_type": "market", "quantity": 0.001},
        )
        orders_response = client.get("/api/paper/orders", headers=headers)
        positions_response = client.get("/api/paper/positions", headers=headers)
        performance_response = client.get("/api/paper/performance", headers=headers)
        position_id = positions_response.json()[0]["id"]
        close_response = client.post(f"/api/paper/positions/{position_id}/close", headers=headers)
        reset_response = client.post("/api/paper/reset", headers=headers, json={"starting_balance": 10000})

    assert account_response.status_code == 200
    assert account_response.json()["paper_equity"] >= 0
    assert order_response.status_code == 200, order_response.text
    assert order_response.json()["execution_mode"] == "paper"
    assert order_response.json()["status"] == "filled"
    assert orders_response.status_code == 200
    assert orders_response.json()[0]["symbol"] == "BTCUSDT"
    assert positions_response.status_code == 200
    assert positions_response.json()[0]["status"] == "open"
    assert performance_response.status_code == 200
    assert performance_response.json()["points"]
    assert close_response.status_code == 200
    assert close_response.json()["status"] == "closed"
    assert reset_response.status_code == 200
    assert reset_response.json()["account"]["cash_balance"] == 10000


def test_performance_analytics_endpoints_return_trade_metrics() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        order_response = client.post(
            "/api/paper/orders",
            headers=headers,
            json={"symbol": "ETHUSDT", "side": "buy", "order_type": "market", "quantity": 0.02},
        )
        assert order_response.status_code == 200, order_response.text
        positions_response = client.get("/api/paper/positions", headers=headers)
        position_id = positions_response.json()[0]["id"]
        close_response = client.post(f"/api/paper/positions/{position_id}/close", headers=headers)
        assert close_response.status_code == 200, close_response.text

        performance_response = client.get("/api/analytics/performance", headers=headers)
        equity_response = client.get("/api/analytics/equity-curve", headers=headers)
        strategies_response = client.get("/api/analytics/strategies", headers=headers)
        trades_response = client.get("/api/analytics/trades", headers=headers)

    assert performance_response.status_code == 200
    performance = performance_response.json()
    assert {
        "win_rate",
        "loss_rate",
        "average_win",
        "average_loss",
        "profit_factor",
        "sharpe_ratio",
        "max_drawdown",
        "total_trades",
        "winning_trades",
        "losing_trades",
        "best_trade",
        "worst_trade",
    }.issubset(performance)
    assert performance["total_trades"] >= 1
    assert equity_response.status_code == 200
    assert "points" in equity_response.json()
    assert strategies_response.status_code == 200
    assert "strategies" in strategies_response.json()
    assert trades_response.status_code == 200
    assert trades_response.json()


def test_broker_registry_hides_secrets_and_placeholder_execution_is_guarded() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        brokers_response = client.get("/api/brokers", headers=headers)
        connect_response = client.post("/api/brokers/connect", headers=headers, json={"broker": "binance"})
        placeholder_order_response = client.post(
            "/api/brokers/bybit/orders",
            headers=headers,
            json={"symbol": "BTCUSDT", "side": "buy", "order_type": "market", "quantity": 0.01},
        )

    assert brokers_response.status_code == 200
    brokers = brokers_response.json()
    assert {"binance", "bybit", "okx", "kucoin", "mt5"}.issubset({broker["name"] for broker in brokers})
    assert all("api_key" not in broker for broker in brokers)
    assert all("api_secret" not in broker for broker in brokers)
    assert all("api_key_configured" in broker for broker in brokers)
    assert connect_response.status_code == 200
    assert connect_response.json()["broker"]["name"] == "binance"
    assert placeholder_order_response.status_code == 501


def test_advanced_risk_engine_endpoints() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        summary_response = client.get("/api/risk/summary", headers=headers)
        limits_response = client.get("/api/risk/limits", headers=headers)
        update_limits_response = client.put(
            "/api/risk/limits",
            headers=headers,
            json={"max_weekly_loss": 0.07, "max_drawdown": 0.12, "max_leverage": 2.0},
        )
        validation_response = client.post(
            "/api/risk/validate-trade",
            headers=headers,
            json={
                "symbol": "BTCUSDT",
                "side": "buy",
                "price": 65000,
                "quantity": 0.001,
                "stop_loss": 64000,
                "take_profit": 67000,
                "leverage": 1,
                "execution_mode": "paper",
            },
        )
        sizing_response = client.post(
            "/api/risk/position-size",
            headers=headers,
            json={
                "symbol": "BTCUSDT",
                "method": "fixed_percentage_risk",
                "entry_price": 65000,
                "stop_loss": 64000,
                "risk_percent": 0.01,
            },
        )
        enable_response = client.post("/api/risk/circuit-breaker/enable", headers=headers)
        disable_response = client.post("/api/risk/circuit-breaker/disable", headers=headers)

    assert summary_response.status_code == 200
    assert "risk_score" in summary_response.json()
    assert limits_response.status_code == 200
    assert "max_leverage" in limits_response.json()
    assert update_limits_response.status_code == 200
    assert update_limits_response.json()["max_leverage"] == 2.0
    assert validation_response.status_code == 200
    assert "risk_score" in validation_response.json()
    assert sizing_response.status_code == 200
    assert sizing_response.json()["quantity"] > 0
    assert enable_response.status_code == 200
    assert enable_response.json()["circuit_breaker_enabled"] is True
    assert disable_response.status_code == 200
    assert disable_response.json()["circuit_breaker_enabled"] is False


def test_strategy_builder_creates_updates_and_evaluates_rules() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        create_response = client.post(
            "/api/strategies/builder",
            headers=headers,
            json={
                "name": "Builder Test Strategy",
                "description": "Rule builder test",
                "timeframe": "15m",
                "enabled": False,
                "rules": [
                    {
                        "name": "RSI entry",
                        "priority": 1,
                        "logic_operator": "AND",
                        "enabled": True,
                        "conditions": [
                            {"sequence": 1, "indicator": "RSI", "period": 14, "operator": "<", "value": 101}
                        ],
                        "action": {"action": "BUY"},
                    }
                ],
            },
        )
        assert create_response.status_code == 200, create_response.text
        strategy_id = create_response.json()["id"]

        list_response = client.get("/api/strategies/builder", headers=headers)
        rules_response = client.get(f"/api/strategies/{strategy_id}/rules", headers=headers)
        update_response = client.put(
            f"/api/strategies/{strategy_id}/rules",
            headers=headers,
            json={
                "rules": [
                    {
                        "name": "Price change entry",
                        "priority": 1,
                        "logic_operator": "AND",
                        "enabled": True,
                        "conditions": [
                            {"sequence": 1, "indicator": "PRICE_CHANGE", "period": 1, "operator": ">", "value": -1}
                        ],
                        "action": {"action": "SELL"},
                    }
                ]
            },
        )
        evaluate_response = client.post(
            f"/api/strategies/{strategy_id}/evaluate",
            headers=headers,
            json={"symbol": "BTCUSDT", "timeframe": "15m", "lookback": 120},
        )

    assert list_response.status_code == 200
    assert any(item["id"] == strategy_id for item in list_response.json())
    assert rules_response.status_code == 200
    assert rules_response.json()[0]["conditions"][0]["indicator"] == "RSI"
    assert update_response.status_code == 200
    assert update_response.json()[0]["actions"][0]["action"] == "SELL"
    assert evaluate_response.status_code == 200, evaluate_response.text
    evaluation = evaluate_response.json()
    assert evaluation["action"] == "SELL"
    assert evaluation["triggered_rule_id"] is not None
    assert "PRICE_CHANGE" in evaluation["indicators"]


def test_walk_forward_backtest_persists_windows_and_aggregate_result() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        run_response = client.post(
            "/api/backtests/walk-forward",
            headers=headers,
            json={
                "symbol": "BTCUSDT",
                "timeframe": "15m",
                "initial_balance": 10000,
                "training_period": 60,
                "validation_period": 30,
                "test_period": 30,
                "rolling_windows": 3,
            },
        )
        assert run_response.status_code == 200, run_response.text
        run = run_response.json()
        lookup_response = client.get(f"/api/backtests/walk-forward/{run['id']}", headers=headers)

    assert run["id"] > 0
    assert run["status"] == "completed"
    assert len(run["window_metrics"]) == 3
    assert len(run["optimization_results"]) == 3
    assert len(run["out_of_sample_results"]) == 3
    assert run["aggregated_result"]["windows"] == 3
    assert "robustness_score" in run["aggregated_result"]
    assert lookup_response.status_code == 200
    assert lookup_response.json()["id"] == run["id"]


def test_monte_carlo_risk_simulation_persists_and_returns_distribution() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client)
        run_response = client.post(
            "/api/risk/monte-carlo",
            headers=headers,
            json={
                "starting_balance": 10000,
                "win_rate": 0.55,
                "average_win": 1.4,
                "average_loss": 1.0,
                "number_of_trades": 50,
                "number_of_simulations": 1000,
                "risk_per_trade": 0.01,
            },
        )
        assert run_response.status_code == 200, run_response.text
        run = run_response.json()
        lookup_response = client.get(f"/api/risk/monte-carlo/{run['id']}", headers=headers)

    assert run["id"] > 0
    assert 0 <= run["probability_of_ruin"] <= 1
    assert run["ending_equity_distribution"]
    assert "ending_equity" in run["confidence_intervals"]
    assert run["risk_recommendation"]
    assert lookup_response.status_code == 200
    assert lookup_response.json()["id"] == run["id"]


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
        approve_response = client.post(
            f"/api/ai/models/{model['id']}/approve",
            headers=headers,
            json={"notes": "Approved for lifecycle test."},
        )

        retrain_response = client.post(
            f"/api/ai/models/{model['id']}/retrain",
            headers=headers,
            json={"lookback": 240, "training_params": {"n_estimators": 20, "max_depth": 4, "random_state": 42}},
        )
        assert retrain_response.status_code == 200, retrain_response.text
        retrained = retrain_response.json()

        deploy_response = client.post(f"/api/ai/models/{retrained['id']}/deploy", headers=headers)
        activate_response = client.post(f"/api/ai/models/{retrained['id']}/activate", headers=headers)
        schedule_response = client.post(
            f"/api/ai/models/{retrained['id']}/retrain-schedule",
            headers=headers,
            json={"interval_hours": 24},
        )
        detail_response = client.get(f"/api/ai/models/{retrained['id']}", headers=headers)
        evaluation_response = client.get(f"/api/ai/evaluation/{retrained['id']}", headers=headers)
        active_predict_response = client.post(
            "/api/ai/predict",
            headers=headers,
            json={"symbol": "BTCUSDT", "timeframe": "15m", "model_type": "random_forest"},
        )
        pipeline_train_response = client.post(
            "/api/ai/train",
            headers=headers,
            json={
                "name": "Pipeline Feature Selection Model",
                "symbol": "BTCUSDT",
                "timeframe": "15m",
                "lookback": 240,
                "model_type": "random_forest",
                "selected_features": ["rsi_14", "macd", "ema_20", "sma_20", "bb_width", "volume_ratio"],
            },
        )
        compare_response = client.post(
            "/api/ai/models/compare",
            headers=headers,
            json={"model_ids": [model["id"], retrained["id"]]},
        )
        predict_response = client.post(f"/api/ai/models/{retrained['id']}/predict", headers=headers)
        drift_response = client.post(f"/api/ai/models/{retrained['id']}/drift-check", headers=headers)
        disable_response = client.post(f"/api/ai/models/{retrained['id']}/disable", headers=headers)

    assert model["version"] == 1
    assert model["approval_status"] == "pending"
    assert model["champion"] is False
    assert "feature_baseline" in model["metrics"]
    assert approve_response.status_code == 200
    assert approve_response.json()["approval_status"] == "approved"
    assert retrained["version"] == 2
    assert retrained["parent_model_id"] == model["id"]
    assert retrained["challenger_of_id"] == model["id"]
    assert "rsi_14" in model["feature_names"]
    assert "macd" in model["feature_names"]
    assert "adx_14" in model["feature_names"]
    assert deploy_response.status_code == 200
    assert deploy_response.json()["deployed"] is True
    assert deploy_response.json()["champion"] is True
    assert deploy_response.json()["approval_status"] == "approved"
    assert deploy_response.json()["status"] == "deployed"
    assert activate_response.status_code == 200
    assert activate_response.json()["deployed"] is True
    assert schedule_response.status_code == 200
    assert schedule_response.json()["retrain_interval_hours"] == 24
    assert schedule_response.json()["next_retrain_at"] is not None
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == retrained["id"]
    assert evaluation_response.status_code == 200
    assert "profit_factor" in evaluation_response.json()
    assert active_predict_response.status_code == 200
    assert active_predict_response.json()["model_id"] == retrained["id"]
    assert active_predict_response.json()["prediction_id"] is not None
    assert pipeline_train_response.status_code == 200, pipeline_train_response.text
    assert pipeline_train_response.json()["feature_names"] == ["rsi_14", "macd", "ema_20", "sma_20", "bb_width", "volume_ratio"]
    assert compare_response.status_code == 200
    assert [item["rank"] for item in compare_response.json()] == [1, 2]
    assert {"comparison", "champion", "approval_status"}.issubset(compare_response.json()[0])
    assert predict_response.status_code == 200
    assert predict_response.json()["direction"] in {"buy", "sell"}
    assert predict_response.json()["prediction_id"] is not None
    assert "bb_width" in predict_response.json()["features"]
    assert drift_response.status_code == 200
    assert drift_response.json()["model_drift"]["status"] in {"stable", "watch"}
    assert drift_response.json()["feature_drift"]["status"] in {"stable", "drifted"}
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

import os
from pathlib import Path

test_db_path = Path(".tmp/test_app.sqlite")
test_db_path.parent.mkdir(exist_ok=True)
test_db_path.unlink(missing_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path.as_posix()}"

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


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
        headers = auth_headers(client, "navigation-admin@example.com")
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
            health_response = client.get("/api/health")
            missing_key_response = client.get("/api/signals")
            valid_key_response = client.get("/api/signals", headers={"X-API-Key": "test-secret"})
    finally:
        settings.api_key = original_api_key

    assert health_response.status_code == 200
    assert missing_key_response.status_code == 401
    assert valid_key_response.status_code == 200


def test_api_credentials_do_not_return_secret() -> None:
    with TestClient(app) as client:
        headers = auth_headers(client, "credential-admin@example.com")
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

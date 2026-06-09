import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.sqlite")

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


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
        me_response = client.get("/api/me")
        navigation_response = client.get("/api/navigation")

    assert me_response.status_code == 200
    assert navigation_response.status_code == 200

    permissions = set(me_response.json()["permissions"])
    navigation = navigation_response.json()

    assert {item["href"] for item in navigation} == {"#/overview", "#/trading", "#/activity"}
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

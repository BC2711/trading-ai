import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("API_KEY", raising=False)

    with pytest.raises(ValidationError, match="API_KEY is required"):
        Settings()


def test_production_rejects_wildcard_hosts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("API_KEY", "prod-secret")
    monkeypatch.setenv("ALLOWED_HOSTS", '["*"]')

    with pytest.raises(ValidationError, match="ALLOWED_HOSTS cannot contain"):
        Settings()

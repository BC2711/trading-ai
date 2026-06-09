from configparser import ConfigParser

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_default_database_url_uses_local_postgres(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    settings = Settings(_env_file=None)

    assert settings.database_url == "postgresql+psycopg://trading:trading@localhost:5432/trading"


def test_alembic_fallback_database_url_matches_local_postgres() -> None:
    config = ConfigParser()
    config.read("alembic.ini")

    assert config["alembic"]["sqlalchemy.url"] == "postgresql+psycopg://trading:trading@localhost:5432/trading"


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

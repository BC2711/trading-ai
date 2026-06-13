from configparser import ConfigParser

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect, text

from app.core.config import Settings
from app.db.schema_compat import ensure_schema_compatibility


def test_default_database_url_uses_local_postgres(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    settings = Settings(_env_file=None)

    assert settings.database_url == "postgresql+psycopg://trading:trading@localhost:5432/trading"


def test_alembic_fallback_database_url_matches_local_postgres() -> None:
    config = ConfigParser()
    config.read("alembic.ini")

    assert config["alembic"]["sqlalchemy.url"] == "postgresql+psycopg://trading:trading@localhost:5432/trading"


def test_schema_compatibility_adds_missing_risk_setting_columns(tmp_path) -> None:
    database_path = tmp_path / "legacy.sqlite"
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE risk_settings (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(120) NOT NULL,
                    max_risk_per_trade FLOAT NOT NULL,
                    max_daily_loss FLOAT NOT NULL,
                    max_open_trades INTEGER NOT NULL,
                    max_symbol_exposure FLOAT NOT NULL,
                    status VARCHAR(16) NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )

    ensure_schema_compatibility(engine)

    columns = {column["name"] for column in inspect(engine).get_columns("risk_settings")}
    assert {"max_weekly_loss", "max_drawdown", "max_leverage"}.issubset(columns)
    assert {"max_consecutive_losses", "emergency_stop", "live_trading_enabled"}.issubset(columns)


def test_schema_compatibility_adds_missing_strategy_columns(tmp_path) -> None:
    database_path = tmp_path / "legacy_strategy.sqlite"
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE strategies (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(120) NOT NULL,
                    description VARCHAR(500) NOT NULL,
                    timeframe VARCHAR(8) NOT NULL,
                    status VARCHAR(16) NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )

    ensure_schema_compatibility(engine)

    columns = {column["name"] for column in inspect(engine).get_columns("strategies")}
    assert {"parameters", "enabled", "performance"}.issubset(columns)


def test_schema_compatibility_adds_missing_market_candle_columns(tmp_path) -> None:
    database_path = tmp_path / "legacy_market.sqlite"
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE market_candles (
                    id INTEGER PRIMARY KEY,
                    symbol_id INTEGER NOT NULL,
                    timeframe VARCHAR(8) NOT NULL,
                    opened_at DATETIME NOT NULL,
                    open FLOAT NOT NULL,
                    high FLOAT NOT NULL,
                    low FLOAT NOT NULL,
                    close FLOAT NOT NULL,
                    volume FLOAT NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )

    ensure_schema_compatibility(engine)

    columns = {column["name"] for column in inspect(engine).get_columns("market_candles")}
    assert "spread" in columns


def test_schema_compatibility_adds_missing_notification_delivery_columns(tmp_path) -> None:
    database_path = tmp_path / "legacy_notifications.sqlite"
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE notifications (
                    id INTEGER PRIMARY KEY,
                    title VARCHAR(180) NOT NULL,
                    message VARCHAR(800) NOT NULL,
                    severity VARCHAR(16) NOT NULL,
                    is_read BOOLEAN NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )

    ensure_schema_compatibility(engine)

    columns = {column["name"] for column in inspect(engine).get_columns("notifications")}
    assert {"delivery_status", "delivery_attempted_at"}.issubset(columns)


def test_production_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("API_KEY", raising=False)

    with pytest.raises(ValidationError, match="API_KEY is required"):
        Settings()


def test_production_rejects_wildcard_hosts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("API_KEY", "prod-secret")
    monkeypatch.setenv("JWT_SECRET", "prod-jwt-secret")
    monkeypatch.setenv("JWT_REFRESH_SECRET", "prod-refresh-secret")
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_SECRET", "prod-credential-secret")
    monkeypatch.setenv("ALLOWED_HOSTS", '["*"]')

    with pytest.raises(ValidationError, match="ALLOWED_HOSTS cannot contain"):
        Settings()


def test_production_requires_refresh_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("API_KEY", "prod-secret")
    monkeypatch.setenv("JWT_SECRET", "prod-jwt-secret")
    monkeypatch.setenv("JWT_REFRESH_SECRET", "change-me-refresh-token-secret")
    monkeypatch.setenv("CREDENTIAL_ENCRYPTION_SECRET", "prod-credential-secret")

    with pytest.raises(ValidationError, match="JWT_REFRESH_SECRET must be changed"):
        Settings()

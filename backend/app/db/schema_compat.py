import logging

from sqlalchemy import Engine, inspect, text

logger = logging.getLogger(__name__)


RISK_SETTING_COLUMNS = {
    "max_consecutive_losses": {
        "postgresql": "INTEGER NOT NULL DEFAULT 3",
        "sqlite": "INTEGER NOT NULL DEFAULT 3",
        "default": "INTEGER NOT NULL DEFAULT 3",
    },
    "emergency_stop": {
        "postgresql": "BOOLEAN NOT NULL DEFAULT false",
        "sqlite": "BOOLEAN NOT NULL DEFAULT 0",
        "default": "BOOLEAN NOT NULL DEFAULT false",
    },
    "live_trading_enabled": {
        "postgresql": "BOOLEAN NOT NULL DEFAULT false",
        "sqlite": "BOOLEAN NOT NULL DEFAULT 0",
        "default": "BOOLEAN NOT NULL DEFAULT false",
    },
    "max_weekly_loss": {
        "postgresql": "FLOAT NOT NULL DEFAULT 0.08",
        "sqlite": "FLOAT NOT NULL DEFAULT 0.08",
        "default": "FLOAT NOT NULL DEFAULT 0.08",
    },
    "max_drawdown": {
        "postgresql": "FLOAT NOT NULL DEFAULT 0.15",
        "sqlite": "FLOAT NOT NULL DEFAULT 0.15",
        "default": "FLOAT NOT NULL DEFAULT 0.15",
    },
    "max_leverage": {
        "postgresql": "FLOAT NOT NULL DEFAULT 1.0",
        "sqlite": "FLOAT NOT NULL DEFAULT 1.0",
        "default": "FLOAT NOT NULL DEFAULT 1.0",
    },
}

STRATEGY_COLUMNS = {
    "parameters": {
        "postgresql": "JSON NOT NULL DEFAULT '{}'",
        "sqlite": "JSON NOT NULL DEFAULT '{}'",
        "default": "JSON NOT NULL DEFAULT '{}'",
    },
    "enabled": {
        "postgresql": "BOOLEAN NOT NULL DEFAULT true",
        "sqlite": "BOOLEAN NOT NULL DEFAULT 1",
        "default": "BOOLEAN NOT NULL DEFAULT true",
    },
    "performance": {
        "postgresql": "JSON NOT NULL DEFAULT '{}'",
        "sqlite": "JSON NOT NULL DEFAULT '{}'",
        "default": "JSON NOT NULL DEFAULT '{}'",
    },
}

MARKET_CANDLE_COLUMNS = {
    "spread": {
        "postgresql": "FLOAT NOT NULL DEFAULT 0",
        "sqlite": "FLOAT NOT NULL DEFAULT 0",
        "default": "FLOAT NOT NULL DEFAULT 0",
    },
}

NOTIFICATION_COLUMNS = {
    "delivery_status": {
        "postgresql": "JSON NOT NULL DEFAULT '{}'",
        "sqlite": "JSON NOT NULL DEFAULT '{}'",
        "default": "JSON NOT NULL DEFAULT '{}'",
    },
    "delivery_attempted_at": {
        "postgresql": "TIMESTAMP WITH TIME ZONE NULL",
        "sqlite": "DATETIME NULL",
        "default": "TIMESTAMP NULL",
    },
}


def ensure_schema_compatibility(engine: Engine) -> None:
    """Repair additive columns needed before startup seed queries can run."""
    with engine.begin() as connection:
        inspector = inspect(connection)
        table_names = set(inspector.get_table_names())
        if not {"risk_settings", "strategies", "market_candles", "notifications"}.intersection(table_names):
            return

        dialect = connection.dialect.name
        if "market_candles" in table_names:
            _add_missing_columns(connection, "market_candles", MARKET_CANDLE_COLUMNS, dialect)
        if "risk_settings" in table_names:
            _add_missing_columns(connection, "risk_settings", RISK_SETTING_COLUMNS, dialect)
        if "strategies" in table_names:
            _add_missing_columns(connection, "strategies", STRATEGY_COLUMNS, dialect)
        if "notifications" in table_names:
            _add_missing_columns(connection, "notifications", NOTIFICATION_COLUMNS, dialect)


def _add_missing_columns(connection, table_name: str, columns: dict[str, dict[str, str]], dialect: str) -> None:
    existing_columns = {column["name"] for column in inspect(connection).get_columns(table_name)}
    for column_name, ddl_by_dialect in columns.items():
        if column_name in existing_columns:
            continue
        column_ddl = ddl_by_dialect.get(dialect, ddl_by_dialect["default"])
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_ddl}"))
        logger.info("Added missing %s.%s column during startup schema compatibility check.", table_name, column_name)

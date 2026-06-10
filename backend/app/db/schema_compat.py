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


def ensure_schema_compatibility(engine: Engine) -> None:
    """Repair additive columns needed before startup seed queries can run."""
    with engine.begin() as connection:
        inspector = inspect(connection)
        if "risk_settings" not in inspector.get_table_names():
            return

        existing_columns = {column["name"] for column in inspector.get_columns("risk_settings")}
        dialect = connection.dialect.name
        for column_name, ddl_by_dialect in RISK_SETTING_COLUMNS.items():
            if column_name in existing_columns:
                continue
            column_ddl = ddl_by_dialect.get(dialect, ddl_by_dialect["default"])
            connection.execute(text(f"ALTER TABLE risk_settings ADD COLUMN {column_name} {column_ddl}"))
            logger.info("Added missing risk_settings.%s column during startup schema compatibility check.", column_name)

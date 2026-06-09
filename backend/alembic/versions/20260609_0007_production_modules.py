"""production modules

Revision ID: 20260609_0007
Revises: 20260607_0006
Create Date: 2026-06-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260609_0007"
down_revision: str | None = "20260607_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def columns(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if column.name in columns(table_name):
        return
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.add_column(column)
        return
    op.add_column(table_name, column)


def upgrade() -> None:
    if has_table("strategies"):
        add_column_if_missing("strategies", sa.Column("parameters", sa.JSON(), nullable=False, server_default="{}"))
        add_column_if_missing("strategies", sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
        add_column_if_missing("strategies", sa.Column("performance", sa.JSON(), nullable=False, server_default="{}"))

    if has_table("risk_settings"):
        add_column_if_missing("risk_settings", sa.Column("max_consecutive_losses", sa.Integer(), nullable=False, server_default="3"))
        add_column_if_missing("risk_settings", sa.Column("emergency_stop", sa.Boolean(), nullable=False, server_default=sa.false()))
        add_column_if_missing("risk_settings", sa.Column("live_trading_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))

    if has_table("backtest_runs"):
        add_column_if_missing("backtest_runs", sa.Column("fees", sa.Float(), nullable=False, server_default="0"))
        add_column_if_missing("backtest_runs", sa.Column("slippage", sa.Float(), nullable=False, server_default="0"))
        add_column_if_missing("backtest_runs", sa.Column("spread", sa.Float(), nullable=False, server_default="0"))
        add_column_if_missing("backtest_runs", sa.Column("profit_factor", sa.Float(), nullable=False, server_default="0"))
        add_column_if_missing("backtest_runs", sa.Column("sharpe_ratio", sa.Float(), nullable=False, server_default="0"))
        add_column_if_missing("backtest_runs", sa.Column("equity_curve", sa.JSON(), nullable=False, server_default="[]"))

    if has_table("paper_orders"):
        add_column_if_missing("paper_orders", sa.Column("execution_mode", sa.String(length=16), nullable=False, server_default="paper"))
        add_column_if_missing("paper_orders", sa.Column("exchange_order_id", sa.String(length=80), nullable=True))
        add_column_if_missing("paper_orders", sa.Column("failure_reason", sa.String(length=500), nullable=True))

    if not has_table("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("full_name", sa.String(length=160), nullable=False),
            sa.Column("hashed_password", sa.String(length=300), nullable=False),
            sa.Column("role", sa.String(length=24), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email"),
        )
        op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
        op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
        op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)
        op.create_index(op.f("ix_users_is_active"), "users", ["is_active"], unique=False)
        op.create_index(op.f("ix_users_created_at"), "users", ["created_at"], unique=False)

    if not has_table("api_credentials"):
        op.create_table(
            "api_credentials",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("exchange", sa.String(length=48), nullable=False),
            sa.Column("api_key", sa.String(length=255), nullable=False),
            sa.Column("encrypted_api_secret", sa.String(length=1000), nullable=False),
            sa.Column("mode", sa.String(length=16), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_api_credentials_id"), "api_credentials", ["id"], unique=False)
        op.create_index(op.f("ix_api_credentials_exchange"), "api_credentials", ["exchange"], unique=False)
        op.create_index(op.f("ix_api_credentials_mode"), "api_credentials", ["mode"], unique=False)
        op.create_index(op.f("ix_api_credentials_is_active"), "api_credentials", ["is_active"], unique=False)
        op.create_index(op.f("ix_api_credentials_created_at"), "api_credentials", ["created_at"], unique=False)

    if not has_table("ai_model_metadata"):
        op.create_table(
            "ai_model_metadata",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("symbol", sa.String(length=24), nullable=False),
            sa.Column("timeframe", sa.String(length=8), nullable=False),
            sa.Column("model_type", sa.String(length=64), nullable=False),
            sa.Column("model_path", sa.String(length=500), nullable=False),
            sa.Column("metrics", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(length=24), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_ai_model_metadata_id"), "ai_model_metadata", ["id"], unique=False)
        op.create_index(op.f("ix_ai_model_metadata_name"), "ai_model_metadata", ["name"], unique=False)
        op.create_index(op.f("ix_ai_model_metadata_symbol"), "ai_model_metadata", ["symbol"], unique=False)
        op.create_index(op.f("ix_ai_model_metadata_status"), "ai_model_metadata", ["status"], unique=False)
        op.create_index(op.f("ix_ai_model_metadata_created_at"), "ai_model_metadata", ["created_at"], unique=False)

    if not has_table("notifications"):
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=180), nullable=False),
            sa.Column("message", sa.String(length=800), nullable=False),
            sa.Column("severity", sa.String(length=16), nullable=False),
            sa.Column("is_read", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_notifications_id"), "notifications", ["id"], unique=False)
        op.create_index(op.f("ix_notifications_severity"), "notifications", ["severity"], unique=False)
        op.create_index(op.f("ix_notifications_is_read"), "notifications", ["is_read"], unique=False)
        op.create_index(op.f("ix_notifications_created_at"), "notifications", ["created_at"], unique=False)

    if not has_table("system_logs"):
        op.create_table(
            "system_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("level", sa.String(length=16), nullable=False),
            sa.Column("source", sa.String(length=80), nullable=False),
            sa.Column("message", sa.String(length=1000), nullable=False),
            sa.Column("context", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_system_logs_id"), "system_logs", ["id"], unique=False)
        op.create_index(op.f("ix_system_logs_level"), "system_logs", ["level"], unique=False)
        op.create_index(op.f("ix_system_logs_source"), "system_logs", ["source"], unique=False)
        op.create_index(op.f("ix_system_logs_created_at"), "system_logs", ["created_at"], unique=False)


def downgrade() -> None:
    for table_name in ["system_logs", "notifications", "ai_model_metadata", "api_credentials", "users"]:
        if has_table(table_name):
            op.drop_table(table_name)

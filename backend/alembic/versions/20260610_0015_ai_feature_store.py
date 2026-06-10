"""ai feature store tables

Revision ID: 20260610_0015
Revises: 20260610_0014
Create Date: 2026-06-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260610_0015"
down_revision: str | None = "20260610_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not has_table("feature_sets"):
        op.create_table(
            "feature_sets",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("description", sa.String(length=500), nullable=False),
            sa.Column("features", sa.JSON(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )
        op.create_index(op.f("ix_feature_sets_id"), "feature_sets", ["id"], unique=False)
        op.create_index(op.f("ix_feature_sets_name"), "feature_sets", ["name"], unique=True)
        op.create_index(op.f("ix_feature_sets_status"), "feature_sets", ["status"], unique=False)
        op.create_index(op.f("ix_feature_sets_created_at"), "feature_sets", ["created_at"], unique=False)

    if not has_table("market_features"):
        op.create_table(
            "market_features",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("symbol_id", sa.Integer(), nullable=False),
            sa.Column("feature_set_id", sa.Integer(), nullable=False),
            sa.Column("timeframe", sa.String(length=8), nullable=False),
            sa.Column("candle_opened_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("values", sa.JSON(), nullable=False),
            sa.Column("source", sa.String(length=32), nullable=False),
            sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["feature_set_id"], ["feature_sets.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("symbol_id", "feature_set_id", "timeframe", "candle_opened_at", name="uq_market_feature_symbol_set_time"),
        )
        op.create_index(op.f("ix_market_features_id"), "market_features", ["id"], unique=False)
        op.create_index(op.f("ix_market_features_symbol_id"), "market_features", ["symbol_id"], unique=False)
        op.create_index(op.f("ix_market_features_feature_set_id"), "market_features", ["feature_set_id"], unique=False)
        op.create_index(op.f("ix_market_features_timeframe"), "market_features", ["timeframe"], unique=False)
        op.create_index(op.f("ix_market_features_candle_opened_at"), "market_features", ["candle_opened_at"], unique=False)
        op.create_index(op.f("ix_market_features_calculated_at"), "market_features", ["calculated_at"], unique=False)

    if not has_table("feature_calculation_logs"):
        op.create_table(
            "feature_calculation_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("symbol_id", sa.Integer(), nullable=True),
            sa.Column("feature_set_id", sa.Integer(), nullable=True),
            sa.Column("timeframe", sa.String(length=8), nullable=False),
            sa.Column("lookback", sa.Integer(), nullable=False),
            sa.Column("rows_calculated", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column("message", sa.String(length=500), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["feature_set_id"], ["feature_sets.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_feature_calculation_logs_id"), "feature_calculation_logs", ["id"], unique=False)
        op.create_index(op.f("ix_feature_calculation_logs_symbol_id"), "feature_calculation_logs", ["symbol_id"], unique=False)
        op.create_index(op.f("ix_feature_calculation_logs_feature_set_id"), "feature_calculation_logs", ["feature_set_id"], unique=False)
        op.create_index(op.f("ix_feature_calculation_logs_timeframe"), "feature_calculation_logs", ["timeframe"], unique=False)
        op.create_index(op.f("ix_feature_calculation_logs_status"), "feature_calculation_logs", ["status"], unique=False)
        op.create_index(op.f("ix_feature_calculation_logs_created_at"), "feature_calculation_logs", ["created_at"], unique=False)


def downgrade() -> None:
    for table_name, indexes in [
        (
            "feature_calculation_logs",
            [
                "ix_feature_calculation_logs_created_at",
                "ix_feature_calculation_logs_status",
                "ix_feature_calculation_logs_timeframe",
                "ix_feature_calculation_logs_feature_set_id",
                "ix_feature_calculation_logs_symbol_id",
                "ix_feature_calculation_logs_id",
            ],
        ),
        (
            "market_features",
            [
                "ix_market_features_calculated_at",
                "ix_market_features_candle_opened_at",
                "ix_market_features_timeframe",
                "ix_market_features_feature_set_id",
                "ix_market_features_symbol_id",
                "ix_market_features_id",
            ],
        ),
        ("feature_sets", ["ix_feature_sets_created_at", "ix_feature_sets_status", "ix_feature_sets_name", "ix_feature_sets_id"]),
    ]:
        if not has_table(table_name):
            continue
        existing_indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}
        for index_name in indexes:
            if index_name in existing_indexes:
                op.drop_index(index_name, table_name=table_name)
        op.drop_table(table_name)

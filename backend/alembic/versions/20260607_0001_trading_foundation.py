"""trading foundation tables

Revision ID: 20260607_0001
Revises:
Create Date: 2026-06-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260607_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "risk_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("max_risk_per_trade", sa.Float(), nullable=False),
        sa.Column("max_daily_loss", sa.Float(), nullable=False),
        sa.Column("max_open_trades", sa.Integer(), nullable=False),
        sa.Column("max_symbol_exposure", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_risk_settings_id"), "risk_settings", ["id"], unique=False)

    op.create_table(
        "strategies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("timeframe", sa.String(length=8), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_strategies_id"), "strategies", ["id"], unique=False)

    op.create_table(
        "symbols",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=24), nullable=False),
        sa.Column("base_asset", sa.String(length=16), nullable=False),
        sa.Column("quote_asset", sa.String(length=16), nullable=False),
        sa.Column("market", sa.String(length=24), nullable=False),
        sa.Column("exchange", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol"),
    )
    op.create_index(op.f("ix_symbols_id"), "symbols", ["id"], unique=False)
    op.create_index(op.f("ix_symbols_symbol"), "symbols", ["symbol"], unique=False)

    op.create_table(
        "market_candles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("symbol_id", sa.Integer(), nullable=False),
        sa.Column("timeframe", sa.String(length=8), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol_id", "timeframe", "opened_at", name="uq_market_candle_symbol_timeframe_opened"),
    )
    op.create_index(op.f("ix_market_candles_id"), "market_candles", ["id"], unique=False)
    op.create_index(op.f("ix_market_candles_opened_at"), "market_candles", ["opened_at"], unique=False)
    op.create_index(op.f("ix_market_candles_symbol_id"), "market_candles", ["symbol_id"], unique=False)
    op.create_index(op.f("ix_market_candles_timeframe"), "market_candles", ["timeframe"], unique=False)

    op.create_table(
        "signals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("symbol_id", sa.Integer(), nullable=False),
        sa.Column("strategy_id", sa.Integer(), nullable=True),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("timeframe", sa.String(length=8), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_signals_created_at"), "signals", ["created_at"], unique=False)
    op.create_index(op.f("ix_signals_direction"), "signals", ["direction"], unique=False)
    op.create_index(op.f("ix_signals_id"), "signals", ["id"], unique=False)
    op.create_index(op.f("ix_signals_symbol_id"), "signals", ["symbol_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_signals_symbol_id"), table_name="signals")
    op.drop_index(op.f("ix_signals_id"), table_name="signals")
    op.drop_index(op.f("ix_signals_direction"), table_name="signals")
    op.drop_index(op.f("ix_signals_created_at"), table_name="signals")
    op.drop_table("signals")
    op.drop_index(op.f("ix_market_candles_timeframe"), table_name="market_candles")
    op.drop_index(op.f("ix_market_candles_symbol_id"), table_name="market_candles")
    op.drop_index(op.f("ix_market_candles_opened_at"), table_name="market_candles")
    op.drop_index(op.f("ix_market_candles_id"), table_name="market_candles")
    op.drop_table("market_candles")
    op.drop_index(op.f("ix_symbols_symbol"), table_name="symbols")
    op.drop_index(op.f("ix_symbols_id"), table_name="symbols")
    op.drop_table("symbols")
    op.drop_index(op.f("ix_strategies_id"), table_name="strategies")
    op.drop_table("strategies")
    op.drop_index(op.f("ix_risk_settings_id"), table_name="risk_settings")
    op.drop_table("risk_settings")

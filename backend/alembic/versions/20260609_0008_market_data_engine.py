"""market data engine

Revision ID: 20260609_0008
Revises: 20260609_0007
Create Date: 2026-06-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260609_0008"
down_revision: str | None = "20260609_0007"
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
    if has_table("market_candles"):
        add_column_if_missing("market_candles", sa.Column("spread", sa.Float(), nullable=False, server_default="0"))

    if not has_table("market_ticks"):
        op.create_table(
            "market_ticks",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("symbol_id", sa.Integer(), nullable=False),
            sa.Column("exchange", sa.String(length=32), nullable=False, server_default="binance"),
            sa.Column("tick_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("bid", sa.Float(), nullable=True),
            sa.Column("ask", sa.Float(), nullable=True),
            sa.Column("price", sa.Float(), nullable=False),
            sa.Column("volume", sa.Float(), nullable=False, server_default="0"),
            sa.Column("spread", sa.Float(), nullable=False, server_default="0"),
            sa.Column("source", sa.String(length=32), nullable=False, server_default="import"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("symbol_id", "exchange", "tick_time", name="uq_market_tick_symbol_exchange_time"),
        )
        op.create_index(op.f("ix_market_ticks_id"), "market_ticks", ["id"], unique=False)
        op.create_index(op.f("ix_market_ticks_symbol_id"), "market_ticks", ["symbol_id"], unique=False)
        op.create_index(op.f("ix_market_ticks_tick_time"), "market_ticks", ["tick_time"], unique=False)

    if not has_table("market_order_books"):
        op.create_table(
            "market_order_books",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("symbol_id", sa.Integer(), nullable=False),
            sa.Column("exchange", sa.String(length=32), nullable=False, server_default="binance"),
            sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("bids", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("asks", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("best_bid", sa.Float(), nullable=True),
            sa.Column("best_ask", sa.Float(), nullable=True),
            sa.Column("spread", sa.Float(), nullable=False, server_default="0"),
            sa.Column("depth", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("source", sa.String(length=32), nullable=False, server_default="stream"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("symbol_id", "exchange", "captured_at", name="uq_order_book_symbol_exchange_time"),
        )
        op.create_index(op.f("ix_market_order_books_id"), "market_order_books", ["id"], unique=False)
        op.create_index(op.f("ix_market_order_books_symbol_id"), "market_order_books", ["symbol_id"], unique=False)
        op.create_index(op.f("ix_market_order_books_captured_at"), "market_order_books", ["captured_at"], unique=False)

    if not has_table("market_trades"):
        op.create_table(
            "market_trades",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("symbol_id", sa.Integer(), nullable=False),
            sa.Column("exchange", sa.String(length=32), nullable=False, server_default="binance"),
            sa.Column("trade_id", sa.String(length=80), nullable=False),
            sa.Column("traded_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("price", sa.Float(), nullable=False),
            sa.Column("quantity", sa.Float(), nullable=False),
            sa.Column("side", sa.String(length=12), nullable=False, server_default="unknown"),
            sa.Column("source", sa.String(length=32), nullable=False, server_default="stream"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("symbol_id", "exchange", "trade_id", name="uq_market_trade_symbol_exchange_trade"),
        )
        op.create_index(op.f("ix_market_trades_id"), "market_trades", ["id"], unique=False)
        op.create_index(op.f("ix_market_trades_symbol_id"), "market_trades", ["symbol_id"], unique=False)
        op.create_index(op.f("ix_market_trades_trade_id"), "market_trades", ["trade_id"], unique=False)
        op.create_index(op.f("ix_market_trades_traded_at"), "market_trades", ["traded_at"], unique=False)


def downgrade() -> None:
    for table_name in ["market_trades", "market_order_books", "market_ticks"]:
        if has_table(table_name):
            op.drop_table(table_name)

    if has_table("market_candles") and "spread" in columns("market_candles"):
        if op.get_bind().dialect.name == "sqlite":
            with op.batch_alter_table("market_candles") as batch_op:
                batch_op.drop_column("spread")
        else:
            op.drop_column("market_candles", "spread")

"""paper trading account and ledger

Revision ID: 20260610_0010
Revises: 20260609_0009
Create Date: 2026-06-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260610_0010"
down_revision: str | None = "20260609_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not has_table("paper_accounts"):
        op.create_table(
            "paper_accounts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("starting_balance", sa.Float(), nullable=False),
            sa.Column("cash_balance", sa.Float(), nullable=False),
            sa.Column("realized_pnl", sa.Float(), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("reset_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )
        op.create_index(op.f("ix_paper_accounts_id"), "paper_accounts", ["id"], unique=False)
        op.create_index(op.f("ix_paper_accounts_status"), "paper_accounts", ["status"], unique=False)
        op.create_index(op.f("ix_paper_accounts_created_at"), "paper_accounts", ["created_at"], unique=False)

    if not has_table("paper_trade_ledger"):
        op.create_table(
            "paper_trade_ledger",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("account_id", sa.Integer(), nullable=False),
            sa.Column("order_id", sa.Integer(), nullable=True),
            sa.Column("position_id", sa.Integer(), nullable=True),
            sa.Column("symbol_id", sa.Integer(), nullable=True),
            sa.Column("event_type", sa.String(length=32), nullable=False),
            sa.Column("side", sa.String(length=12), nullable=False),
            sa.Column("quantity", sa.Float(), nullable=False),
            sa.Column("price", sa.Float(), nullable=False),
            sa.Column("realized_pnl", sa.Float(), nullable=False),
            sa.Column("unrealized_pnl", sa.Float(), nullable=False),
            sa.Column("balance_after", sa.Float(), nullable=False),
            sa.Column("equity_after", sa.Float(), nullable=False),
            sa.Column("event_metadata", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["account_id"], ["paper_accounts.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["order_id"], ["paper_orders.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["position_id"], ["paper_positions.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_paper_trade_ledger_id"), "paper_trade_ledger", ["id"], unique=False)
        op.create_index(op.f("ix_paper_trade_ledger_account_id"), "paper_trade_ledger", ["account_id"], unique=False)
        op.create_index(op.f("ix_paper_trade_ledger_order_id"), "paper_trade_ledger", ["order_id"], unique=False)
        op.create_index(op.f("ix_paper_trade_ledger_position_id"), "paper_trade_ledger", ["position_id"], unique=False)
        op.create_index(op.f("ix_paper_trade_ledger_symbol_id"), "paper_trade_ledger", ["symbol_id"], unique=False)
        op.create_index(op.f("ix_paper_trade_ledger_event_type"), "paper_trade_ledger", ["event_type"], unique=False)
        op.create_index(op.f("ix_paper_trade_ledger_created_at"), "paper_trade_ledger", ["created_at"], unique=False)


def downgrade() -> None:
    if has_table("paper_trade_ledger"):
        for index_name in [
            "ix_paper_trade_ledger_created_at",
            "ix_paper_trade_ledger_event_type",
            "ix_paper_trade_ledger_symbol_id",
            "ix_paper_trade_ledger_position_id",
            "ix_paper_trade_ledger_order_id",
            "ix_paper_trade_ledger_account_id",
            "ix_paper_trade_ledger_id",
        ]:
            existing_indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("paper_trade_ledger")}
            if index_name in existing_indexes:
                op.drop_index(index_name, table_name="paper_trade_ledger")
        op.drop_table("paper_trade_ledger")

    if has_table("paper_accounts"):
        for index_name in ["ix_paper_accounts_created_at", "ix_paper_accounts_status", "ix_paper_accounts_id"]:
            existing_indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("paper_accounts")}
            if index_name in existing_indexes:
                op.drop_index(index_name, table_name="paper_accounts")
        op.drop_table("paper_accounts")

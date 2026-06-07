"""paper trading orders and positions

Revision ID: 20260607_0004
Revises: 20260607_0003
Create Date: 2026-06-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260607_0004"
down_revision: str | None = "20260607_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = inspector.get_table_names()

    if "paper_orders" not in tables:
        op.create_table(
            "paper_orders",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("symbol_id", sa.Integer(), nullable=False),
            sa.Column("signal_id", sa.Integer(), nullable=True),
            sa.Column("ai_analysis_id", sa.Integer(), nullable=True),
            sa.Column("side", sa.String(length=12), nullable=False),
            sa.Column("order_type", sa.String(length=16), nullable=False),
            sa.Column("quantity", sa.Float(), nullable=False),
            sa.Column("requested_price", sa.Float(), nullable=False),
            sa.Column("fill_price", sa.Float(), nullable=True),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column("risk_status", sa.String(length=16), nullable=False),
            sa.Column("risk_message", sa.String(length=500), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("filled_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["ai_analysis_id"], ["ai_analyses.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_paper_orders_ai_analysis_id"), "paper_orders", ["ai_analysis_id"], unique=False)
        op.create_index(op.f("ix_paper_orders_created_at"), "paper_orders", ["created_at"], unique=False)
        op.create_index(op.f("ix_paper_orders_id"), "paper_orders", ["id"], unique=False)
        op.create_index(op.f("ix_paper_orders_side"), "paper_orders", ["side"], unique=False)
        op.create_index(op.f("ix_paper_orders_signal_id"), "paper_orders", ["signal_id"], unique=False)
        op.create_index(op.f("ix_paper_orders_status"), "paper_orders", ["status"], unique=False)
        op.create_index(op.f("ix_paper_orders_symbol_id"), "paper_orders", ["symbol_id"], unique=False)

    if "paper_positions" not in tables:
        op.create_table(
            "paper_positions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("symbol_id", sa.Integer(), nullable=False),
            sa.Column("side", sa.String(length=12), nullable=False),
            sa.Column("quantity", sa.Float(), nullable=False),
            sa.Column("avg_entry_price", sa.Float(), nullable=False),
            sa.Column("mark_price", sa.Float(), nullable=False),
            sa.Column("unrealized_pnl", sa.Float(), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("symbol_id", "side", "status", name="uq_paper_position_symbol_side_status"),
        )
        op.create_index(op.f("ix_paper_positions_created_at"), "paper_positions", ["created_at"], unique=False)
        op.create_index(op.f("ix_paper_positions_id"), "paper_positions", ["id"], unique=False)
        op.create_index(op.f("ix_paper_positions_side"), "paper_positions", ["side"], unique=False)
        op.create_index(op.f("ix_paper_positions_status"), "paper_positions", ["status"], unique=False)
        op.create_index(op.f("ix_paper_positions_symbol_id"), "paper_positions", ["symbol_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_paper_positions_symbol_id"), table_name="paper_positions")
    op.drop_index(op.f("ix_paper_positions_status"), table_name="paper_positions")
    op.drop_index(op.f("ix_paper_positions_side"), table_name="paper_positions")
    op.drop_index(op.f("ix_paper_positions_id"), table_name="paper_positions")
    op.drop_index(op.f("ix_paper_positions_created_at"), table_name="paper_positions")
    op.drop_table("paper_positions")
    op.drop_index(op.f("ix_paper_orders_symbol_id"), table_name="paper_orders")
    op.drop_index(op.f("ix_paper_orders_status"), table_name="paper_orders")
    op.drop_index(op.f("ix_paper_orders_signal_id"), table_name="paper_orders")
    op.drop_index(op.f("ix_paper_orders_side"), table_name="paper_orders")
    op.drop_index(op.f("ix_paper_orders_id"), table_name="paper_orders")
    op.drop_index(op.f("ix_paper_orders_created_at"), table_name="paper_orders")
    op.drop_index(op.f("ix_paper_orders_ai_analysis_id"), table_name="paper_orders")
    op.drop_table("paper_orders")

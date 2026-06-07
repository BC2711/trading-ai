"""backtest run history

Revision ID: 20260607_0002
Revises: 20260607_0001
Create Date: 2026-06-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260607_0002"
down_revision: str | None = "20260607_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "backtest_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("symbol_id", sa.Integer(), nullable=False),
        sa.Column("strategy_id", sa.Integer(), nullable=True),
        sa.Column("timeframe", sa.String(length=8), nullable=False),
        sa.Column("initial_balance", sa.Float(), nullable=False),
        sa.Column("ending_balance", sa.Float(), nullable=False),
        sa.Column("total_return", sa.Float(), nullable=False),
        sa.Column("win_rate", sa.Float(), nullable=False),
        sa.Column("max_drawdown", sa.Float(), nullable=False),
        sa.Column("trades_count", sa.Integer(), nullable=False),
        sa.Column("winning_trades", sa.Integer(), nullable=False),
        sa.Column("losing_trades", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_backtest_runs_created_at"), "backtest_runs", ["created_at"], unique=False)
    op.create_index(op.f("ix_backtest_runs_id"), "backtest_runs", ["id"], unique=False)
    op.create_index(op.f("ix_backtest_runs_symbol_id"), "backtest_runs", ["symbol_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_backtest_runs_symbol_id"), table_name="backtest_runs")
    op.drop_index(op.f("ix_backtest_runs_id"), table_name="backtest_runs")
    op.drop_index(op.f("ix_backtest_runs_created_at"), table_name="backtest_runs")
    op.drop_table("backtest_runs")

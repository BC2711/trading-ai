"""walk forward backtest runs

Revision ID: 20260610_0014
Revises: 20260610_0013
Create Date: 2026-06-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260610_0014"
down_revision: str | None = "20260610_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if has_table("walk_forward_runs"):
        return
    op.create_table(
        "walk_forward_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("symbol_id", sa.Integer(), nullable=False),
        sa.Column("strategy_id", sa.Integer(), nullable=True),
        sa.Column("timeframe", sa.String(length=8), nullable=False),
        sa.Column("training_period", sa.Integer(), nullable=False),
        sa.Column("validation_period", sa.Integer(), nullable=False),
        sa.Column("test_period", sa.Integer(), nullable=False),
        sa.Column("rolling_windows", sa.Integer(), nullable=False),
        sa.Column("initial_balance", sa.Float(), nullable=False),
        sa.Column("optimization_results", sa.JSON(), nullable=False),
        sa.Column("out_of_sample_results", sa.JSON(), nullable=False),
        sa.Column("window_metrics", sa.JSON(), nullable=False),
        sa.Column("aggregated_result", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("warning", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["symbol_id"], ["symbols.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_walk_forward_runs_id"), "walk_forward_runs", ["id"], unique=False)
    op.create_index(op.f("ix_walk_forward_runs_symbol_id"), "walk_forward_runs", ["symbol_id"], unique=False)
    op.create_index(op.f("ix_walk_forward_runs_created_at"), "walk_forward_runs", ["created_at"], unique=False)
    op.create_index(op.f("ix_walk_forward_runs_status"), "walk_forward_runs", ["status"], unique=False)


def downgrade() -> None:
    if not has_table("walk_forward_runs"):
        return
    existing_indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("walk_forward_runs")}
    for index_name in [
        "ix_walk_forward_runs_status",
        "ix_walk_forward_runs_created_at",
        "ix_walk_forward_runs_symbol_id",
        "ix_walk_forward_runs_id",
    ]:
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name="walk_forward_runs")
    op.drop_table("walk_forward_runs")

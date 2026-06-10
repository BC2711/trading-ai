"""monte carlo risk simulation runs

Revision ID: 20260610_0012
Revises: 20260610_0011
Create Date: 2026-06-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260610_0012"
down_revision: str | None = "20260610_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if has_table("monte_carlo_runs"):
        return
    op.create_table(
        "monte_carlo_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("starting_balance", sa.Float(), nullable=False),
        sa.Column("win_rate", sa.Float(), nullable=False),
        sa.Column("average_win", sa.Float(), nullable=False),
        sa.Column("average_loss", sa.Float(), nullable=False),
        sa.Column("number_of_trades", sa.Integer(), nullable=False),
        sa.Column("number_of_simulations", sa.Integer(), nullable=False),
        sa.Column("risk_per_trade", sa.Float(), nullable=False),
        sa.Column("probability_of_ruin", sa.Float(), nullable=False),
        sa.Column("expected_drawdown", sa.Float(), nullable=False),
        sa.Column("maximum_drawdown", sa.Float(), nullable=False),
        sa.Column("best_case", sa.Float(), nullable=False),
        sa.Column("worst_case", sa.Float(), nullable=False),
        sa.Column("median_case", sa.Float(), nullable=False),
        sa.Column("confidence_intervals", sa.JSON(), nullable=False),
        sa.Column("ending_equity_distribution", sa.JSON(), nullable=False),
        sa.Column("risk_recommendation", sa.String(length=800), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_monte_carlo_runs_id"), "monte_carlo_runs", ["id"], unique=False)
    op.create_index(op.f("ix_monte_carlo_runs_created_at"), "monte_carlo_runs", ["created_at"], unique=False)


def downgrade() -> None:
    if not has_table("monte_carlo_runs"):
        return
    for index_name in ["ix_monte_carlo_runs_created_at", "ix_monte_carlo_runs_id"]:
        existing_indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("monte_carlo_runs")}
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name="monte_carlo_runs")
    op.drop_table("monte_carlo_runs")

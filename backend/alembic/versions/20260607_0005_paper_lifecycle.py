"""paper order lifecycle fields

Revision ID: 20260607_0005
Revises: 20260607_0004
Create Date: 2026-06-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260607_0005"
down_revision: str | None = "20260607_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("paper_positions")}
    constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("paper_positions")}

    if "uq_paper_position_symbol_side_status" in constraints:
        op.drop_constraint("uq_paper_position_symbol_side_status", "paper_positions", type_="unique")

    if "realized_pnl" not in columns:
        op.add_column("paper_positions", sa.Column("realized_pnl", sa.Float(), nullable=False, server_default="0"))
        op.alter_column("paper_positions", "realized_pnl", server_default=None)

    if "closed_at" not in columns:
        op.add_column("paper_positions", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("paper_positions")}
    constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("paper_positions")}

    if "closed_at" in columns:
        op.drop_column("paper_positions", "closed_at")

    if "realized_pnl" in columns:
        op.drop_column("paper_positions", "realized_pnl")

    if "uq_paper_position_symbol_side_status" not in constraints:
        op.create_unique_constraint(
            "uq_paper_position_symbol_side_status",
            "paper_positions",
            ["symbol_id", "side", "status"],
        )

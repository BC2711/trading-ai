"""ai analysis history

Revision ID: 20260607_0003
Revises: 20260607_0002
Create Date: 2026-06-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260607_0003"
down_revision: str | None = "20260607_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "ai_analyses" in inspector.get_table_names():
        return

    op.create_table(
        "ai_analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("signal_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(length=48), nullable=False),
        sa.Column("symbol", sa.String(length=24), nullable=False),
        sa.Column("timeframe", sa.String(length=8), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("explanation", sa.String(length=1200), nullable=False),
        sa.Column("reasoning", sa.JSON(), nullable=False),
        sa.Column("risk_notes", sa.JSON(), nullable=False),
        sa.Column("suggested_action", sa.String(length=500), nullable=False),
        sa.Column("indicators", sa.JSON(), nullable=False),
        sa.Column("backtest_summary", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_analyses_created_at"), "ai_analyses", ["created_at"], unique=False)
    op.create_index(op.f("ix_ai_analyses_direction"), "ai_analyses", ["direction"], unique=False)
    op.create_index(op.f("ix_ai_analyses_id"), "ai_analyses", ["id"], unique=False)
    op.create_index(op.f("ix_ai_analyses_signal_id"), "ai_analyses", ["signal_id"], unique=False)
    op.create_index(op.f("ix_ai_analyses_symbol"), "ai_analyses", ["symbol"], unique=False)
    op.create_index(op.f("ix_ai_analyses_timeframe"), "ai_analyses", ["timeframe"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_analyses_timeframe"), table_name="ai_analyses")
    op.drop_index(op.f("ix_ai_analyses_symbol"), table_name="ai_analyses")
    op.drop_index(op.f("ix_ai_analyses_signal_id"), table_name="ai_analyses")
    op.drop_index(op.f("ix_ai_analyses_id"), table_name="ai_analyses")
    op.drop_index(op.f("ix_ai_analyses_direction"), table_name="ai_analyses")
    op.drop_index(op.f("ix_ai_analyses_created_at"), table_name="ai_analyses")
    op.drop_table("ai_analyses")

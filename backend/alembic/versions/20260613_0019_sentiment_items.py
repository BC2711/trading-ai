"""sentiment provider items

Revision ID: 20260613_0019
Revises: 20260613_0018
Create Date: 2026-06-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260613_0019"
down_revision: str | None = "20260613_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if has_table("sentiment_items"):
        return

    op.create_table(
        "sentiment_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=48), nullable=False),
        sa.Column("source", sa.String(length=160), nullable=False),
        sa.Column("symbol", sa.String(length=24), nullable=False),
        sa.Column("related_asset", sa.String(length=24), nullable=False),
        sa.Column("headline", sa.String(length=1000), nullable=False),
        sa.Column("sentiment_score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "symbol", "headline", "observed_at", name="uq_sentiment_provider_symbol_headline_time"),
    )
    op.create_index(op.f("ix_sentiment_items_id"), "sentiment_items", ["id"], unique=False)
    op.create_index(op.f("ix_sentiment_items_provider"), "sentiment_items", ["provider"], unique=False)
    op.create_index(op.f("ix_sentiment_items_source"), "sentiment_items", ["source"], unique=False)
    op.create_index(op.f("ix_sentiment_items_symbol"), "sentiment_items", ["symbol"], unique=False)
    op.create_index(op.f("ix_sentiment_items_related_asset"), "sentiment_items", ["related_asset"], unique=False)
    op.create_index(op.f("ix_sentiment_items_sentiment_score"), "sentiment_items", ["sentiment_score"], unique=False)
    op.create_index(op.f("ix_sentiment_items_observed_at"), "sentiment_items", ["observed_at"], unique=False)
    op.create_index(op.f("ix_sentiment_items_created_at"), "sentiment_items", ["created_at"], unique=False)


def downgrade() -> None:
    if not has_table("sentiment_items"):
        return
    op.drop_index(op.f("ix_sentiment_items_created_at"), table_name="sentiment_items")
    op.drop_index(op.f("ix_sentiment_items_observed_at"), table_name="sentiment_items")
    op.drop_index(op.f("ix_sentiment_items_sentiment_score"), table_name="sentiment_items")
    op.drop_index(op.f("ix_sentiment_items_related_asset"), table_name="sentiment_items")
    op.drop_index(op.f("ix_sentiment_items_symbol"), table_name="sentiment_items")
    op.drop_index(op.f("ix_sentiment_items_source"), table_name="sentiment_items")
    op.drop_index(op.f("ix_sentiment_items_provider"), table_name="sentiment_items")
    op.drop_index(op.f("ix_sentiment_items_id"), table_name="sentiment_items")
    op.drop_table("sentiment_items")


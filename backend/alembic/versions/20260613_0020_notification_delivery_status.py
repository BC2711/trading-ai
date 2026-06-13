"""notification delivery status

Revision ID: 20260613_0020
Revises: 20260613_0019
Create Date: 2026-06-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260613_0020"
down_revision: str | None = "20260613_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def has_column(table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    if not has_table("notifications"):
        return
    if not has_column("notifications", "delivery_status"):
        op.add_column("notifications", sa.Column("delivery_status", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    if not has_column("notifications", "delivery_attempted_at"):
        op.add_column("notifications", sa.Column("delivery_attempted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    if not has_table("notifications"):
        return
    if has_column("notifications", "delivery_attempted_at"):
        op.drop_column("notifications", "delivery_attempted_at")
    if has_column("notifications", "delivery_status"):
        op.drop_column("notifications", "delivery_status")

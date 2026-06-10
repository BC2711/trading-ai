"""advanced risk limits

Revision ID: 20260610_0011
Revises: 20260610_0010
Create Date: 2026-06-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260610_0011"
down_revision: str | None = "20260610_0010"
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
    if not has_table("risk_settings"):
        return
    add_column_if_missing("risk_settings", sa.Column("max_weekly_loss", sa.Float(), nullable=False, server_default="0.08"))
    add_column_if_missing("risk_settings", sa.Column("max_drawdown", sa.Float(), nullable=False, server_default="0.15"))
    add_column_if_missing("risk_settings", sa.Column("max_leverage", sa.Float(), nullable=False, server_default="1.0"))


def downgrade() -> None:
    if not has_table("risk_settings"):
        return
    for column_name in ["max_leverage", "max_drawdown", "max_weekly_loss"]:
        if column_name not in columns("risk_settings"):
            continue
        if op.get_bind().dialect.name == "sqlite":
            with op.batch_alter_table("risk_settings") as batch_op:
                batch_op.drop_column(column_name)
        else:
            op.drop_column("risk_settings", column_name)

"""ai training pipeline metadata

Revision ID: 20260609_0009
Revises: 20260609_0008
Create Date: 2026-06-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260609_0009"
down_revision: str | None = "20260609_0008"
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
    if not has_table("ai_model_metadata"):
        return

    add_column_if_missing("ai_model_metadata", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    add_column_if_missing("ai_model_metadata", sa.Column("parent_model_id", sa.Integer(), nullable=True))
    add_column_if_missing("ai_model_metadata", sa.Column("feature_names", sa.JSON(), nullable=False, server_default="[]"))
    add_column_if_missing("ai_model_metadata", sa.Column("training_params", sa.JSON(), nullable=False, server_default="{}"))
    add_column_if_missing("ai_model_metadata", sa.Column("target", sa.String(length=80), nullable=False, server_default="next_close_direction"))
    add_column_if_missing("ai_model_metadata", sa.Column("deployed", sa.Boolean(), nullable=False, server_default=sa.false()))

    existing_indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("ai_model_metadata")}
    if "ix_ai_model_metadata_parent_model_id" not in existing_indexes:
        op.create_index(op.f("ix_ai_model_metadata_parent_model_id"), "ai_model_metadata", ["parent_model_id"], unique=False)
    if "ix_ai_model_metadata_deployed" not in existing_indexes:
        op.create_index(op.f("ix_ai_model_metadata_deployed"), "ai_model_metadata", ["deployed"], unique=False)


def downgrade() -> None:
    if not has_table("ai_model_metadata"):
        return

    for index_name in ["ix_ai_model_metadata_deployed", "ix_ai_model_metadata_parent_model_id"]:
        existing_indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("ai_model_metadata")}
        if index_name in existing_indexes:
            op.drop_index(index_name, table_name="ai_model_metadata")

    for column_name in ["deployed", "target", "training_params", "feature_names", "parent_model_id", "version"]:
        if column_name not in columns("ai_model_metadata"):
            continue
        if op.get_bind().dialect.name == "sqlite":
            with op.batch_alter_table("ai_model_metadata") as batch_op:
                batch_op.drop_column(column_name)
        else:
            op.drop_column("ai_model_metadata", column_name)

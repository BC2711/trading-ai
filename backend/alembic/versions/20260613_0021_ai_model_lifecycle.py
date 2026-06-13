"""ai model lifecycle metadata

Revision ID: 20260613_0021
Revises: 20260613_0020
Create Date: 2026-06-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260613_0021"
down_revision: str | None = "20260613_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def has_column(table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    if not has_table("ai_model_metadata"):
        return

    columns = [
        ("champion", sa.Column("champion", sa.Boolean(), nullable=False, server_default=sa.text("false"))),
        ("approval_status", sa.Column("approval_status", sa.String(length=24), nullable=False, server_default="pending")),
        ("approved_at", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True)),
        ("approved_by", sa.Column("approved_by", sa.String(length=255), nullable=True)),
        ("challenger_of_id", sa.Column("challenger_of_id", sa.Integer(), nullable=True)),
        ("lifecycle_metadata", sa.Column("lifecycle_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'"))),
        ("model_drift", sa.Column("model_drift", sa.JSON(), nullable=False, server_default=sa.text("'{}'"))),
        ("feature_drift", sa.Column("feature_drift", sa.JSON(), nullable=False, server_default=sa.text("'{}'"))),
        ("last_prediction_at", sa.Column("last_prediction_at", sa.DateTime(timezone=True), nullable=True)),
        ("last_retrained_at", sa.Column("last_retrained_at", sa.DateTime(timezone=True), nullable=True)),
        ("retrain_interval_hours", sa.Column("retrain_interval_hours", sa.Integer(), nullable=True)),
        ("next_retrain_at", sa.Column("next_retrain_at", sa.DateTime(timezone=True), nullable=True)),
    ]
    for column_name, column in columns:
        if not has_column("ai_model_metadata", column_name):
            op.add_column("ai_model_metadata", column)

    for column_name in ("champion", "approval_status", "challenger_of_id", "next_retrain_at"):
        index_name = op.f(f"ix_ai_model_metadata_{column_name}")
        op.create_index(index_name, "ai_model_metadata", [column_name], unique=False)


def downgrade() -> None:
    if not has_table("ai_model_metadata"):
        return
    for column_name in ("next_retrain_at", "challenger_of_id", "approval_status", "champion"):
        op.drop_index(op.f(f"ix_ai_model_metadata_{column_name}"), table_name="ai_model_metadata")
    for column_name in (
        "next_retrain_at",
        "retrain_interval_hours",
        "last_retrained_at",
        "last_prediction_at",
        "feature_drift",
        "model_drift",
        "lifecycle_metadata",
        "challenger_of_id",
        "approved_by",
        "approved_at",
        "approval_status",
        "champion",
    ):
        if has_column("ai_model_metadata", column_name):
            op.drop_column("ai_model_metadata", column_name)

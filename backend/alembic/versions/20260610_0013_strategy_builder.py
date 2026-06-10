"""strategy builder rule tables

Revision ID: 20260610_0013
Revises: 20260610_0012
Create Date: 2026-06-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260610_0013"
down_revision: str | None = "20260610_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not has_table("strategy_rules"):
        op.create_table(
            "strategy_rules",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("strategy_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=160), nullable=False),
            sa.Column("logic_operator", sa.String(length=8), nullable=False),
            sa.Column("priority", sa.Integer(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_strategy_rules_id"), "strategy_rules", ["id"], unique=False)
        op.create_index(op.f("ix_strategy_rules_strategy_id"), "strategy_rules", ["strategy_id"], unique=False)
        op.create_index(op.f("ix_strategy_rules_created_at"), "strategy_rules", ["created_at"], unique=False)

    if not has_table("strategy_conditions"):
        op.create_table(
            "strategy_conditions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("rule_id", sa.Integer(), nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("indicator", sa.String(length=40), nullable=False),
            sa.Column("operator", sa.String(length=16), nullable=False),
            sa.Column("value", sa.Float(), nullable=True),
            sa.Column("period", sa.Integer(), nullable=True),
            sa.Column("compare_indicator", sa.String(length=40), nullable=True),
            sa.Column("compare_period", sa.Integer(), nullable=True),
            sa.Column("parameters", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["rule_id"], ["strategy_rules.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_strategy_conditions_id"), "strategy_conditions", ["id"], unique=False)
        op.create_index(op.f("ix_strategy_conditions_rule_id"), "strategy_conditions", ["rule_id"], unique=False)
        op.create_index(op.f("ix_strategy_conditions_indicator"), "strategy_conditions", ["indicator"], unique=False)
        op.create_index(op.f("ix_strategy_conditions_created_at"), "strategy_conditions", ["created_at"], unique=False)

    if not has_table("strategy_actions"):
        op.create_table(
            "strategy_actions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("rule_id", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(length=24), nullable=False),
            sa.Column("parameters", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["rule_id"], ["strategy_rules.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_strategy_actions_id"), "strategy_actions", ["id"], unique=False)
        op.create_index(op.f("ix_strategy_actions_rule_id"), "strategy_actions", ["rule_id"], unique=False)
        op.create_index(op.f("ix_strategy_actions_action"), "strategy_actions", ["action"], unique=False)
        op.create_index(op.f("ix_strategy_actions_created_at"), "strategy_actions", ["created_at"], unique=False)


def downgrade() -> None:
    for table_name, indexes in [
        ("strategy_actions", ["ix_strategy_actions_created_at", "ix_strategy_actions_action", "ix_strategy_actions_rule_id", "ix_strategy_actions_id"]),
        (
            "strategy_conditions",
            ["ix_strategy_conditions_created_at", "ix_strategy_conditions_indicator", "ix_strategy_conditions_rule_id", "ix_strategy_conditions_id"],
        ),
        ("strategy_rules", ["ix_strategy_rules_created_at", "ix_strategy_rules_strategy_id", "ix_strategy_rules_id"]),
    ]:
        if not has_table(table_name):
            continue
        existing_indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}
        for index_name in indexes:
            if index_name in existing_indexes:
                op.drop_index(index_name, table_name=table_name)
        op.drop_table(table_name)

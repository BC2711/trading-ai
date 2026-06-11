"""rbac roles and permissions

Revision ID: 20260611_0016
Revises: 20260610_0015
Create Date: 2026-06-11
"""

from collections.abc import Sequence
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision: str = "20260611_0016"
down_revision: str | None = "20260610_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


RBAC_PERMISSIONS = [
    ("view_dashboard", "View dashboard, portfolio, market, and read-only workspace data."),
    ("manage_users", "Create, update, deactivate, and delete users."),
    ("manage_api_keys", "Manage broker and exchange API credentials."),
    ("execute_trades", "Create, cancel, and manage trade orders and positions."),
    ("view_orders", "View orders, positions, and portfolio trading records."),
    ("manage_strategies", "Create and update strategies, signals, and strategy rules."),
    ("run_backtests", "Run and inspect backtests and walk-forward tests."),
    ("train_models", "Train, retrain, deploy, and manage AI models."),
    ("manage_risk", "View and update risk controls."),
    ("view_logs", "View logs, audit events, and notifications."),
]

DEFAULT_ROLES = [
    ("Super Admin", "super_admin", "Full system owner with automatic access to every permission."),
    ("Admin", "admin", "Operational administrator for users, credentials, risk, models, and trading controls."),
    ("Trader", "trader", "Trading operator with execution, strategy, backtest, and risk access."),
    ("Analyst", "analyst", "Research user for analysis, strategy testing, model training, and logs."),
    ("Viewer", "viewer", "Read-only user for dashboards, orders, logs, and audit visibility."),
]

DEFAULT_ROLE_PERMISSIONS = {
    "super_admin": [name for name, _description in RBAC_PERMISSIONS],
    "admin": [name for name, _description in RBAC_PERMISSIONS],
    "trader": ["view_dashboard", "execute_trades", "view_orders", "manage_strategies", "run_backtests", "manage_risk"],
    "analyst": ["view_dashboard", "view_orders", "manage_strategies", "run_backtests", "train_models", "view_logs"],
    "viewer": ["view_dashboard", "view_orders", "view_logs"],
}


def has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    if not has_table("roles"):
        op.create_table(
            "roles",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=80), nullable=False),
            sa.Column("slug", sa.String(length=80), nullable=False),
            sa.Column("description", sa.String(length=500), nullable=False),
            sa.Column("is_system", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
            sa.UniqueConstraint("slug"),
        )
        op.create_index(op.f("ix_roles_id"), "roles", ["id"], unique=False)
        op.create_index(op.f("ix_roles_name"), "roles", ["name"], unique=True)
        op.create_index(op.f("ix_roles_slug"), "roles", ["slug"], unique=True)
        op.create_index(op.f("ix_roles_is_system"), "roles", ["is_system"], unique=False)
        op.create_index(op.f("ix_roles_created_at"), "roles", ["created_at"], unique=False)

    if not has_table("permissions"):
        op.create_table(
            "permissions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=80), nullable=False),
            sa.Column("description", sa.String(length=500), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )
        op.create_index(op.f("ix_permissions_id"), "permissions", ["id"], unique=False)
        op.create_index(op.f("ix_permissions_name"), "permissions", ["name"], unique=True)
        op.create_index(op.f("ix_permissions_created_at"), "permissions", ["created_at"], unique=False)

    if not has_table("user_roles"):
        op.create_table(
            "user_roles",
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("role_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("user_id", "role_id"),
            sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
        )
        op.create_index(op.f("ix_user_roles_created_at"), "user_roles", ["created_at"], unique=False)

    if not has_table("role_permissions"):
        op.create_table(
            "role_permissions",
            sa.Column("role_id", sa.Integer(), nullable=False),
            sa.Column("permission_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("role_id", "permission_id"),
            sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),
        )
        op.create_index(op.f("ix_role_permissions_created_at"), "role_permissions", ["created_at"], unique=False)

    seed_defaults()


def seed_defaults() -> None:
    connection = op.get_bind()
    now = datetime.now(timezone.utc)
    permission_ids: dict[str, int] = {}
    for name, description in RBAC_PERMISSIONS:
        existing = connection.execute(sa.text("SELECT id FROM permissions WHERE name = :name"), {"name": name}).scalar()
        if existing is None:
            connection.execute(
                sa.text("INSERT INTO permissions (name, description, created_at) VALUES (:name, :description, :created_at)"),
                {"name": name, "description": description, "created_at": now},
            )
            existing = connection.execute(sa.text("SELECT id FROM permissions WHERE name = :name"), {"name": name}).scalar()
        permission_ids[name] = int(existing)

    role_ids: dict[str, int] = {}
    for name, slug, description in DEFAULT_ROLES:
        existing = connection.execute(sa.text("SELECT id FROM roles WHERE slug = :slug"), {"slug": slug}).scalar()
        if existing is None:
            connection.execute(
                sa.text(
                    "INSERT INTO roles (name, slug, description, is_system, created_at, updated_at) "
                    "VALUES (:name, :slug, :description, :is_system, :created_at, :updated_at)"
                ),
                {
                    "name": name,
                    "slug": slug,
                    "description": description,
                    "is_system": True,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            existing = connection.execute(sa.text("SELECT id FROM roles WHERE slug = :slug"), {"slug": slug}).scalar()
        role_ids[slug] = int(existing)

    for slug, names in DEFAULT_ROLE_PERMISSIONS.items():
        role_id = role_ids[slug]
        for permission_name in names:
            permission_id = permission_ids[permission_name]
            exists = connection.execute(
                sa.text("SELECT 1 FROM role_permissions WHERE role_id = :role_id AND permission_id = :permission_id"),
                {"role_id": role_id, "permission_id": permission_id},
            ).scalar()
            if exists is None:
                connection.execute(
                    sa.text(
                        "INSERT INTO role_permissions (role_id, permission_id, created_at) "
                        "VALUES (:role_id, :permission_id, :created_at)"
                    ),
                    {"role_id": role_id, "permission_id": permission_id, "created_at": now},
                )

    users = connection.execute(sa.text("SELECT id, role FROM users")).fetchall()
    for user_id, legacy_role in users:
        exists = connection.execute(sa.text("SELECT 1 FROM user_roles WHERE user_id = :user_id"), {"user_id": user_id}).scalar()
        if exists is not None:
            continue
        role_id = role_ids.get(str(legacy_role).lower(), role_ids["trader"])
        connection.execute(
            sa.text("INSERT INTO user_roles (user_id, role_id, created_at) VALUES (:user_id, :role_id, :created_at)"),
            {"user_id": user_id, "role_id": role_id, "created_at": now},
        )


def downgrade() -> None:
    for table_name, indexes in [
        ("role_permissions", ["ix_role_permissions_created_at"]),
        ("user_roles", ["ix_user_roles_created_at"]),
        ("permissions", ["ix_permissions_created_at", "ix_permissions_name", "ix_permissions_id"]),
        ("roles", ["ix_roles_created_at", "ix_roles_is_system", "ix_roles_slug", "ix_roles_name", "ix_roles_id"]),
    ]:
        if not has_table(table_name):
            continue
        existing_indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}
        for index_name in indexes:
            if index_name in existing_indexes:
                op.drop_index(index_name, table_name=table_name)
        op.drop_table(table_name)

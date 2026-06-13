import re

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.security import encrypt_secret, hash_password, verify_password, decode_refresh_token
from app.models import AIModelMetadata, ApiCredential, Notification, Permission, Role, RolePermission, SystemLog, User, UserRole
from app.schemas.trading import ApiCredentialCreate, ApiCredentialUpdate, NotificationCreate, RoleCreate, RoleUpdate, UserCreate, UserUpdate
from app.services.audit import record_event


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

DEFAULT_ROLE_PERMISSIONS = {
    "super_admin": [name for name, _description in RBAC_PERMISSIONS],
    "admin": [
        "view_dashboard",
        "manage_users",
        "manage_api_keys",
        "execute_trades",
        "view_orders",
        "manage_strategies",
        "run_backtests",
        "train_models",
        "manage_risk",
        "view_logs",
    ],
    "trader": [
        "view_dashboard",
        "execute_trades",
        "view_orders",
        "manage_strategies",
        "run_backtests",
        "manage_risk",
    ],
    "analyst": [
        "view_dashboard",
        "view_orders",
        "manage_strategies",
        "run_backtests",
        "train_models",
        "view_logs",
    ],
    "viewer": [
        "view_dashboard",
        "view_orders",
        "view_logs",
    ],
}

DEFAULT_ROLES = [
    ("Super Admin", "super_admin", "Full system owner with automatic access to every permission."),
    ("Admin", "admin", "Operational administrator for users, credentials, risk, models, and trading controls."),
    ("Trader", "trader", "Trading operator with execution, strategy, backtest, and risk access."),
    ("Analyst", "analyst", "Research user for analysis, strategy testing, model training, and logs."),
    ("Viewer", "viewer", "Read-only user for dashboards, orders, logs, and audit visibility."),
]

PERMISSION_ALIASES = {
    "view_dashboard": [
        "dashboard:view",
        "symbols:view",
        "market-data:view",
        "market-data:stream",
        "portfolio:view",
        "signals:view",
        "ai-analyses:view",
        "ai-models:view",
        "notifications:view",
    ],
    "manage_users": ["users:manage", "rbac:manage"],
    "manage_api_keys": ["api-credentials:manage"],
    "execute_trades": ["orders:create", "orders:manage", "positions:manage"],
    "view_orders": ["orders:view", "positions:view", "portfolio:view"],
    "manage_strategies": [
        "strategies:view",
        "strategies:update",
        "strategies:manage",
        "signals:generate",
        "ai-analyses:create",
    ],
    "run_backtests": ["backtests:view", "backtests:run"],
    "train_models": ["ai-models:view", "ai-models:manage", "ai-provider:manage"],
    "manage_risk": ["risk-settings:view", "risk-settings:update", "risk-settings:manage"],
    "view_logs": ["logs:view", "audit:view", "notifications:view", "notifications:manage"],
}

ADMIN_PERMISSIONS = [
    "users:manage",
    "api-credentials:manage",
    "symbols:manage",
    "market-data:import",
    "market-data:repair",
    "market-data:sync",
    "market-data:stream",
    "strategies:manage",
    "risk-settings:manage",
    "ai-provider:manage",
    "ai-models:manage",
    "orders:manage",
    "positions:manage",
    "logs:view",
    "notifications:manage",
]

TRADER_PERMISSIONS = [
    "dashboard:view",
    "symbols:view",
    "market-data:view",
    "portfolio:view",
    "signals:view",
    "signals:generate",
    "ai-analyses:view",
    "ai-analyses:create",
    "orders:view",
    "orders:create",
    "positions:view",
    "backtests:view",
    "backtests:run",
    "strategies:view",
    "strategies:update",
    "risk-settings:view",
    "risk-settings:update",
    "ai-models:view",
    "audit:view",
    "notifications:view",
    "logs:view",
]


def role_slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def permissions_for_role(role: str) -> list[str]:
    """Legacy fallback used before the RBAC seed has run."""
    slug = role_slug(role)
    rbac_permissions = set(DEFAULT_ROLE_PERMISSIONS.get(slug, DEFAULT_ROLE_PERMISSIONS["trader"]))
    if slug == "super_admin":
        rbac_permissions = {name for name, _description in RBAC_PERMISSIONS}
    return expand_permissions(rbac_permissions)


def expand_permissions(permissions: set[str]) -> list[str]:
    expanded = set(permissions)
    for permission in list(permissions):
        expanded.update(PERMISSION_ALIASES.get(permission, []))
    return sorted(expanded)


def ensure_rbac_defaults(db: Session) -> None:
    permission_by_name: dict[str, Permission] = {}
    for name, description in RBAC_PERMISSIONS:
        permission = db.scalar(select(Permission).where(Permission.name == name))
        if permission is None:
            permission = Permission(name=name, description=description)
            db.add(permission)
            db.flush()
        else:
            permission.description = description
        permission_by_name[name] = permission

    role_by_slug: dict[str, Role] = {}
    for name, slug, description in DEFAULT_ROLES:
        role = db.scalar(select(Role).where(Role.slug == slug))
        if role is None:
            role = Role(name=name, slug=slug, description=description, is_system=True)
            db.add(role)
            db.flush()
        else:
            role.name = name
            role.description = description
            role.is_system = True
        role_by_slug[slug] = role

    for slug, permission_names in DEFAULT_ROLE_PERMISSIONS.items():
        role = role_by_slug[slug]
        existing = {assignment.permission_id for assignment in role.permission_assignments}
        for permission_name in permission_names:
            permission = permission_by_name[permission_name]
            if permission.id not in existing:
                db.add(RolePermission(role_id=role.id, permission_id=permission.id))

    for user in db.scalars(select(User)).all():
        if user.role_assignments:
            continue
        slug = role_slug(user.role)
        default_role = role_by_slug.get(slug) or role_by_slug["trader"]
        db.add(UserRole(user_id=user.id, role_id=default_role.id))

    db.commit()


def permissions_for_user(db: Session, user: User) -> list[str]:
    ensure_rbac_defaults(db)
    roles = roles_for_user(db, user.id)
    if any(role.slug == "super_admin" for role in roles):
        permissions = set(expand_permissions({permission.name for permission in list_permissions(db)}))
        permissions.update(TRADER_PERMISSIONS)
        permissions.update(ADMIN_PERMISSIONS)
        return sorted(permissions)

    granted = {
        assignment.permission_ref.name
        for role in roles
        for assignment in role.permission_assignments
    }
    if not granted:
        granted.update(DEFAULT_ROLE_PERMISSIONS.get(role_slug(user.role), DEFAULT_ROLE_PERMISSIONS["trader"]))
    expanded = set(expand_permissions(granted))
    if any(role.slug == "admin" for role in roles) or role_slug(user.role) == "admin":
        expanded.update(TRADER_PERMISSIONS)
        expanded.update(ADMIN_PERMISSIONS)
    return sorted(expanded)


def roles_for_user(db: Session, user_id: int) -> list[Role]:
    ensure_rbac_defaults(db)
    statement = (
        select(Role)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
        .order_by(Role.name)
    )
    return list(db.scalars(statement).all())


def user_has_role(db: Session, user: User, role_names: set[str]) -> bool:
    wanted = {role_slug(role) for role in role_names}
    return role_slug(user.role) in wanted or any(role.slug in wanted for role in roles_for_user(db, user.id))


def list_roles(db: Session) -> list[Role]:
    ensure_rbac_defaults(db)
    return list(db.scalars(select(Role).order_by(Role.name)).all())


def list_permissions(db: Session) -> list[Permission]:
    ensure_rbac_defaults(db)
    return list(db.scalars(select(Permission).order_by(Permission.name)).all())


def create_role(db: Session, payload: RoleCreate) -> Role:
    ensure_rbac_defaults(db)
    name = payload.name.strip()
    slug = role_slug(name)
    if db.scalar(select(Role).where(Role.slug == slug)):
        raise ValueError("Role already exists")
    role = Role(name=name, slug=slug, description=payload.description, is_system=False)
    db.add(role)
    db.flush()
    set_role_permissions(db, role, payload.permission_ids)
    db.commit()
    db.refresh(role)
    return role


def update_role(db: Session, role_id: int, payload: RoleUpdate) -> Role | None:
    ensure_rbac_defaults(db)
    role = db.get(Role, role_id)
    if role is None:
        return None
    changes = payload.model_dump(exclude_unset=True)
    if "name" in changes and changes["name"] is not None:
        role.name = changes["name"].strip()
        if not role.is_system:
            role.slug = role_slug(role.name)
    if "description" in changes and changes["description"] is not None:
        role.description = changes["description"]
    if "permission_ids" in changes and changes["permission_ids"] is not None:
        set_role_permissions(db, role, changes["permission_ids"])
    db.commit()
    db.refresh(role)
    return role


def delete_role(db: Session, role_id: int) -> bool:
    ensure_rbac_defaults(db)
    role = db.get(Role, role_id)
    if role is None:
        return False
    if role.is_system:
        raise ValueError("System roles cannot be deleted")
    db.delete(role)
    db.commit()
    return True


def set_role_permissions(db: Session, role: Role, permission_ids: list[int]) -> None:
    valid_permissions = set(db.scalars(select(Permission.id).where(Permission.id.in_(permission_ids))).all())
    if len(valid_permissions) != len(set(permission_ids)):
        raise ValueError("One or more permissions were not found")
    db.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
    for permission_id in sorted(valid_permissions):
        db.add(RolePermission(role_id=role.id, permission_id=permission_id))


def assign_roles_to_user(db: Session, user_id: int, role_ids: list[int]) -> User | None:
    ensure_rbac_defaults(db)
    user = db.get(User, user_id)
    if user is None:
        return None
    valid_role_ids = set(db.scalars(select(Role.id).where(Role.id.in_(role_ids))).all())
    if len(valid_role_ids) != len(set(role_ids)):
        raise ValueError("One or more roles were not found")
    db.execute(delete(UserRole).where(UserRole.user_id == user.id))
    for role_id in sorted(valid_role_ids):
        db.add(UserRole(user_id=user.id, role_id=role_id))
    primary_role = db.get(Role, min(valid_role_ids)) if valid_role_ids else None
    if primary_role is not None:
        user.role = primary_role.slug
    db.commit()
    db.refresh(user)
    return user

def revoke_refresh_token(db: Session, token: str) -> bool:
    """
    In production, this should write to a 'RevokedToken' table or Redis blacklist.
    """
    payload = decode_refresh_token(token)
    if not payload:
        return False
    
    # Placeholder for actual persistence logic
    # db.add(RevokedToken(jti=payload["jti"]))
    # db.commit()
    
    return True


def register_user(db: Session, payload: UserCreate) -> User:
    email = payload.email.lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise ValueError("Email is already registered")

    first_user = db.scalar(select(User.id).limit(1)) is None
    ensure_rbac_defaults(db)
    role = "super_admin" if first_user else "trader"
    user = User(
        email=email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    default_role = db.scalar(select(Role).where(Role.slug == role)) or db.scalar(select(Role).where(Role.slug == "trader"))
    if default_role is not None:
        db.add(UserRole(user_id=user.id, role_id=default_role.id))
    db.commit()
    db.refresh(user)
    record_event(
        db,
        event_type="user.registered",
        entity_type="user",
        entity_id=user.id,
        message=f"Registered user {user.email}.",
        metadata={"role": user.role},
        commit=True,
    )
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None or not user.is_active or not verify_password(password, user.hashed_password):
        return None
    return user


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.desc())).all())


def update_user(db: Session, user_id: int, payload: UserUpdate) -> User | None:
    user = db.get(User, user_id)
    if user is None:
        return None
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> bool:
    user = db.get(User, user_id)
    if user is None:
        return False
    db.delete(user)
    db.commit()
    return True


def list_credentials(db: Session) -> list[ApiCredential]:
    return list(db.scalars(select(ApiCredential).order_by(ApiCredential.created_at.desc())).all())


def create_credential(db: Session, payload: ApiCredentialCreate) -> ApiCredential:
    credential = ApiCredential(
        exchange=payload.exchange.lower(),
        api_key=payload.api_key,
        encrypted_api_secret=encrypt_secret(payload.api_secret),
        mode=payload.mode,
        is_active=payload.is_active,
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return credential


def update_credential(db: Session, credential_id: int, payload: ApiCredentialUpdate) -> ApiCredential | None:
    credential = db.get(ApiCredential, credential_id)
    if credential is None:
        return None
    changes = payload.model_dump(exclude_unset=True)
    if "api_secret" in changes and changes["api_secret"]:
        credential.encrypted_api_secret = encrypt_secret(changes.pop("api_secret"))
    for field, value in changes.items():
        if value is not None:
            setattr(credential, field, value.lower() if field in {"exchange", "mode"} else value)
    db.commit()
    db.refresh(credential)
    return credential


def delete_credential(db: Session, credential_id: int) -> bool:
    credential = db.get(ApiCredential, credential_id)
    if credential is None:
        return False
    db.delete(credential)
    db.commit()
    return True


def list_notifications(db: Session, unread_only: bool = False) -> list[Notification]:
    statement = select(Notification)
    if unread_only:
        statement = statement.where(Notification.is_read.is_(False))
    return list(db.scalars(statement.order_by(Notification.created_at.desc())).all())


def create_notification(db: Session, payload: NotificationCreate) -> Notification:
    notification = Notification(title=payload.title, message=payload.message, severity=payload.severity)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def mark_notification_read(db: Session, notification_id: int) -> Notification | None:
    notification = db.get(Notification, notification_id)
    if notification is None:
        return None
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


def list_system_logs(db: Session, limit: int = 100, level: str | None = None) -> list[SystemLog]:
    statement = select(SystemLog)
    if level:
        statement = statement.where(SystemLog.level == level)
    return list(db.scalars(statement.order_by(SystemLog.created_at.desc()).limit(limit)).all())


def write_log(db: Session, level: str, source: str, message: str, context: dict | None = None) -> SystemLog:
    log = SystemLog(level=level, source=source, message=message, context=context or {})
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def list_ai_models(db: Session) -> list[AIModelMetadata]:
    return list(db.scalars(select(AIModelMetadata).order_by(AIModelMetadata.created_at.desc())).all())

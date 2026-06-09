from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import encrypt_secret, hash_password, verify_password
from app.models import AIModelMetadata, ApiCredential, Notification, SystemLog, User
from app.schemas.trading import ApiCredentialCreate, ApiCredentialUpdate, NotificationCreate, UserCreate, UserUpdate
from app.services.audit import record_event


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


def permissions_for_role(role: str) -> list[str]:
    return sorted(set(TRADER_PERMISSIONS + (ADMIN_PERMISSIONS if role == "admin" else [])))


def register_user(db: Session, payload: UserCreate) -> User:
    email = payload.email.lower()
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise ValueError("Email is already registered")

    first_user = db.scalar(select(User.id).limit(1)) is None
    role = "admin" if first_user else "trader"
    user = User(
        email=email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=role,
        is_active=True,
    )
    db.add(user)
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

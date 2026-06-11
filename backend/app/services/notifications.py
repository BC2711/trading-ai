from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Notification
from app.schemas.notifications import (
    NotificationChannelRead,
    NotificationEventRead,
    NotificationMarkReadRequest,
    NotificationMarkReadResponse,
    NotificationSettingsRead,
    NotificationSettingsUpdate,
)
from app.schemas.trading import NotificationCreate, NotificationRead
from app.services.admin import create_notification


SUPPORTED_CHANNELS = [
    {"key": "in_app", "label": "In-app", "placeholder": False},
    {"key": "email", "label": "Email", "placeholder": True},
    {"key": "telegram", "label": "Telegram", "placeholder": True},
    {"key": "whatsapp", "label": "WhatsApp", "placeholder": True},
    {"key": "discord", "label": "Discord", "placeholder": True},
]

SUPPORTED_EVENTS = [
    {"key": "trade_executed", "label": "Trade executed", "category": "trade"},
    {"key": "trade_rejected", "label": "Trade rejected", "category": "trade"},
    {"key": "stop_loss_hit", "label": "Stop loss hit", "category": "trade"},
    {"key": "take_profit_hit", "label": "Take profit hit", "category": "trade"},
    {"key": "ai_signal_generated", "label": "AI signal generated", "category": "ai"},
    {"key": "daily_loss_limit_reached", "label": "Daily loss limit reached", "category": "risk"},
    {"key": "drawdown_warning", "label": "Drawdown warning", "category": "risk"},
    {"key": "model_training_completed", "label": "Model training completed", "category": "ai"},
    {"key": "backtest_completed", "label": "Backtest completed", "category": "system"},
    {"key": "broker_disconnected", "label": "Broker disconnected", "category": "system"},
]

_SETTINGS = {
    "in_app_enabled": True,
    "email_enabled": False,
    "telegram_enabled": False,
    "whatsapp_enabled": False,
    "discord_enabled": False,
    "trade_alerts": True,
    "risk_alerts": True,
    "ai_alerts": True,
    "system_alerts": True,
    "updated_at": datetime.now(timezone.utc),
}


def get_notification_settings() -> NotificationSettingsRead:
    return _settings_read()


def update_notification_settings(payload: NotificationSettingsUpdate) -> NotificationSettingsRead:
    changes = payload.model_dump(exclude_unset=True)
    if changes:
        _SETTINGS.update({key: value for key, value in changes.items() if value is not None})
        _SETTINGS["updated_at"] = datetime.now(timezone.utc)
    return _settings_read()


def mark_notifications_read(db: Session, payload: NotificationMarkReadRequest) -> NotificationMarkReadResponse:
    if payload.all:
        notifications = list(db.scalars(select(Notification).where(Notification.is_read.is_(False))).all())
    elif payload.notification_ids:
        notifications = list(
            db.scalars(select(Notification).where(Notification.id.in_(payload.notification_ids))).all()
        )
    else:
        notifications = []

    updated_count = 0
    for notification in notifications:
        if not notification.is_read:
            notification.is_read = True
            updated_count += 1

    if notifications:
        db.commit()
        for notification in notifications:
            db.refresh(notification)

    return NotificationMarkReadResponse(
        updated_count=updated_count,
        notifications=[NotificationRead.model_validate(notification) for notification in notifications],
    )


def dispatch_notification(
    db: Session,
    event_key: str,
    title: str,
    message: str,
    severity: str = "info",
) -> Notification | None:
    if not _event_enabled(event_key) or not _SETTINGS["in_app_enabled"]:
        return None
    return create_notification(db, NotificationCreate(title=title, message=message, severity=severity))


def _settings_read() -> NotificationSettingsRead:
    return NotificationSettingsRead(
        **_SETTINGS,
        channels=[
            NotificationChannelRead(
                **channel,
                enabled=bool(_SETTINGS[f"{channel['key']}_enabled"]),
            )
            for channel in SUPPORTED_CHANNELS
        ],
        events=[
            NotificationEventRead(
                **event,
                enabled=_category_enabled(event["category"]),
            )
            for event in SUPPORTED_EVENTS
        ],
    )


def _event_enabled(event_key: str) -> bool:
    event = next((item for item in SUPPORTED_EVENTS if item["key"] == event_key), None)
    return bool(event and _category_enabled(event["category"]))


def _category_enabled(category: str) -> bool:
    return bool(_SETTINGS.get(f"{category}_alerts", False))

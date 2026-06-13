import logging
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
from app.services.notification_providers import (
    DeliveryResult,
    DiscordNotificationProvider,
    EmailNotificationProvider,
    NotificationPayload,
    NotificationProvider,
    TelegramNotificationProvider,
    WhatsAppNotificationProvider,
)

logger = logging.getLogger(__name__)

SUPPORTED_CHANNELS = [
    {"key": "in_app", "label": "In-app", "placeholder": False},
    {"key": "email", "label": "Email", "placeholder": False},
    {"key": "telegram", "label": "Telegram", "placeholder": False},
    {"key": "whatsapp", "label": "WhatsApp", "placeholder": False},
    {"key": "discord", "label": "Discord", "placeholder": False},
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

CHANNEL_SETTING_KEYS = {
    "in_app": "in_app_enabled",
    "email": "email_enabled",
    "telegram": "telegram_enabled",
    "whatsapp": "whatsapp_enabled",
    "discord": "discord_enabled",
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
    if not _event_enabled(event_key):
        return None
    return create_and_dispatch_notification(
        db,
        NotificationCreate(title=title, message=message, severity=severity),
        event_key=event_key,
    )


def create_and_dispatch_notification(
    db: Session,
    payload: NotificationCreate,
    event_key: str = "manual_notification",
) -> Notification:
    notification = create_notification(db, payload)
    delivery_status = dispatch_to_channels(NotificationPayload(title=payload.title, message=payload.message, severity=payload.severity))
    notification.delivery_status = delivery_status
    notification.delivery_attempted_at = datetime.now(timezone.utc)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def dispatch_to_channels(payload: NotificationPayload) -> dict[str, dict[str, str]]:
    results: dict[str, DeliveryResult] = {
        "in_app": DeliveryResult.delivered("in_app", "In-app")
        if _SETTINGS["in_app_enabled"]
        else DeliveryResult.skipped("in_app", "In-app", "Channel is disabled.")
    }

    for provider in configured_providers():
        if not _SETTINGS[CHANNEL_SETTING_KEYS[provider.channel]]:
            results[provider.channel] = DeliveryResult.skipped(provider.channel, provider.label, "Channel is disabled.")
            continue
        try:
            result = provider.send(payload)
        except Exception as exc:
            result = DeliveryResult.failed(provider.channel, provider.label, str(exc))
        results[provider.channel] = result
        if result.status == "failed":
            logger.error("Notification delivery failed for %s: %s", provider.channel, result.detail)
        elif result.status == "not_configured":
            logger.warning("Notification delivery skipped for %s: provider is not configured.", provider.channel)

    return {channel: result.to_record() for channel, result in results.items()}


def configured_providers() -> list[NotificationProvider]:
    return [
        EmailNotificationProvider(),
        TelegramNotificationProvider(),
        WhatsAppNotificationProvider(),
        DiscordNotificationProvider(),
    ]


def _settings_read() -> NotificationSettingsRead:
    providers = {provider.channel: provider for provider in configured_providers()}
    return NotificationSettingsRead(
        **_SETTINGS,
        channels=[
            NotificationChannelRead(
                **channel,
                enabled=bool(_SETTINGS[f"{channel['key']}_enabled"]),
                configured=True if channel["key"] == "in_app" else providers[channel["key"]].is_configured,
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

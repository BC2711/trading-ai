from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.trading import NotificationRead


class NotificationChannelRead(BaseModel):
    key: str
    label: str
    enabled: bool
    placeholder: bool = False


class NotificationEventRead(BaseModel):
    key: str
    label: str
    category: str
    enabled: bool


class NotificationSettingsRead(BaseModel):
    in_app_enabled: bool = True
    email_enabled: bool = False
    telegram_enabled: bool = False
    whatsapp_enabled: bool = False
    discord_enabled: bool = False
    trade_alerts: bool = True
    risk_alerts: bool = True
    ai_alerts: bool = True
    system_alerts: bool = True
    channels: list[NotificationChannelRead] = Field(default_factory=list)
    events: list[NotificationEventRead] = Field(default_factory=list)
    updated_at: datetime


class NotificationSettingsUpdate(BaseModel):
    in_app_enabled: bool | None = None
    email_enabled: bool | None = None
    telegram_enabled: bool | None = None
    whatsapp_enabled: bool | None = None
    discord_enabled: bool | None = None
    trade_alerts: bool | None = None
    risk_alerts: bool | None = None
    ai_alerts: bool | None = None
    system_alerts: bool | None = None


class NotificationMarkReadRequest(BaseModel):
    notification_ids: list[int] = Field(default_factory=list)
    all: bool = False


class NotificationMarkReadResponse(BaseModel):
    updated_count: int
    notifications: list[NotificationRead]

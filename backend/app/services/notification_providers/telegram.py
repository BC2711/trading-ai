from __future__ import annotations

from app.core.config import Settings, settings
from app.services.notification_providers.interfaces import DeliveryResult, NotificationPayload, NotificationProvider


class TelegramNotificationProvider(NotificationProvider):
    channel = "telegram"
    label = "Telegram"

    def __init__(self, config: Settings = settings) -> None:
        self.config = config

    @property
    def is_configured(self) -> bool:
        return bool(self.config.telegram_bot_token and self.config.telegram_chat_id)

    def send(self, payload: NotificationPayload) -> DeliveryResult:
        if not self.is_configured:
            return DeliveryResult.not_configured(self.channel, self.label)

        import httpx

        url = f"{self.config.telegram_api_base_url.rstrip('/')}/bot{self.config.telegram_bot_token}/sendMessage"
        try:
            response = httpx.post(
                url,
                json={
                    "chat_id": self.config.telegram_chat_id,
                    "text": f"{payload.title}\n\n{payload.message}\nSeverity: {payload.severity}",
                    "disable_web_page_preview": True,
                },
                timeout=self.config.notification_request_timeout_seconds,
            )
            response.raise_for_status()
            return DeliveryResult.delivered(self.channel, self.label)
        except Exception as exc:
            return DeliveryResult.failed(self.channel, self.label, str(exc))

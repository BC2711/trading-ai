from __future__ import annotations

from app.core.config import Settings, settings
from app.services.notification_providers.interfaces import DeliveryResult, NotificationPayload, NotificationProvider


class DiscordNotificationProvider(NotificationProvider):
    channel = "discord"
    label = "Discord"

    def __init__(self, config: Settings = settings) -> None:
        self.config = config

    @property
    def is_configured(self) -> bool:
        return bool(self.config.discord_webhook_url)

    def send(self, payload: NotificationPayload) -> DeliveryResult:
        if not self.is_configured:
            return DeliveryResult.not_configured(self.channel, self.label)

        import httpx

        try:
            response = httpx.post(
                self.config.discord_webhook_url or "",
                json={
                    "content": None,
                    "embeds": [
                        {
                            "title": payload.title,
                            "description": payload.message,
                            "fields": [{"name": "Severity", "value": payload.severity, "inline": True}],
                        }
                    ],
                },
                timeout=self.config.notification_request_timeout_seconds,
            )
            response.raise_for_status()
            return DeliveryResult.delivered(self.channel, self.label)
        except Exception as exc:
            return DeliveryResult.failed(self.channel, self.label, str(exc))

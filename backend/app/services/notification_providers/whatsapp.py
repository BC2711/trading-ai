from __future__ import annotations

from app.core.config import Settings, settings
from app.services.notification_providers.interfaces import DeliveryResult, NotificationPayload, NotificationProvider


class WhatsAppNotificationProvider(NotificationProvider):
    channel = "whatsapp"
    label = "WhatsApp"

    def __init__(self, config: Settings = settings) -> None:
        self.config = config

    @property
    def is_configured(self) -> bool:
        return bool(self.config.whatsapp_access_token and self.config.whatsapp_phone_number_id and self.config.whatsapp_to_number)

    def send(self, payload: NotificationPayload) -> DeliveryResult:
        if not self.is_configured:
            return DeliveryResult.not_configured(self.channel, self.label)

        import httpx

        url = f"{self.config.whatsapp_api_base_url.rstrip('/')}/{self.config.whatsapp_phone_number_id}/messages"
        try:
            response = httpx.post(
                url,
                headers={"Authorization": f"Bearer {self.config.whatsapp_access_token}"},
                json={
                    "messaging_product": "whatsapp",
                    "to": self.config.whatsapp_to_number,
                    "type": "text",
                    "text": {"preview_url": False, "body": f"{payload.title}\n\n{payload.message}\nSeverity: {payload.severity}"},
                },
                timeout=self.config.notification_request_timeout_seconds,
            )
            response.raise_for_status()
            return DeliveryResult.delivered(self.channel, self.label)
        except Exception as exc:
            return DeliveryResult.failed(self.channel, self.label, str(exc))

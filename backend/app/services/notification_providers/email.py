from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.core.config import Settings, settings
from app.services.notification_providers.interfaces import DeliveryResult, NotificationPayload, NotificationProvider


class EmailNotificationProvider(NotificationProvider):
    channel = "email"
    label = "Email"

    def __init__(self, config: Settings = settings) -> None:
        self.config = config

    @property
    def is_configured(self) -> bool:
        return bool(self.config.notification_email_smtp_host and self.config.notification_email_from and self.config.notification_email_to)

    def send(self, payload: NotificationPayload) -> DeliveryResult:
        if not self.is_configured:
            return DeliveryResult.not_configured(self.channel, self.label)

        message = EmailMessage()
        message["Subject"] = payload.title
        message["From"] = self.config.notification_email_from or ""
        message["To"] = ", ".join(self.config.notification_email_to)
        message.set_content(f"{payload.title}\n\n{payload.message}\n\nSeverity: {payload.severity}")

        try:
            with smtplib.SMTP(self.config.notification_email_smtp_host or "", self.config.notification_email_smtp_port, timeout=self.config.notification_request_timeout_seconds) as smtp:
                if self.config.notification_email_use_tls:
                    smtp.starttls()
                if self.config.notification_email_username:
                    smtp.login(self.config.notification_email_username, self.config.notification_email_password or "")
                smtp.send_message(message)
            return DeliveryResult.delivered(self.channel, self.label)
        except Exception as exc:
            return DeliveryResult.failed(self.channel, self.label, str(exc))

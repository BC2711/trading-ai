from __future__ import annotations

import logging

from app.services.notification_providers import DeliveryResult, NotificationPayload
from app.services import notifications


class FailingEmailProvider:
    channel = "email"
    label = "Email"
    is_configured = True

    def send(self, payload: NotificationPayload) -> DeliveryResult:
        return DeliveryResult.failed(self.channel, self.label, "SMTP rejected the message.")


def test_dispatch_to_channels_logs_failed_delivery(monkeypatch, caplog) -> None:
    original_email_enabled = notifications._SETTINGS["email_enabled"]
    notifications._SETTINGS["email_enabled"] = True
    monkeypatch.setattr(notifications, "configured_providers", lambda: [FailingEmailProvider()])

    try:
        with caplog.at_level(logging.ERROR):
            delivery_status = notifications.dispatch_to_channels(
                NotificationPayload(title="Risk alert", message="Daily loss limit reached.", severity="warning")
            )
    finally:
        notifications._SETTINGS["email_enabled"] = original_email_enabled

    assert delivery_status["email"]["status"] == "failed"
    assert "SMTP rejected the message." in delivery_status["email"]["detail"]
    assert "Notification delivery failed for email" in caplog.text

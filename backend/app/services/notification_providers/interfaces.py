from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class NotificationPayload:
    title: str
    message: str
    severity: str = "info"


@dataclass(frozen=True)
class DeliveryResult:
    channel: str
    status: str
    provider: str
    timestamp: datetime
    detail: str | None = None

    @classmethod
    def delivered(cls, channel: str, provider: str, detail: str | None = None) -> "DeliveryResult":
        return cls(channel=channel, status="delivered", provider=provider, timestamp=datetime.now(timezone.utc), detail=detail)

    @classmethod
    def failed(cls, channel: str, provider: str, detail: str) -> "DeliveryResult":
        return cls(channel=channel, status="failed", provider=provider, timestamp=datetime.now(timezone.utc), detail=detail)

    @classmethod
    def skipped(cls, channel: str, provider: str, detail: str) -> "DeliveryResult":
        return cls(channel=channel, status="skipped", provider=provider, timestamp=datetime.now(timezone.utc), detail=detail)

    @classmethod
    def not_configured(cls, channel: str, provider: str) -> "DeliveryResult":
        return cls(channel=channel, status="not_configured", provider=provider, timestamp=datetime.now(timezone.utc), detail="Provider is missing required environment configuration.")

    def to_record(self) -> dict[str, str]:
        record = {
            "channel": self.channel,
            "status": self.status,
            "provider": self.provider,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.detail:
            record["detail"] = self.detail
        return record


class NotificationProvider:
    channel: str
    label: str

    @property
    def is_configured(self) -> bool:
        raise NotImplementedError

    def send(self, payload: NotificationPayload) -> DeliveryResult:
        raise NotImplementedError

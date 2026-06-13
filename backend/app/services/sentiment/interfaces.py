from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class ProviderSentimentItem:
    provider: str
    symbol: str
    headline: str
    source: str
    observed_at: datetime
    related_asset: str
    sentiment_score: float
    confidence: float = 0.5


class SentimentProvider(Protocol):
    name: str

    @property
    def is_configured(self) -> bool:
        ...

    def fetch(self, symbols: list[str]) -> list[ProviderSentimentItem]:
        ...

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services.sentiment.interfaces import ProviderSentimentItem
from app.services.sentiment.providers.utils import asset_from_symbol
from app.services.sentiment.scoring import score_text


class FallbackSentimentProvider:
    name = "fallback"

    @property
    def is_configured(self) -> bool:
        return True

    def fetch(self, symbols: list[str]) -> list[ProviderSentimentItem]:
        now = datetime.now(timezone.utc).replace(microsecond=0)
        items: list[ProviderSentimentItem] = []
        templates = [
            ("News API Fallback", "{asset} institutional inflows improve as traders watch resistance"),
            ("CryptoPanic Fallback", "{asset} demand improves after network upgrade"),
            ("Reddit Fallback", "Reddit traders debate {asset} accumulation near support"),
            ("X/Twitter Fallback", "X chatter turns bullish on {asset} breakout but warns of liquidations"),
        ]
        for index, symbol in enumerate(symbols):
            asset = asset_from_symbol(symbol)
            for offset, (source, template) in enumerate(templates):
                headline = template.format(asset=asset)
                items.append(
                    ProviderSentimentItem(
                        provider=self.name,
                        symbol=symbol,
                        headline=headline,
                        source=source,
                        observed_at=now - timedelta(minutes=index * 17 + offset * 5),
                        related_asset=asset,
                        sentiment_score=score_text(headline),
                        confidence=0.35,
                    )
                )
        return items

from __future__ import annotations

from app.core.config import Settings, settings
from app.services.sentiment.interfaces import ProviderSentimentItem
from app.services.sentiment.providers.utils import asset_from_symbol, first_text, parse_datetime
from app.services.sentiment.scoring import score_text


class CryptoPanicSentimentProvider:
    name = "cryptopanic"

    def __init__(self, config: Settings = settings) -> None:
        self.config = config

    @property
    def is_configured(self) -> bool:
        return bool(self.config.cryptopanic_api_key)

    def fetch(self, symbols: list[str]) -> list[ProviderSentimentItem]:
        import httpx

        items: list[ProviderSentimentItem] = []
        with httpx.Client(timeout=self.config.sentiment_request_timeout_seconds) as client:
            for symbol in symbols:
                asset = asset_from_symbol(symbol)
                response = client.get(
                    self.config.cryptopanic_base_url,
                    params={
                        "auth_token": self.config.cryptopanic_api_key,
                        "currencies": asset,
                        "kind": "news",
                        "public": "true",
                    },
                )
                response.raise_for_status()
                for post in response.json().get("results", []):
                    headline = first_text(post.get("title"))
                    if not headline:
                        continue
                    votes = post.get("votes") or {}
                    confidence = 0.62 + min(0.25, sum(float(votes.get(key) or 0) for key in ("positive", "negative", "important")) / 100)
                    source = post.get("domain") or (post.get("source") or {}).get("title") or "CryptoPanic"
                    items.append(
                        ProviderSentimentItem(
                            provider=self.name,
                            symbol=symbol,
                            headline=headline,
                            source=str(source),
                            observed_at=parse_datetime(post.get("published_at")),
                            related_asset=asset,
                            sentiment_score=score_text(headline),
                            confidence=confidence,
                        )
                    )
        return items

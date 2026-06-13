from __future__ import annotations

from app.core.config import Settings, settings
from app.services.sentiment.interfaces import ProviderSentimentItem
from app.services.sentiment.providers.utils import asset_from_symbol, first_text, parse_datetime
from app.services.sentiment.scoring import score_text


class XSentimentProvider:
    name = "x"

    def __init__(self, config: Settings = settings) -> None:
        self.config = config

    @property
    def is_configured(self) -> bool:
        return bool(self.config.x_bearer_token)

    def fetch(self, symbols: list[str]) -> list[ProviderSentimentItem]:
        import httpx

        items: list[ProviderSentimentItem] = []
        headers = {"Authorization": f"Bearer {self.config.x_bearer_token}"}
        with httpx.Client(timeout=self.config.sentiment_request_timeout_seconds, headers=headers) as client:
            for symbol in symbols:
                asset = asset_from_symbol(symbol)
                response = client.get(
                    self.config.x_recent_search_url,
                    params={
                        "query": f"({asset} OR {symbol}) lang:en -is:retweet",
                        "max_results": max(10, min(100, self.config.sentiment_items_per_provider)),
                        "tweet.fields": "created_at,public_metrics,lang",
                    },
                )
                response.raise_for_status()
                for post in response.json().get("data", []):
                    headline = first_text(post.get("text"))
                    if not headline:
                        continue
                    metrics = post.get("public_metrics") or {}
                    engagement = sum(float(metrics.get(key) or 0) for key in ("like_count", "reply_count", "retweet_count", "quote_count"))
                    items.append(
                        ProviderSentimentItem(
                            provider=self.name,
                            symbol=symbol,
                            headline=headline,
                            source="X/Twitter",
                            observed_at=parse_datetime(post.get("created_at")),
                            related_asset=asset,
                            sentiment_score=score_text(headline),
                            confidence=0.58 + min(0.3, engagement / 5000),
                        )
                    )
        return items

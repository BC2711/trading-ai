from __future__ import annotations

from app.core.config import Settings, settings
from app.services.sentiment.interfaces import ProviderSentimentItem
from app.services.sentiment.providers.utils import asset_from_symbol, first_text, parse_datetime
from app.services.sentiment.scoring import score_text


class NewsApiSentimentProvider:
    name = "newsapi"

    def __init__(self, config: Settings = settings) -> None:
        self.config = config

    @property
    def is_configured(self) -> bool:
        return bool(self.config.news_api_key)

    def fetch(self, symbols: list[str]) -> list[ProviderSentimentItem]:
        import httpx

        items: list[ProviderSentimentItem] = []
        with httpx.Client(timeout=self.config.sentiment_request_timeout_seconds) as client:
            for symbol in symbols:
                asset = asset_from_symbol(symbol)
                response = client.get(
                    self.config.news_api_base_url,
                    headers={"X-Api-Key": self.config.news_api_key or ""},
                    params={
                        "q": f"({asset} OR {symbol}) AND (crypto OR market OR trading)",
                        "language": "en",
                        "sortBy": "publishedAt",
                        "pageSize": self.config.sentiment_items_per_provider,
                    },
                )
                response.raise_for_status()
                for article in response.json().get("articles", []):
                    headline = first_text(article.get("title"), article.get("description"))
                    if not headline:
                        continue
                    source = article.get("source") or {}
                    items.append(
                        ProviderSentimentItem(
                            provider=self.name,
                            symbol=symbol,
                            headline=headline,
                            source=str(source.get("name") or "News API"),
                            observed_at=parse_datetime(article.get("publishedAt")),
                            related_asset=asset,
                            sentiment_score=score_text(headline),
                            confidence=0.72,
                        )
                    )
        return items

from __future__ import annotations

from datetime import datetime, timezone

from app.core.config import Settings, settings
from app.services.sentiment.interfaces import ProviderSentimentItem
from app.services.sentiment.providers.utils import asset_from_symbol, first_text
from app.services.sentiment.scoring import score_text


class RedditSentimentProvider:
    name = "reddit"

    def __init__(self, config: Settings = settings) -> None:
        self.config = config

    @property
    def is_configured(self) -> bool:
        return bool(self.config.reddit_bearer_token)

    def fetch(self, symbols: list[str]) -> list[ProviderSentimentItem]:
        import httpx

        items: list[ProviderSentimentItem] = []
        headers = {
            "Authorization": f"Bearer {self.config.reddit_bearer_token}",
            "User-Agent": self.config.reddit_user_agent,
        }
        endpoint = f"{self.config.reddit_api_base_url.rstrip('/')}/r/{self.config.reddit_subreddit}/search.json"
        with httpx.Client(timeout=self.config.sentiment_request_timeout_seconds, headers=headers) as client:
            for symbol in symbols:
                asset = asset_from_symbol(symbol)
                response = client.get(
                    endpoint,
                    params={
                        "q": f"{asset} OR {symbol}",
                        "restrict_sr": "true",
                        "sort": "new",
                        "t": "week",
                        "limit": self.config.sentiment_items_per_provider,
                    },
                )
                response.raise_for_status()
                for child in response.json().get("data", {}).get("children", []):
                    post = child.get("data") or {}
                    headline = first_text(post.get("title"), post.get("selftext"))
                    if not headline:
                        continue
                    engagement = float(post.get("score") or 0) + float(post.get("num_comments") or 0)
                    items.append(
                        ProviderSentimentItem(
                            provider=self.name,
                            symbol=symbol,
                            headline=headline,
                            source=f"r/{post.get('subreddit') or self.config.reddit_subreddit}",
                            observed_at=datetime.fromtimestamp(float(post.get("created_utc") or datetime.now(timezone.utc).timestamp()), tz=timezone.utc),
                            related_asset=asset,
                            sentiment_score=score_text(headline),
                            confidence=0.55 + min(0.3, engagement / 1000),
                        )
                    )
        return items

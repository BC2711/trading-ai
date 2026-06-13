from __future__ import annotations

import os
from datetime import datetime, timezone

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import Base
from app.models import SentimentItem
from app.services.sentiment.interfaces import ProviderSentimentItem
from app.services.sentiment.service import collect_provider_sentiment, persist_sentiment_items


def test_missing_provider_keys_return_fallback_sentiment() -> None:
    original_providers = settings.sentiment_providers
    original_news_key = settings.news_api_key
    original_cryptopanic_key = settings.cryptopanic_api_key
    original_reddit_token = settings.reddit_bearer_token
    original_x_token = settings.x_bearer_token
    settings.sentiment_providers = ["newsapi", "cryptopanic", "reddit", "x"]
    settings.news_api_key = None
    settings.cryptopanic_api_key = None
    settings.reddit_bearer_token = None
    settings.x_bearer_token = None

    try:
        items = collect_provider_sentiment(["BTCUSDT"])
    finally:
        settings.sentiment_providers = original_providers
        settings.news_api_key = original_news_key
        settings.cryptopanic_api_key = original_cryptopanic_key
        settings.reddit_bearer_token = original_reddit_token
        settings.x_bearer_token = original_x_token

    assert items
    assert {item.provider for item in items} == {"fallback"}
    assert {"News API Fallback", "CryptoPanic Fallback", "Reddit Fallback", "X/Twitter Fallback"} == {item.source for item in items}
    assert all(item.symbol == "BTCUSDT" for item in items)
    assert all(-1.0 <= item.sentiment_score <= 1.0 for item in items)


def test_persist_sentiment_items_stores_provider_metadata(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{(tmp_path / 'sentiment.sqlite').as_posix()}")
    Base.metadata.create_all(bind=engine)
    observed_at = datetime(2026, 6, 13, 9, 30, tzinfo=timezone.utc)
    item = ProviderSentimentItem(
        provider="newsapi",
        source="CoinDesk",
        symbol="ETHUSDT",
        related_asset="ETH",
        headline="ETH institutional inflows improve after upgrade",
        sentiment_score=0.56,
        confidence=0.82,
        observed_at=observed_at,
    )

    with Session(engine) as session:
        stored = persist_sentiment_items(session, [item])
        db_item = session.scalar(select(SentimentItem).where(SentimentItem.symbol == "ETHUSDT"))

    assert len(stored) == 1
    assert db_item is not None
    assert db_item.provider == "newsapi"
    assert db_item.source == "CoinDesk"
    assert db_item.symbol == "ETHUSDT"
    assert db_item.related_asset == "ETH"
    assert db_item.sentiment_score == 0.56
    assert db_item.confidence == 0.82
    assert db_item.observed_at.replace(tzinfo=timezone.utc) == observed_at

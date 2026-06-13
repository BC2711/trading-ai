from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import SentimentItem
from app.schemas.sentiment import SentimentItemRead, SentimentResponse
from app.services.repository import list_symbols, seed_defaults
from app.services.sentiment.interfaces import ProviderSentimentItem, SentimentProvider
from app.services.sentiment.providers import (
    CryptoPanicSentimentProvider,
    FallbackSentimentProvider,
    NewsApiSentimentProvider,
    RedditSentimentProvider,
    XSentimentProvider,
)
from app.services.sentiment.scoring import classification, impact_level


def get_market_sentiment(db: Session) -> SentimentResponse:
    return analyze_sentiment(db)


def get_symbol_sentiment(db: Session, symbol: str) -> SentimentResponse:
    return analyze_sentiment(db, symbol=symbol)


def analyze_sentiment(db: Session, symbol: str | None = None) -> SentimentResponse:
    seed_defaults(db)
    selected_symbols = [symbol.upper()] if symbol else [item.symbol for item in list_symbols(db)]
    provider_items = collect_provider_sentiment(selected_symbols)
    stored_items = persist_sentiment_items(db, provider_items)
    return _response([_to_schema(item) for item in stored_items])


def collect_provider_sentiment(symbols: list[str]) -> list[ProviderSentimentItem]:
    enabled = {name.lower() for name in settings.sentiment_providers}
    items: list[ProviderSentimentItem] = []

    for provider in configured_providers():
        if provider.name not in enabled or not provider.is_configured:
            continue
        try:
            items.extend(provider.fetch(symbols))
        except Exception:
            continue

    if items:
        return items
    return FallbackSentimentProvider().fetch(symbols)


def configured_providers() -> list[SentimentProvider]:
    return [
        NewsApiSentimentProvider(),
        CryptoPanicSentimentProvider(),
        RedditSentimentProvider(),
        XSentimentProvider(),
    ]


def persist_sentiment_items(db: Session, provider_items: list[ProviderSentimentItem]) -> list[SentimentItem]:
    stored_items: list[SentimentItem] = []
    for item in provider_items:
        stored = db.scalar(
            select(SentimentItem).where(
                SentimentItem.provider == item.provider,
                SentimentItem.symbol == item.symbol,
                SentimentItem.headline == item.headline[:1000],
                SentimentItem.observed_at == item.observed_at,
            )
        )
        if stored is None:
            stored = SentimentItem(
                provider=item.provider,
                source=item.source[:160],
                symbol=item.symbol,
                related_asset=item.related_asset,
                headline=item.headline[:1000],
                sentiment_score=round(max(-1.0, min(1.0, item.sentiment_score)), 4),
                confidence=round(max(0.0, min(1.0, item.confidence)), 4),
                observed_at=item.observed_at,
            )
            db.add(stored)
            try:
                db.commit()
                db.refresh(stored)
            except IntegrityError:
                db.rollback()
                stored = db.scalar(
                    select(SentimentItem).where(
                        SentimentItem.provider == item.provider,
                        SentimentItem.symbol == item.symbol,
                        SentimentItem.headline == item.headline[:1000],
                        SentimentItem.observed_at == item.observed_at,
                    )
                )
        if stored is not None:
            stored_items.append(stored)
    return stored_items


def _to_schema(item: SentimentItem) -> SentimentItemRead:
    return SentimentItemRead(
        symbol=item.symbol,
        sentiment_score=item.sentiment_score,
        status=classification(item.sentiment_score),
        headline=item.headline,
        source=item.source,
        date=item.observed_at,
        impact_level=impact_level(item.sentiment_score, item.confidence),
        related_asset=item.related_asset,
    )


def _response(items: list[SentimentItemRead]) -> SentimentResponse:
    market_score = round(sum(item.sentiment_score for item in items) / len(items), 4) if items else 0.0
    return SentimentResponse(
        market_sentiment_score=market_score,
        market_status=classification(market_score),
        bullish_count=sum(1 for item in items if item.status == "bullish"),
        bearish_count=sum(1 for item in items if item.status == "bearish"),
        neutral_count=sum(1 for item in items if item.status == "neutral"),
        items=sorted(items, key=lambda item: (item.symbol, item.date), reverse=True),
    )

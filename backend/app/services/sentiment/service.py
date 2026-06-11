from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.schemas.sentiment import SentimentItemRead, SentimentResponse
from app.services.repository import list_symbols, seed_defaults


@dataclass(frozen=True)
class RawSentimentPost:
    symbol: str
    headline: str
    source: str
    date: datetime
    related_asset: str


POSITIVE_TERMS = {
    "breakout": 0.28,
    "bullish": 0.3,
    "demand": 0.18,
    "inflows": 0.22,
    "institutional": 0.16,
    "partnership": 0.18,
    "upgrade": 0.2,
    "accumulation": 0.18,
    "support": 0.12,
}

NEGATIVE_TERMS = {
    "bearish": -0.3,
    "exploit": -0.35,
    "outflows": -0.24,
    "rejection": -0.18,
    "selloff": -0.32,
    "regulatory": -0.2,
    "liquidations": -0.25,
    "resistance": -0.12,
    "slowdown": -0.16,
}


def get_market_sentiment(db: Session) -> SentimentResponse:
    return analyze_sentiment(db)


def get_symbol_sentiment(db: Session, symbol: str) -> SentimentResponse:
    return analyze_sentiment(db, symbol=symbol)


def analyze_sentiment(db: Session, symbol: str | None = None) -> SentimentResponse:
    seed_defaults(db)
    selected_symbols = [symbol.upper()] if symbol else [item.symbol for item in list_symbols(db)]
    raw_items = collect_placeholder_sentiment(selected_symbols)
    scored_items = [_score_item(item) for item in raw_items]
    return _response(scored_items)


def collect_placeholder_sentiment(symbols: list[str]) -> list[RawSentimentPost]:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    items: list[RawSentimentPost] = []
    for index, symbol in enumerate(symbols):
        asset = _asset_from_symbol(symbol)
        offset = index * 17
        items.extend(
            [
                *collect_news_placeholder(symbol, asset, now - timedelta(minutes=offset)),
                *collect_twitter_placeholder(symbol, asset, now - timedelta(minutes=offset + 5)),
                *collect_reddit_placeholder(symbol, asset, now - timedelta(minutes=offset + 10)),
                *collect_cryptopanic_placeholder(symbol, asset, now - timedelta(minutes=offset + 15)),
            ]
        )
    return items


def collect_news_placeholder(symbol: str, asset: str, timestamp: datetime) -> list[RawSentimentPost]:
    return [
        RawSentimentPost(
            symbol=symbol,
            headline=f"{asset} institutional inflows improve as traders watch resistance",
            source="News Placeholder",
            date=timestamp,
            related_asset=asset,
        )
    ]


def collect_twitter_placeholder(symbol: str, asset: str, timestamp: datetime) -> list[RawSentimentPost]:
    return [
        RawSentimentPost(
            symbol=symbol,
            headline=f"X chatter turns bullish on {asset} breakout but warns of liquidations",
            source="Twitter/X Placeholder",
            date=timestamp,
            related_asset=asset,
        )
    ]


def collect_reddit_placeholder(symbol: str, asset: str, timestamp: datetime) -> list[RawSentimentPost]:
    return [
        RawSentimentPost(
            symbol=symbol,
            headline=f"Reddit traders debate {asset} accumulation near support",
            source="Reddit Placeholder",
            date=timestamp,
            related_asset=asset,
        )
    ]


def collect_cryptopanic_placeholder(symbol: str, asset: str, timestamp: datetime) -> list[RawSentimentPost]:
    headline = (
        f"CryptoPanic placeholder flags {asset} regulatory risk after rejection"
        if asset == "ETH"
        else f"CryptoPanic placeholder tracks {asset} demand after network upgrade"
    )
    return [
        RawSentimentPost(
            symbol=symbol,
            headline=headline,
            source="CryptoPanic Placeholder",
            date=timestamp,
            related_asset=asset,
        )
    ]


def _score_item(item: RawSentimentPost) -> SentimentItemRead:
    text = item.headline.lower()
    score = 0.0
    for term, weight in POSITIVE_TERMS.items():
        if term in text:
            score += weight
    for term, weight in NEGATIVE_TERMS.items():
        if term in text:
            score += weight
    score = round(max(-1.0, min(1.0, score)), 4)
    return SentimentItemRead(
        symbol=item.symbol,
        sentiment_score=score,
        status=_classification(score),
        headline=item.headline,
        source=item.source,
        date=item.date,
        impact_level=_impact_level(score),
        related_asset=item.related_asset,
    )


def _response(items: list[SentimentItemRead]) -> SentimentResponse:
    market_score = round(sum(item.sentiment_score for item in items) / len(items), 4) if items else 0.0
    return SentimentResponse(
        market_sentiment_score=market_score,
        market_status=_classification(market_score),
        bullish_count=sum(1 for item in items if item.status == "bullish"),
        bearish_count=sum(1 for item in items if item.status == "bearish"),
        neutral_count=sum(1 for item in items if item.status == "neutral"),
        items=sorted(items, key=lambda item: (item.symbol, item.date), reverse=True),
    )


def _classification(score: float) -> str:
    if score >= 0.15:
        return "bullish"
    if score <= -0.15:
        return "bearish"
    return "neutral"


def _impact_level(score: float) -> str:
    absolute_score = abs(score)
    if absolute_score >= 0.45:
        return "high"
    if absolute_score >= 0.2:
        return "medium"
    return "low"


def _asset_from_symbol(symbol: str) -> str:
    if symbol.endswith("USDT"):
        return symbol.removesuffix("USDT")
    if symbol.endswith("USD"):
        return symbol.removesuffix("USD")
    return symbol

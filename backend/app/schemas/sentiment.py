from datetime import datetime

from pydantic import BaseModel, Field


class SentimentAnalyzeRequest(BaseModel):
    symbol: str | None = None


class SentimentItemRead(BaseModel):
    symbol: str
    sentiment_score: float
    status: str
    headline: str
    source: str
    date: datetime
    impact_level: str
    related_asset: str


class SentimentResponse(BaseModel):
    market_sentiment_score: float
    market_status: str
    bullish_count: int
    bearish_count: int
    neutral_count: int
    items: list[SentimentItemRead] = Field(default_factory=list)

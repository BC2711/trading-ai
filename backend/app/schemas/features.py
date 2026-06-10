from datetime import datetime

from pydantic import BaseModel, Field


class FeatureSetRead(BaseModel):
    id: int
    name: str
    description: str
    features: list[str]
    version: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MarketFeatureRead(BaseModel):
    id: int
    symbol: str
    timeframe: str
    feature_set: str
    candle_opened_at: datetime
    values: dict[str, float]
    source: str
    calculated_at: datetime


class FeatureCalculationRequest(BaseModel):
    symbol: str = "BTCUSDT"
    timeframe: str = "15m"
    lookback: int = Field(default=240, ge=80, le=2000)
    feature_set: str = Field(default="default-ai-trading", min_length=2, max_length=120)
    persist_last: int = Field(default=100, ge=1, le=500)


class FeatureCalculationResponse(BaseModel):
    symbol: str
    timeframe: str
    feature_set: FeatureSetRead
    rows_calculated: int
    latest: MarketFeatureRead | None = None
    log_id: int

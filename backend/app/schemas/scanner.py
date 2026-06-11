from datetime import datetime

from pydantic import BaseModel, Field


class ScannerRunRequest(BaseModel):
    symbols: list[str] | None = None
    timeframe: str = "15m"
    lookback: int = Field(default=240, ge=60, le=1000)


class ScannerRead(BaseModel):
    symbol: str
    current_price: float
    signal: str
    confidence: float
    risk_level: str
    rsi: float
    macd_signal: str
    trend_direction: str
    volatility: float
    recommended_action: str
    created_at: datetime

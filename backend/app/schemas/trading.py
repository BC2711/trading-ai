from datetime import datetime

from pydantic import BaseModel, Field


class SymbolCreate(BaseModel):
    symbol: str = Field(..., examples=["BTCUSDT"])
    base_asset: str = Field(..., examples=["BTC"])
    quote_asset: str = Field(..., examples=["USDT"])
    market: str = "crypto"
    exchange: str = "binance_testnet"


class SymbolRead(SymbolCreate):
    id: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MarketCandleCreate(BaseModel):
    symbol: str = Field(..., examples=["BTCUSDT"])
    timeframe: str = "15m"
    opened_at: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketCandleRead(BaseModel):
    id: int
    symbol: str
    timeframe: str
    opened_at: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketDataSyncRequest(BaseModel):
    symbols: list[str] = Field(default_factory=lambda: ["BTCUSDT", "ETHUSDT"])
    timeframe: str = "15m"
    limit: int = Field(default=500, ge=1, le=1000)
    regenerate_signals: bool = True


class MarketDataSyncResult(BaseModel):
    symbol: str
    timeframe: str
    fetched: int
    inserted: int
    updated: int


class MarketDataSyncResponse(BaseModel):
    provider: str
    timeframe: str
    results: list[MarketDataSyncResult]
    signals: list["SignalRead"] = Field(default_factory=list)


class SignalRead(BaseModel):
    id: int
    symbol: str
    direction: str
    confidence: float
    timeframe: str
    reason: str
    status: str
    created_at: datetime


class SignalGenerateRequest(BaseModel):
    symbol: str | None = None
    timeframe: str = "15m"


class StrategyRead(BaseModel):
    id: int
    name: str
    description: str
    timeframe: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RiskSettingRead(BaseModel):
    id: int
    name: str
    max_risk_per_trade: float
    max_daily_loss: float
    max_open_trades: int
    max_symbol_exposure: float
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}

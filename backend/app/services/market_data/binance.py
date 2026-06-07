from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.schemas.trading import MarketCandleCreate


BINANCE_INTERVALS = {
    "1m",
    "3m",
    "5m",
    "15m",
    "30m",
    "1h",
    "2h",
    "4h",
    "6h",
    "8h",
    "12h",
    "1d",
    "3d",
    "1w",
    "1M",
}


class MarketDataProviderError(RuntimeError):
    pass


def fetch_binance_klines(symbol: str, timeframe: str = "15m", limit: int = 500) -> list[MarketCandleCreate]:
    symbol = symbol.upper()

    if timeframe not in BINANCE_INTERVALS:
        raise MarketDataProviderError(f"Unsupported Binance interval: {timeframe}")

    try:
        response = httpx.get(
            f"{settings.binance_api_base_url}/api/v3/klines",
            params={"symbol": symbol, "interval": timeframe, "limit": limit},
            timeout=15.0,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise MarketDataProviderError(f"Unable to fetch Binance candles for {symbol}: {exc}") from exc

    payload = response.json()
    if not isinstance(payload, list):
        raise MarketDataProviderError(f"Unexpected Binance response for {symbol}")

    return [binance_kline_to_candle(symbol, timeframe, item) for item in payload]


def binance_kline_to_candle(symbol: str, timeframe: str, item: list[Any]) -> MarketCandleCreate:
    opened_at = datetime.fromtimestamp(int(item[0]) / 1000, tz=timezone.utc)

    return MarketCandleCreate(
        symbol=symbol,
        timeframe=timeframe,
        opened_at=opened_at,
        open=float(item[1]),
        high=float(item[2]),
        low=float(item[3]),
        close=float(item[4]),
        volume=float(item[5]),
    )

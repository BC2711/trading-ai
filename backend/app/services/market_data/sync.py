from sqlalchemy.orm import Session

from app.models import Symbol
from app.schemas.trading import MarketCandleCreate, MarketDataSyncResult
from app.services.market_data.binance import fetch_binance_klines
from app.services.market_data.repository import MarketDataRepository


def sync_market_data(
    db: Session,
    symbols: list[str],
    timeframe: str = "15m",
    limit: int = 500,
) -> list[MarketDataSyncResult]:
    results: list[MarketDataSyncResult] = []

    for symbol in symbols:
        normalized_symbol = symbol.upper()
        candles = fetch_binance_klines(normalized_symbol, timeframe, limit)
        repository = MarketDataRepository(db)
        inserted, updated = repository.upsert_candles(candles, market="crypto", exchange="binance")
        results.append(
            MarketDataSyncResult(
                symbol=normalized_symbol,
                timeframe=timeframe,
                fetched=len(candles),
                inserted=inserted,
                updated=updated,
            )
        )

    db.commit()
    return results


def ensure_symbol_from_name(db: Session, symbol: str) -> Symbol:
    return MarketDataRepository(db).ensure_symbol(symbol, market="crypto", exchange="binance")


def upsert_candles(db: Session, symbol: Symbol, candles: list[MarketCandleCreate]) -> tuple[int, int]:
    return MarketDataRepository(db).upsert_candles(candles, market=symbol.market, exchange=symbol.exchange)

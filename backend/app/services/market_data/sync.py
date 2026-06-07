from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MarketCandle, Symbol
from app.schemas.trading import MarketCandleCreate, MarketDataSyncResult, SymbolCreate
from app.services.market_data.binance import fetch_binance_klines
from app.services.repository import create_symbol, get_symbol


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
        symbol_model = ensure_symbol_from_name(db, normalized_symbol)
        inserted, updated = upsert_candles(db, symbol_model, candles)
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
    existing = get_symbol(db, symbol)
    if existing:
        return existing

    base_asset, quote_asset = split_symbol(symbol)
    return create_symbol(
        db,
        SymbolCreate(
            symbol=symbol,
            base_asset=base_asset,
            quote_asset=quote_asset,
            market="crypto",
            exchange="binance",
        ),
    )


def split_symbol(symbol: str) -> tuple[str, str]:
    known_quotes = ["USDT", "USDC", "BUSD", "FDUSD", "BTC", "ETH", "BNB", "USD", "EUR"]
    for quote in known_quotes:
        if symbol.endswith(quote) and len(symbol) > len(quote):
            return symbol[: -len(quote)], quote
    return symbol, "UNKNOWN"


def upsert_candles(db: Session, symbol: Symbol, candles: list[MarketCandleCreate]) -> tuple[int, int]:
    inserted = 0
    updated = 0

    for candle in candles:
        existing = db.scalar(
            select(MarketCandle).where(
                MarketCandle.symbol_id == symbol.id,
                MarketCandle.timeframe == candle.timeframe,
                MarketCandle.opened_at == candle.opened_at,
            )
        )

        if existing:
            existing.open = candle.open
            existing.high = candle.high
            existing.low = candle.low
            existing.close = candle.close
            existing.volume = candle.volume
            updated += 1
        else:
            db.add(
                MarketCandle(
                    symbol_id=symbol.id,
                    timeframe=candle.timeframe,
                    opened_at=candle.opened_at,
                    open=candle.open,
                    high=candle.high,
                    low=candle.low,
                    close=candle.close,
                    volume=candle.volume,
                )
            )
            inserted += 1

    return inserted, updated

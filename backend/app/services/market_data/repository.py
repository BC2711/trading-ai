from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MarketCandle, MarketOrderBookSnapshot, MarketTick, MarketTrade, Symbol
from app.schemas.trading import (
    MarketCandleCreate,
    MarketOrderBookCreate,
    MarketTickCreate,
    MarketTradeCreate,
    SymbolCreate,
)
from app.services.repository import create_symbol, get_symbol

SUPPORTED_MARKETS = {"forex", "stock", "stocks", "crypto", "commodity", "commodities", "index", "indices"}


def normalize_market(market: str) -> str:
    value = market.lower()
    if value == "stocks":
        return "stock"
    if value == "commodities":
        return "commodity"
    if value == "indices":
        return "index"
    if value not in SUPPORTED_MARKETS:
        raise ValueError(f"Unsupported market: {market}")
    return value


def split_symbol(symbol: str) -> tuple[str, str]:
    normalized = symbol.upper().replace("/", "")
    known_quotes = ["USDT", "USDC", "BUSD", "FDUSD", "BTC", "ETH", "BNB", "USD", "EUR", "JPY", "GBP", "AUD", "CAD", "CHF"]
    for quote in known_quotes:
        if normalized.endswith(quote) and len(normalized) > len(quote):
            return normalized[: -len(quote)], quote
    return normalized, "UNKNOWN"


def timeframe_delta(timeframe: str) -> timedelta:
    unit = timeframe[-1]
    try:
        amount = int(timeframe[:-1])
    except ValueError as exc:
        raise ValueError(f"Unsupported timeframe: {timeframe}") from exc

    if unit == "m":
        return timedelta(minutes=amount)
    if unit == "h":
        return timedelta(hours=amount)
    if unit == "d":
        return timedelta(days=amount)
    if unit == "w":
        return timedelta(weeks=amount)
    raise ValueError(f"Unsupported timeframe: {timeframe}")


class MarketDataRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def ensure_symbol(self, symbol: str, *, market: str = "crypto", exchange: str = "binance") -> Symbol:
        normalized_symbol = symbol.upper().replace("/", "")
        existing = get_symbol(self.db, normalized_symbol)
        if existing:
            return existing

        base_asset, quote_asset = split_symbol(normalized_symbol)
        return create_symbol(
            self.db,
            SymbolCreate(
                symbol=normalized_symbol,
                base_asset=base_asset,
                quote_asset=quote_asset,
                market=normalize_market(market),
                exchange=exchange.lower(),
            ),
        )

    def list_candles(self, symbol: str, timeframe: str, limit: int = 500) -> list[MarketCandle]:
        symbol_model = get_symbol(self.db, symbol)
        if symbol_model is None:
            return []
        statement = (
            select(MarketCandle)
            .where(MarketCandle.symbol_id == symbol_model.id, MarketCandle.timeframe == timeframe)
            .order_by(MarketCandle.opened_at.desc())
            .limit(limit)
        )
        return list(reversed(self.db.scalars(statement).all()))

    def list_ticks(self, symbol: str, limit: int = 200) -> list[MarketTick]:
        symbol_model = get_symbol(self.db, symbol)
        if symbol_model is None:
            return []
        statement = (
            select(MarketTick)
            .where(MarketTick.symbol_id == symbol_model.id)
            .order_by(MarketTick.tick_time.desc())
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def list_trades(self, symbol: str, limit: int = 200) -> list[MarketTrade]:
        symbol_model = get_symbol(self.db, symbol)
        if symbol_model is None:
            return []
        statement = (
            select(MarketTrade)
            .where(MarketTrade.symbol_id == symbol_model.id)
            .order_by(MarketTrade.traded_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def list_order_books(self, symbol: str, limit: int = 50) -> list[MarketOrderBookSnapshot]:
        symbol_model = get_symbol(self.db, symbol)
        if symbol_model is None:
            return []
        statement = (
            select(MarketOrderBookSnapshot)
            .where(MarketOrderBookSnapshot.symbol_id == symbol_model.id)
            .order_by(MarketOrderBookSnapshot.captured_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(statement).all())

    def upsert_candles(self, candles: list[MarketCandleCreate], *, market: str = "crypto", exchange: str = "binance") -> tuple[int, int]:
        inserted = 0
        updated = 0
        for candle in candles:
            symbol = self.ensure_symbol(candle.symbol, market=market, exchange=exchange)
            existing = self.db.scalar(
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
                existing.spread = candle.spread
                updated += 1
            else:
                self.db.add(
                    MarketCandle(
                        symbol_id=symbol.id,
                        timeframe=candle.timeframe,
                        opened_at=candle.opened_at,
                        open=candle.open,
                        high=candle.high,
                        low=candle.low,
                        close=candle.close,
                        volume=candle.volume,
                        spread=candle.spread,
                    )
                )
                inserted += 1
        return inserted, updated

    def upsert_ticks(self, ticks: list[MarketTickCreate], *, market: str = "crypto") -> tuple[int, int]:
        inserted = 0
        updated = 0
        for tick in ticks:
            symbol = self.ensure_symbol(tick.symbol, market=market, exchange=tick.exchange)
            spread = tick.spread if tick.spread is not None else calculate_spread(tick.bid, tick.ask)
            existing = self.db.scalar(
                select(MarketTick).where(
                    MarketTick.symbol_id == symbol.id,
                    MarketTick.exchange == tick.exchange.lower(),
                    MarketTick.tick_time == tick.tick_time,
                )
            )
            if existing:
                existing.bid = tick.bid
                existing.ask = tick.ask
                existing.price = tick.price
                existing.volume = tick.volume
                existing.spread = spread
                existing.source = tick.source
                updated += 1
            else:
                self.db.add(
                    MarketTick(
                        symbol_id=symbol.id,
                        exchange=tick.exchange.lower(),
                        tick_time=tick.tick_time,
                        bid=tick.bid,
                        ask=tick.ask,
                        price=tick.price,
                        volume=tick.volume,
                        spread=spread,
                        source=tick.source,
                    )
                )
                inserted += 1
        return inserted, updated

    def upsert_trades(self, trades: list[MarketTradeCreate], *, market: str = "crypto") -> tuple[int, int]:
        inserted = 0
        updated = 0
        for trade in trades:
            symbol = self.ensure_symbol(trade.symbol, market=market, exchange=trade.exchange)
            existing = self.db.scalar(
                select(MarketTrade).where(
                    MarketTrade.symbol_id == symbol.id,
                    MarketTrade.exchange == trade.exchange.lower(),
                    MarketTrade.trade_id == trade.trade_id,
                )
            )
            if existing:
                existing.traded_at = trade.traded_at
                existing.price = trade.price
                existing.quantity = trade.quantity
                existing.side = trade.side
                existing.source = trade.source
                updated += 1
            else:
                self.db.add(
                    MarketTrade(
                        symbol_id=symbol.id,
                        exchange=trade.exchange.lower(),
                        trade_id=trade.trade_id,
                        traded_at=trade.traded_at,
                        price=trade.price,
                        quantity=trade.quantity,
                        side=trade.side,
                        source=trade.source,
                    )
                )
                inserted += 1
        return inserted, updated

    def upsert_order_books(self, snapshots: list[MarketOrderBookCreate], *, market: str = "crypto") -> tuple[int, int]:
        inserted = 0
        updated = 0
        for snapshot in snapshots:
            symbol = self.ensure_symbol(snapshot.symbol, market=market, exchange=snapshot.exchange)
            best_bid = float(snapshot.bids[0][0]) if snapshot.bids else None
            best_ask = float(snapshot.asks[0][0]) if snapshot.asks else None
            spread = calculate_spread(best_bid, best_ask)
            depth = max(len(snapshot.bids), len(snapshot.asks))
            existing = self.db.scalar(
                select(MarketOrderBookSnapshot).where(
                    MarketOrderBookSnapshot.symbol_id == symbol.id,
                    MarketOrderBookSnapshot.exchange == snapshot.exchange.lower(),
                    MarketOrderBookSnapshot.captured_at == snapshot.captured_at,
                )
            )
            if existing:
                existing.bids = snapshot.bids
                existing.asks = snapshot.asks
                existing.best_bid = best_bid
                existing.best_ask = best_ask
                existing.spread = spread
                existing.depth = depth
                existing.source = snapshot.source
                updated += 1
            else:
                self.db.add(
                    MarketOrderBookSnapshot(
                        symbol_id=symbol.id,
                        exchange=snapshot.exchange.lower(),
                        captured_at=snapshot.captured_at,
                        bids=snapshot.bids,
                        asks=snapshot.asks,
                        best_bid=best_bid,
                        best_ask=best_ask,
                        spread=spread,
                        depth=depth,
                        source=snapshot.source,
                    )
                )
                inserted += 1
        return inserted, updated

    def detect_missing_candles(self, symbol: str, timeframe: str, limit: int = 500) -> list[datetime]:
        candles = self.list_candles(symbol, timeframe, limit)
        if len(candles) < 2:
            return []

        interval = timeframe_delta(timeframe)
        missing: list[datetime] = []
        previous = candles[0].opened_at
        for candle in candles[1:]:
            expected = previous + interval
            while expected < candle.opened_at:
                missing.append(expected)
                expected += interval
            previous = candle.opened_at
        return missing


def calculate_spread(bid: float | None, ask: float | None) -> float:
    if bid is None or ask is None:
        return 0.0
    return round(max(0.0, ask - bid), 10)

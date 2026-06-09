from datetime import datetime

from sqlalchemy.orm import Session

from app.schemas.trading import (
    MarketCandleCreate,
    MarketDataImportRequest,
    MarketDataImportResponse,
    MarketDataRepairRequest,
    MarketDataRepairResponse,
    MarketDataStreamEvent,
    MarketDataSyncResult,
    MarketDataValidationIssue,
    MarketDataValidationResponse,
    MarketOrderBookCreate,
    MarketTickCreate,
    MarketTradeCreate,
    MissingCandleGap,
)
from app.services.market_data.binance import MarketDataProviderError, fetch_binance_klines
from app.services.market_data.repository import MarketDataRepository, normalize_market
from app.services.signals import generate_signals


class MarketDataService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = MarketDataRepository(db)

    def import_historical_data(self, payload: MarketDataImportRequest) -> MarketDataImportResponse:
        market = normalize_market(payload.market)
        candle_inserted, candle_updated = self.repository.upsert_candles(
            payload.candles,
            market=market,
            exchange=payload.exchange,
        )
        tick_inserted, tick_updated = self.repository.upsert_ticks(payload.ticks, market=market)
        trade_inserted, trade_updated = self.repository.upsert_trades(payload.trades, market=market)
        order_book_inserted, order_book_updated = self.repository.upsert_order_books(payload.order_books, market=market)
        self.db.commit()

        return MarketDataImportResponse(
            status="ok",
            candle_inserted=candle_inserted,
            candle_updated=candle_updated,
            tick_inserted=tick_inserted,
            tick_updated=tick_updated,
            trade_inserted=trade_inserted,
            trade_updated=trade_updated,
            order_book_inserted=order_book_inserted,
            order_book_updated=order_book_updated,
        )

    def validate_data(self, symbol: str, timeframe: str = "15m", limit: int = 500) -> MarketDataValidationResponse:
        candles = self.repository.list_candles(symbol, timeframe, limit)
        issues: list[MarketDataValidationIssue] = []

        for candle in candles:
            issues.extend(validate_candle(candle.symbol_ref.symbol, candle.timeframe, candle.opened_at, candle.open, candle.high, candle.low, candle.close, candle.volume, candle.spread))

        missing = [
            MissingCandleGap(symbol=symbol.upper(), timeframe=timeframe, expected_at=expected_at)
            for expected_at in self.repository.detect_missing_candles(symbol, timeframe, limit)
        ]

        for gap in missing:
            issues.append(
                MarketDataValidationIssue(
                    symbol=gap.symbol,
                    timeframe=gap.timeframe,
                    timestamp=gap.expected_at,
                    severity="warning",
                    code="missing_candle",
                    message=f"Missing candle at {gap.expected_at.isoformat()}",
                )
            )

        return MarketDataValidationResponse(
            symbol=symbol.upper(),
            timeframe=timeframe,
            checked_candles=len(candles),
            missing_candles=missing,
            issues=issues,
            valid=not issues,
        )

    def repair_data(self, payload: MarketDataRepairRequest) -> MarketDataRepairResponse:
        before = self.validate_data(payload.symbol, payload.timeframe, payload.limit)
        sync_result: MarketDataSyncResult | None = None
        error: str | None = None

        if payload.repair_missing and before.missing_candles:
            try:
                candles = fetch_binance_klines(payload.symbol.upper(), payload.timeframe, payload.limit)
                inserted, updated = self.repository.upsert_candles(candles, market="crypto", exchange="binance")
                self.db.commit()
                sync_result = MarketDataSyncResult(
                    symbol=payload.symbol.upper(),
                    timeframe=payload.timeframe,
                    fetched=len(candles),
                    inserted=inserted,
                    updated=updated,
                )
                if payload.regenerate_signals:
                    generate_signals(self.db, payload.symbol, payload.timeframe)
            except MarketDataProviderError as exc:
                error = str(exc)

        after = self.validate_data(payload.symbol, payload.timeframe, payload.limit) if error is None else None
        return MarketDataRepairResponse(
            status="failed" if error else "ok",
            validation_before=before,
            validation_after=after,
            sync_result=sync_result,
            error=error,
        )

    def ingest_stream_event(self, event: MarketDataStreamEvent, *, market: str = "crypto") -> dict:
        payload = event.payload
        if event.channel == "candles" and isinstance(payload, MarketCandleCreate):
            inserted, updated = self.repository.upsert_candles([payload], market=market, exchange="stream")
        elif event.channel == "ticks" and isinstance(payload, MarketTickCreate):
            inserted, updated = self.repository.upsert_ticks([payload], market=market)
        elif event.channel == "trades" and isinstance(payload, MarketTradeCreate):
            inserted, updated = self.repository.upsert_trades([payload], market=market)
        elif event.channel == "order_books" and isinstance(payload, MarketOrderBookCreate):
            inserted, updated = self.repository.upsert_order_books([payload], market=market)
        else:
            raise ValueError(f"Payload does not match stream channel {event.channel}")

        self.db.commit()
        return {"channel": event.channel, "inserted": inserted, "updated": updated, "payload": payload.model_dump(mode="json")}


def validate_candle(
    symbol: str,
    timeframe: str,
    opened_at: datetime,
    open_price: float,
    high: float,
    low: float,
    close: float,
    volume: float,
    spread: float,
) -> list[MarketDataValidationIssue]:
    issues: list[MarketDataValidationIssue] = []
    if min(open_price, high, low, close) <= 0:
        issues.append(issue(symbol, timeframe, opened_at, "error", "non_positive_price", "OHLC prices must be positive."))
    if high < max(open_price, close, low):
        issues.append(issue(symbol, timeframe, opened_at, "error", "invalid_high", "High is below one or more OHLC values."))
    if low > min(open_price, close, high):
        issues.append(issue(symbol, timeframe, opened_at, "error", "invalid_low", "Low is above one or more OHLC values."))
    if volume < 0:
        issues.append(issue(symbol, timeframe, opened_at, "error", "negative_volume", "Volume cannot be negative."))
    if spread < 0:
        issues.append(issue(symbol, timeframe, opened_at, "error", "negative_spread", "Spread cannot be negative."))
    return issues


def issue(symbol: str, timeframe: str, timestamp: datetime, severity: str, code: str, message: str) -> MarketDataValidationIssue:
    return MarketDataValidationIssue(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp,
        severity=severity,
        code=code,
        message=message,
    )

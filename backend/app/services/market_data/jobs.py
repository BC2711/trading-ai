from sqlalchemy.orm import Session

from app.core.config import settings
from app.schemas.trading import MarketDataRefreshResponse, MarketDataSyncResult
from app.services.market_data.binance import MarketDataProviderError
from app.services.market_data.sync import sync_market_data
from app.services.signals import generate_signals


def run_market_data_refresh(
    db: Session,
    symbols: list[str] | None = None,
    timeframe: str | None = None,
    limit: int | None = None,
    regenerate_signals: bool | None = None,
) -> MarketDataRefreshResponse:
    selected_symbols = [symbol.upper() for symbol in (symbols or settings.market_sync_symbols)]
    selected_timeframe = timeframe or settings.market_sync_timeframe
    selected_limit = limit or settings.market_sync_limit
    should_regenerate = (
        settings.market_sync_regenerate_signals if regenerate_signals is None else regenerate_signals
    )
    results: list[MarketDataSyncResult] = []
    generated_signal_count = 0

    try:
        results = sync_market_data(db, selected_symbols, selected_timeframe, selected_limit)
        if should_regenerate:
            generated_signal_count = len(generate_signals(db, timeframe=selected_timeframe))
        status = "ok"
        error = None
    except MarketDataProviderError as exc:
        status = "failed"
        error = str(exc)

    return MarketDataRefreshResponse(
        status=status,
        provider="binance",
        symbols=selected_symbols,
        timeframe=selected_timeframe,
        limit=selected_limit,
        results=results,
        generated_signal_count=generated_signal_count,
        error=error,
    )

from sqlalchemy.orm import Session

from app.core.config import settings
from app.schemas.trading import MarketDataRefreshResponse, MarketDataRepairRequest, MarketDataRepairResponse
from app.services.market_data.jobs import run_market_data_refresh
from app.services.market_data.service import MarketDataService


class MarketDataScheduler:
    def __init__(self, db: Session) -> None:
        self.db = db

    def scheduled_update(self) -> MarketDataRefreshResponse:
        return run_market_data_refresh(
            self.db,
            symbols=settings.market_sync_symbols,
            timeframe=settings.market_sync_timeframe,
            limit=settings.market_sync_limit,
            regenerate_signals=settings.market_sync_regenerate_signals,
        )

    def scheduled_repair(self, symbol: str, timeframe: str | None = None) -> MarketDataRepairResponse:
        service = MarketDataService(self.db)
        return service.repair_data(
            MarketDataRepairRequest(
                symbol=symbol,
                timeframe=timeframe or settings.market_sync_timeframe,
                limit=settings.market_sync_limit,
                repair_missing=True,
                regenerate_signals=settings.market_sync_regenerate_signals,
            )
        )

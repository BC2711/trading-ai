from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.deps import get_db
from app.schemas.trading import MarketCandleRead, MarketHistoryResponse
from app.services.market_data.warehouse import MarketWarehouseService
from app.db.auth import require_permission

router = APIRouter()

@router.get("/candles", response_model=list[MarketCandleRead])
def get_candles(
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("15m"),
    limit: int = Query(200),
    db: Session = Depends(get_db),
    _u = Depends(require_permission("market-data:view"))
):
    from app.services.repository import list_candles
    # Implementation mapping from original routes.py
    return list_candles(db, symbol, timeframe, limit)

@router.get("/history/{symbol}", response_model=MarketHistoryResponse)
def get_market_history(
    symbol: str,
    timeframe: str = Query("15m"),
    limit: int = Query(500),
    db: Session = Depends(get_db),
    _u = Depends(require_permission("market-data:view"))
):
    return MarketWarehouseService(db).retrieve_market_history(symbol, timeframe=timeframe, limit=limit)
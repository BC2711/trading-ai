from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MarketCandle, RiskSetting, Strategy, Symbol
from app.schemas.trading import SymbolCreate


DEFAULT_SYMBOLS = [
    SymbolCreate(symbol="BTCUSDT", base_asset="BTC", quote_asset="USDT"),
    SymbolCreate(symbol="ETHUSDT", base_asset="ETH", quote_asset="USDT"),
]


def list_symbols(db: Session) -> list[Symbol]:
    seed_defaults(db)
    return list(db.scalars(select(Symbol).order_by(Symbol.symbol)).all())


def create_symbol(db: Session, payload: SymbolCreate) -> Symbol:
    existing = db.scalar(select(Symbol).where(Symbol.symbol == payload.symbol.upper()))
    if existing:
        return existing

    symbol = Symbol(
        symbol=payload.symbol.upper(),
        base_asset=payload.base_asset.upper(),
        quote_asset=payload.quote_asset.upper(),
        market=payload.market,
        exchange=payload.exchange,
    )
    db.add(symbol)
    db.commit()
    db.refresh(symbol)
    return symbol


def get_symbol(db: Session, symbol: str) -> Symbol | None:
    return db.scalar(select(Symbol).where(Symbol.symbol == symbol.upper()))


def list_candles(db: Session, symbol: str, timeframe: str = "15m", limit: int = 200) -> list[MarketCandle]:
    seed_defaults(db)
    symbol_model = get_symbol(db, symbol)
    if not symbol_model:
        return []

    statement = (
        select(MarketCandle)
        .where(MarketCandle.symbol_id == symbol_model.id, MarketCandle.timeframe == timeframe)
        .order_by(MarketCandle.opened_at.desc())
        .limit(limit)
    )
    return list(reversed(db.scalars(statement).all()))


def ensure_default_strategy(db: Session) -> Strategy:
    strategy = db.scalar(select(Strategy).where(Strategy.name == "EMA RSI Risk Guard"))
    if strategy:
        return strategy

    strategy = Strategy(
        name="EMA RSI Risk Guard",
        description="Rule-based starter strategy using EMA trend, RSI, and basic risk constraints.",
        timeframe="15m",
        status="active",
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    return strategy


def ensure_default_risk_settings(db: Session) -> RiskSetting:
    settings = db.scalar(select(RiskSetting).where(RiskSetting.name == "Default Paper Risk"))
    if settings:
        return settings

    settings = RiskSetting(
        name="Default Paper Risk",
        max_risk_per_trade=0.01,
        max_daily_loss=0.03,
        max_open_trades=3,
        max_symbol_exposure=0.2,
        status="active",
    )
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def seed_defaults(db: Session) -> None:
    for payload in DEFAULT_SYMBOLS:
        create_symbol(db, payload)

    ensure_default_strategy(db)
    ensure_default_risk_settings(db)

    for symbol in db.scalars(select(Symbol)).all():
        existing_count = db.scalar(
            select(MarketCandle).where(MarketCandle.symbol_id == symbol.id, MarketCandle.timeframe == "15m").limit(1)
        )
        if not existing_count:
            seed_demo_candles(db, symbol)


def seed_demo_candles(db: Session, symbol: Symbol) -> None:
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    base_price = 65000.0 if symbol.symbol.startswith("BTC") else 3200.0
    candles: list[MarketCandle] = []

    for index in range(240):
        opened_at = now - timedelta(minutes=15 * (239 - index))
        trend = index * (base_price * 0.00035)
        wave = ((index % 12) - 6) * (base_price * 0.00022)
        close = base_price + trend + wave
        open_price = close - (base_price * 0.00018)
        high = close + (base_price * 0.00042)
        low = close - (base_price * 0.0005)
        volume = 1000 + (index % 20) * 35
        candles.append(
            MarketCandle(
                symbol_id=symbol.id,
                timeframe="15m",
                opened_at=opened_at,
                open=round(open_price, 4),
                high=round(high, 4),
                low=round(low, 4),
                close=round(close, 4),
                volume=round(volume, 4),
            )
        )

    db.add_all(candles)
    db.commit()

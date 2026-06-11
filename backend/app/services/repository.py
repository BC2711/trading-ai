from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MarketCandle, RiskSetting, Strategy, Symbol
from app.schemas.trading import RiskSettingUpdate, StrategyCreate, StrategyUpdate, SymbolCreate
from app.services.admin import ensure_rbac_defaults
from app.services.audit import record_event


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

    strategy = db.scalar(select(Strategy).order_by(Strategy.id).limit(1))
    if strategy:
        return strategy

    strategy = Strategy(
        name="EMA RSI Risk Guard",
        description="Rule-based starter strategy using EMA trend, RSI, and basic risk constraints.",
        timeframe="15m",
        status="active",
        enabled=True,
        parameters={"fast_window": 9, "slow_window": 21, "rsi_period": 14},
        performance={},
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    return strategy


def ensure_default_risk_settings(db: Session) -> RiskSetting:
    settings = db.scalar(select(RiskSetting).where(RiskSetting.name == "Default Paper Risk"))
    if settings:
        return settings

    settings = db.scalar(select(RiskSetting).order_by(RiskSetting.id).limit(1))
    if settings:
        return settings

    settings = RiskSetting(
        name="Default Paper Risk",
        max_risk_per_trade=0.01,
        max_daily_loss=0.03,
        max_weekly_loss=0.08,
        max_drawdown=0.15,
        max_open_trades=3,
        max_symbol_exposure=0.2,
        max_leverage=1.0,
        max_consecutive_losses=3,
        emergency_stop=False,
        live_trading_enabled=False,
        status="active",
    )
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def list_strategies(db: Session) -> list[Strategy]:
    seed_defaults(db)
    return list(db.scalars(select(Strategy).order_by(Strategy.created_at.desc())).all())


def create_strategy(db: Session, payload: StrategyCreate) -> Strategy:
    strategy = Strategy(
        name=payload.name,
        description=payload.description,
        timeframe=payload.timeframe,
        status=payload.status,
        parameters=payload.parameters,
        enabled=payload.enabled,
        performance={},
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    record_event(
        db,
        event_type="strategy.created",
        entity_type="strategy",
        entity_id=strategy.id,
        message=f"Created strategy {strategy.name}.",
        metadata={"timeframe": strategy.timeframe, "enabled": strategy.enabled},
        commit=True,
    )
    return strategy


def update_strategy(db: Session, strategy_id: int, payload: StrategyUpdate) -> Strategy | None:
    strategy = db.get(Strategy, strategy_id)
    if not strategy:
        return None

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if value is not None:
            setattr(strategy, field, value)

    db.commit()
    db.refresh(strategy)
    record_event(
        db,
        event_type="settings.strategy.updated",
        entity_type="strategy",
        entity_id=strategy.id,
        severity="info",
        message=f"Updated strategy settings for {strategy.name}.",
        metadata={"changed_fields": sorted(changes.keys())},
        commit=True,
    )
    return strategy


def delete_strategy(db: Session, strategy_id: int) -> bool:
    strategy = db.get(Strategy, strategy_id)
    if strategy is None:
        return False
    db.delete(strategy)
    db.commit()
    return True


def update_risk_settings(db: Session, risk_setting_id: int, payload: RiskSettingUpdate) -> RiskSetting | None:
    settings = db.get(RiskSetting, risk_setting_id)
    if not settings:
        return None

    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if value is not None:
            setattr(settings, field, value)

    db.commit()
    db.refresh(settings)
    record_event(
        db,
        event_type="settings.risk.updated",
        entity_type="risk_setting",
        entity_id=settings.id,
        severity="info",
        message=f"Updated risk settings for {settings.name}.",
        metadata={"changed_fields": sorted(changes.keys())},
        commit=True,
    )
    return settings


def seed_defaults(db: Session) -> None:
    ensure_rbac_defaults(db)

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

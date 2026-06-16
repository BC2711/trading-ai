from collections.abc import Iterator
from datetime import timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base
from app.models import PaperPosition
from app.models.trading import utc_now
from app.schemas.paper_trading import PaperTradingOrderCreate
from app.schemas.risk import RiskTradeValidationRequest
from app.schemas.trading import PaperOrderRequest
from app.services.execution.paper import create_paper_order
from app.services.paper_trading import PaperTradingService
from app.services.repository import ensure_default_risk_settings, get_symbol, seed_defaults
from app.services.risk import validate_trade_request


@pytest.fixture()
def db() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    with TestingSessionLocal() as session:
        seed_defaults(session)
        yield session
    Base.metadata.drop_all(engine)


def test_risk_validation_enforces_max_daily_loss(db: Session) -> None:
    configure_risk(db, max_daily_loss=0.01, max_weekly_loss=1.0, max_drawdown=1.0)
    add_closed_position(db, realized_pnl=-150.0)

    result = validate_default_trade(db)

    assert result.approved is False
    assert "Daily loss limit reached" in result.message


def test_risk_validation_enforces_max_weekly_loss(db: Session) -> None:
    configure_risk(db, max_daily_loss=1.0, max_weekly_loss=0.01, max_drawdown=1.0)
    add_closed_position(db, realized_pnl=-150.0, days_ago=3)

    result = validate_default_trade(db)

    assert result.approved is False
    assert "Weekly loss limit reached" in result.message


def test_risk_validation_enforces_max_open_trades(db: Session) -> None:
    configure_risk(db, max_open_trades=1)
    add_open_position(db, symbol="ETHUSDT")

    result = validate_default_trade(db)

    assert result.approved is False
    assert "Max open trades reached" in result.message


def test_risk_validation_enforces_max_symbol_exposure(db: Session) -> None:
    configure_risk(db, max_symbol_exposure=0.005)

    result = validate_default_trade(db)

    assert result.approved is False
    assert "Symbol exposure would exceed" in result.message


def test_risk_validation_enforces_max_drawdown(db: Session) -> None:
    configure_risk(max_daily_loss=1.0, max_weekly_loss=1.0, max_drawdown=0.01, db=db)
    add_closed_position(db, realized_pnl=-150.0, days_ago=10)

    result = validate_default_trade(db)

    assert result.approved is False
    assert "Max drawdown limit reached" in result.message


def test_risk_validation_enforces_emergency_stop(db: Session) -> None:
    configure_risk(db, emergency_stop=True)

    result = validate_default_trade(db)

    assert result.approved is False
    assert "Emergency stop is enabled" in result.message


def test_live_trading_is_disabled_by_default(db: Session) -> None:
    settings = ensure_default_risk_settings(db)

    result = validate_default_trade(db, execution_mode="live")

    assert settings.live_trading_enabled is False
    assert result.approved is False
    assert "Live trading is disabled" in result.message


def test_paper_trading_order_is_risk_validated_before_execution(db: Session) -> None:
    configure_risk(db, max_risk_per_trade=1.0, max_symbol_exposure=0.001)

    order = PaperTradingService(db).create_order(
        PaperTradingOrderCreate(symbol="BTCUSDT", side="buy", order_type="market", quantity=0.01)
    )
    open_positions = db.scalars(select(PaperPosition).where(PaperPosition.status == "open")).all()

    assert order.status == "rejected"
    assert order.risk_status == "blocked"
    assert "Symbol exposure would exceed" in order.risk_message
    assert len(open_positions) == 0


def test_legacy_paper_order_is_risk_validated_before_execution(db: Session) -> None:
    configure_risk(db, emergency_stop=True)

    order = create_paper_order(
        db,
        PaperOrderRequest(symbol="BTCUSDT", side="buy", order_type="market", quantity=0.001),
    )
    open_positions = db.scalars(select(PaperPosition).where(PaperPosition.status == "open")).all()

    assert order.status == "rejected"
    assert order.risk_status == "blocked"
    assert "Emergency stop is enabled" in order.risk_message
    assert len(open_positions) == 0


def configure_risk(db: Session, **changes) -> None:
    settings = ensure_default_risk_settings(db)
    for field, value in changes.items():
        setattr(settings, field, value)
    db.commit()


def validate_default_trade(db: Session, **overrides):
    payload = {
        "symbol": "BTCUSDT",
        "side": "buy",
        "price": 65000.0,
        "quantity": 0.001,
        "stop_loss": 64900.0,
        "take_profit": 67000.0,
        "leverage": 1.0,
        "execution_mode": "paper",
    }
    payload.update(overrides)
    return validate_trade_request(db, RiskTradeValidationRequest(**payload))


def add_closed_position(db: Session, *, realized_pnl: float, days_ago: int = 0) -> None:
    timestamp = utc_now() - timedelta(days=days_ago)
    symbol = get_symbol(db, "BTCUSDT")
    assert symbol is not None
    db.add(
        PaperPosition(
            symbol_id=symbol.id,
            side="long",
            quantity=0.001,
            avg_entry_price=65000.0,
            mark_price=64000.0,
            unrealized_pnl=0.0,
            realized_pnl=realized_pnl,
            status="closed",
            created_at=timestamp,
            updated_at=timestamp,
            closed_at=timestamp,
        )
    )
    db.commit()


def add_open_position(db: Session, *, symbol: str) -> None:
    symbol_model = get_symbol(db, symbol)
    assert symbol_model is not None
    db.add(
        PaperPosition(
            symbol_id=symbol_model.id,
            side="long",
            quantity=0.001,
            avg_entry_price=3200.0,
            mark_price=3200.0,
            unrealized_pnl=0.0,
            realized_pnl=0.0,
            status="open",
        )
    )
    db.commit()

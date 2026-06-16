from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.session import Base
from app.models import PaperOrder, Signal
from app.models.trading import utc_now
from app.services.automation import run_automated_trading
from app.services.repository import ensure_default_strategy, get_symbol, seed_defaults


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


@pytest.fixture(autouse=True)
def reset_automation_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "automated_trading_enabled", False)
    monkeypatch.setattr(settings, "automated_trading_execution_mode", "paper")
    monkeypatch.setattr(settings, "automated_trading_live_enabled", False)
    monkeypatch.setattr(settings, "automated_trading_min_confidence", 0.7)
    monkeypatch.setattr(settings, "automated_trading_max_orders_per_run", 3)
    monkeypatch.setattr(settings, "automated_trading_order_notional_usd", 50.0)
    monkeypatch.setattr(settings, "automated_trading_cooldown_seconds", 300)
    monkeypatch.setattr(settings, "automated_trading_max_signal_age_minutes", 30)
    monkeypatch.setattr(settings, "automated_trading_one_position_per_symbol", True)
    monkeypatch.setattr(settings, "automated_trading_require_strategy_enabled", True)


def test_automated_trading_is_disabled_by_default(db: Session) -> None:
    add_signal(db)

    result = run_automated_trading(db)

    assert result.enabled is False
    assert result.executed_orders == 0
    assert db.scalar(select(PaperOrder.id)) is None


def test_automated_trading_executes_eligible_paper_signal(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "automated_trading_enabled", True)
    signal = add_signal(db)

    result = run_automated_trading(db)
    order = db.scalar(select(PaperOrder).where(PaperOrder.signal_id == signal.id))

    assert result.enabled is True
    assert result.executed_orders == 1
    assert result.decisions[0].status == "executed"
    assert order is not None
    assert order.status == "filled"
    assert order.risk_status == "approved"


def test_automated_trading_does_not_reuse_signal(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "automated_trading_enabled", True)
    signal = add_signal(db)

    first = run_automated_trading(db)
    second = run_automated_trading(db)
    orders = db.scalars(select(PaperOrder).where(PaperOrder.signal_id == signal.id)).all()

    assert first.executed_orders == 1
    assert second.executed_orders == 0
    assert second.decisions[0].status == "skipped"
    assert "already consumed" in second.decisions[0].reason
    assert len(orders) == 1


def test_automated_live_trading_requires_extra_gate(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "automated_trading_enabled", True)
    monkeypatch.setattr(settings, "automated_trading_execution_mode", "live")
    add_signal(db)

    result = run_automated_trading(db)

    assert result.executed_orders == 0
    assert result.decisions[0].status == "skipped"
    assert "Automated live trading is disabled" in result.decisions[0].reason


def add_signal(db: Session, *, direction: str = "buy", confidence: float = 0.9) -> Signal:
    symbol = get_symbol(db, "BTCUSDT")
    strategy = ensure_default_strategy(db)
    assert symbol is not None
    signal = Signal(
        symbol_id=symbol.id,
        strategy_id=strategy.id,
        direction=direction,
        confidence=confidence,
        timeframe="15m",
        reason="Test automation signal",
        status="active",
        created_at=utc_now(),
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal

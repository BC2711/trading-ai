from datetime import datetime, timezone

from sqlalchemy import Boolean, JSON, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Symbol(Base):
    __tablename__ = "symbols"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    base_asset: Mapped[str] = mapped_column(String(16))
    quote_asset: Mapped[str] = mapped_column(String(16))
    market: Mapped[str] = mapped_column(String(24), default="crypto")
    exchange: Mapped[str] = mapped_column(String(32), default="binance_testnet")
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    candles: Mapped[list["MarketCandle"]] = relationship(back_populates="symbol_ref")
    signals: Mapped[list["Signal"]] = relationship(back_populates="symbol_ref")
    orders: Mapped[list["PaperOrder"]] = relationship(back_populates="symbol_ref")
    positions: Mapped[list["PaperPosition"]] = relationship(back_populates="symbol_ref")


class MarketCandle(Base):
    __tablename__ = "market_candles"
    __table_args__ = (
        UniqueConstraint("symbol_id", "timeframe", "opened_at", name="uq_market_candle_symbol_timeframe_opened"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id", ondelete="CASCADE"), index=True)
    timeframe: Mapped[str] = mapped_column(String(8), index=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    symbol_ref: Mapped[Symbol] = relationship(back_populates="candles")


class Strategy(Base):
    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(String(500), default="")
    timeframe: Mapped[str] = mapped_column(String(8), default="15m")
    status: Mapped[str] = mapped_column(String(16), default="draft")
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    performance: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    signals: Mapped[list["Signal"]] = relationship(back_populates="strategy_ref")
    backtest_runs: Mapped[list["BacktestRun"]] = relationship(back_populates="strategy_ref")


class RiskSetting(Base):
    __tablename__ = "risk_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    max_risk_per_trade: Mapped[float] = mapped_column(Float, default=0.01)
    max_daily_loss: Mapped[float] = mapped_column(Float, default=0.03)
    max_open_trades: Mapped[int] = mapped_column(Integer, default=3)
    max_symbol_exposure: Mapped[float] = mapped_column(Float, default=0.2)
    max_consecutive_losses: Mapped[int] = mapped_column(Integer, default=3)
    emergency_stop: Mapped[bool] = mapped_column(Boolean, default=False)
    live_trading_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id", ondelete="CASCADE"), index=True)
    strategy_id: Mapped[int | None] = mapped_column(ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True)
    direction: Mapped[str] = mapped_column(String(16), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    timeframe: Mapped[str] = mapped_column(String(8), default="15m")
    reason: Mapped[str] = mapped_column(String(500), default="")
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    symbol_ref: Mapped[Symbol] = relationship(back_populates="signals")
    strategy_ref: Mapped[Strategy | None] = relationship(back_populates="signals")
    ai_analyses: Mapped[list["AIAnalysisRecord"]] = relationship(back_populates="signal_ref")
    paper_orders: Mapped[list["PaperOrder"]] = relationship(back_populates="signal_ref")


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id", ondelete="CASCADE"), index=True)
    strategy_id: Mapped[int | None] = mapped_column(ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True)
    timeframe: Mapped[str] = mapped_column(String(8), default="15m")
    initial_balance: Mapped[float] = mapped_column(Float, default=10000.0)
    ending_balance: Mapped[float] = mapped_column(Float, default=10000.0)
    total_return: Mapped[float] = mapped_column(Float, default=0.0)
    win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    max_drawdown: Mapped[float] = mapped_column(Float, default=0.0)
    fees: Mapped[float] = mapped_column(Float, default=0.0)
    slippage: Mapped[float] = mapped_column(Float, default=0.0)
    spread: Mapped[float] = mapped_column(Float, default=0.0)
    profit_factor: Mapped[float] = mapped_column(Float, default=0.0)
    sharpe_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    equity_curve: Mapped[list[dict]] = mapped_column(JSON, default=list)
    trades_count: Mapped[int] = mapped_column(Integer, default=0)
    winning_trades: Mapped[int] = mapped_column(Integer, default=0)
    losing_trades: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="completed")
    summary: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    symbol_ref: Mapped[Symbol] = relationship()
    strategy_ref: Mapped[Strategy | None] = relationship(back_populates="backtest_runs")


class AIAnalysisRecord(Base):
    __tablename__ = "ai_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    signal_id: Mapped[int | None] = mapped_column(ForeignKey("signals.id", ondelete="SET NULL"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(48), default="rules-fallback")
    symbol: Mapped[str] = mapped_column(String(24), index=True)
    timeframe: Mapped[str] = mapped_column(String(8), index=True)
    direction: Mapped[str] = mapped_column(String(16), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    explanation: Mapped[str] = mapped_column(String(1200))
    reasoning: Mapped[list[str]] = mapped_column(JSON)
    risk_notes: Mapped[list[str]] = mapped_column(JSON)
    suggested_action: Mapped[str] = mapped_column(String(500))
    indicators: Mapped[dict[str, float]] = mapped_column(JSON)
    backtest_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    signal_ref: Mapped[Signal | None] = relationship(back_populates="ai_analyses")
    paper_orders: Mapped[list["PaperOrder"]] = relationship(back_populates="ai_analysis_ref")


class PaperOrder(Base):
    __tablename__ = "paper_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id", ondelete="CASCADE"), index=True)
    signal_id: Mapped[int | None] = mapped_column(ForeignKey("signals.id", ondelete="SET NULL"), nullable=True, index=True)
    ai_analysis_id: Mapped[int | None] = mapped_column(ForeignKey("ai_analyses.id", ondelete="SET NULL"), nullable=True, index=True)
    side: Mapped[str] = mapped_column(String(12), index=True)
    order_type: Mapped[str] = mapped_column(String(16), default="market")
    quantity: Mapped[float] = mapped_column(Float)
    requested_price: Mapped[float] = mapped_column(Float)
    fill_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="filled", index=True)
    risk_status: Mapped[str] = mapped_column(String(16), default="approved")
    risk_message: Mapped[str] = mapped_column(String(500), default="")
    execution_mode: Mapped[str] = mapped_column(String(16), default="paper")
    exchange_order_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    symbol_ref: Mapped[Symbol] = relationship(back_populates="orders")
    signal_ref: Mapped[Signal | None] = relationship(back_populates="paper_orders")
    ai_analysis_ref: Mapped[AIAnalysisRecord | None] = relationship(back_populates="paper_orders")


class PaperPosition(Base):
    __tablename__ = "paper_positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol_id: Mapped[int] = mapped_column(ForeignKey("symbols.id", ondelete="CASCADE"), index=True)
    side: Mapped[str] = mapped_column(String(12), index=True)
    quantity: Mapped[float] = mapped_column(Float)
    avg_entry_price: Mapped[float] = mapped_column(Float)
    mark_price: Mapped[float] = mapped_column(Float)
    unrealized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    symbol_ref: Mapped[Symbol] = relationship(back_populates="positions")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    severity: Mapped[str] = mapped_column(String(16), default="info", index=True)
    message: Mapped[str] = mapped_column(String(500))
    event_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    hashed_password: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(24), default="trader", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class ApiCredential(Base):
    __tablename__ = "api_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    exchange: Mapped[str] = mapped_column(String(48), index=True)
    api_key: Mapped[str] = mapped_column(String(255))
    encrypted_api_secret: Mapped[str] = mapped_column(String(1000))
    mode: Mapped[str] = mapped_column(String(16), default="paper", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class AIModelMetadata(Base):
    __tablename__ = "ai_model_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    symbol: Mapped[str] = mapped_column(String(24), index=True)
    timeframe: Mapped[str] = mapped_column(String(8), default="15m")
    model_type: Mapped[str] = mapped_column(String(64), default="random_forest")
    model_path: Mapped[str] = mapped_column(String(500))
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(24), default="trained", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(180))
    message: Mapped[str] = mapped_column(String(800))
    severity: Mapped[str] = mapped_column(String(16), default="info", index=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class SystemLog(Base):
    __tablename__ = "system_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    level: Mapped[str] = mapped_column(String(16), default="info", index=True)
    source: Mapped[str] = mapped_column(String(80), index=True)
    message: Mapped[str] = mapped_column(String(1000))
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

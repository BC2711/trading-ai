from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import FeatureCalculationLog, FeatureSet, MarketCandle, MarketFeature
from app.schemas.features import FeatureCalculationRequest, FeatureCalculationResponse, FeatureSetRead, MarketFeatureRead
from app.services.ai.features.calculator import FEATURE_COLUMNS, FeatureCalculator, FeatureDataset
from app.services.repository import get_symbol, list_candles, seed_defaults


class FeatureService:
    def __init__(self, db: Session | None = None) -> None:
        self.db = db
        self.calculator = FeatureCalculator()

    def build_dataset(self, candles: list[MarketCandle]) -> FeatureDataset:
        return self.calculator.build_dataset(candles)

    def calculate_latest(self, candles: list[MarketCandle]) -> dict[str, float]:
        return self.calculator.latest_feature_map(candles)

    def list_features(self, limit: int = 100, symbol: str | None = None) -> list[MarketFeatureRead]:
        db = self.require_db()
        statement = (
            select(MarketFeature)
            .options(selectinload(MarketFeature.symbol_ref), selectinload(MarketFeature.feature_set_ref))
            .order_by(MarketFeature.calculated_at.desc())
            .limit(limit)
        )
        if symbol:
            symbol_model = get_symbol(db, symbol)
            if symbol_model is None:
                return []
            statement = (
                select(MarketFeature)
                .where(MarketFeature.symbol_id == symbol_model.id)
                .options(selectinload(MarketFeature.symbol_ref), selectinload(MarketFeature.feature_set_ref))
                .order_by(MarketFeature.calculated_at.desc())
                .limit(limit)
            )
        return [market_feature_to_schema(feature) for feature in db.scalars(statement).all()]

    def list_feature_sets(self) -> list[FeatureSetRead]:
        db = self.require_db()
        self.ensure_default_feature_set()
        sets = db.scalars(select(FeatureSet).order_by(FeatureSet.name)).all()
        return [FeatureSetRead.model_validate(item) for item in sets]

    def calculate(self, payload: FeatureCalculationRequest) -> FeatureCalculationResponse:
        db = self.require_db()
        seed_defaults(db)
        symbol = get_symbol(db, payload.symbol)
        if symbol is None:
            raise ValueError(f"Symbol {payload.symbol.upper()} is not configured")

        feature_set = self.ensure_default_feature_set(payload.feature_set)
        candles = list_candles(db, symbol.symbol, payload.timeframe, payload.lookback)
        frame = self.calculator.calculate_frame(candles)
        rows = frame.tail(payload.persist_last)
        stored_features = []

        for _, row in rows.iterrows():
            values = {name: round(float(row[name]), 8) for name in FEATURE_COLUMNS}
            opened_at = row["opened_at"].to_pydatetime() if hasattr(row["opened_at"], "to_pydatetime") else row["opened_at"]
            feature = db.scalar(
                select(MarketFeature).where(
                    MarketFeature.symbol_id == symbol.id,
                    MarketFeature.feature_set_id == feature_set.id,
                    MarketFeature.timeframe == payload.timeframe,
                    MarketFeature.candle_opened_at == opened_at,
                )
            )
            if feature:
                feature.feature_values = values
                feature.source = "calculated"
            else:
                feature = MarketFeature(
                    symbol_id=symbol.id,
                    feature_set_id=feature_set.id,
                    timeframe=payload.timeframe,
                    source="calculated",
                    candle_opened_at=opened_at,
                    feature_values=values,
                )
                db.add(feature)
            stored_features.append(feature)

        log = FeatureCalculationLog(
            symbol_id=symbol.id,
            feature_set_id=feature_set.id,
            timeframe=payload.timeframe,
            lookback=payload.lookback,
            rows_calculated=len(stored_features),
            status="completed",
            message=f"Calculated {len(stored_features)} feature rows for {symbol.symbol}.",
        )
        db.add(log)
        db.commit()
        for feature in stored_features:
            db.refresh(feature)
        db.refresh(log)

        latest = stored_features[-1] if stored_features else None
        return FeatureCalculationResponse(
            symbol=symbol.symbol,
            timeframe=payload.timeframe,
            feature_set=FeatureSetRead.model_validate(feature_set),
            rows_calculated=len(stored_features),
            latest=market_feature_to_schema(latest) if latest else None,
            log_id=log.id,
        )

    def ensure_default_feature_set(self, name: str = "default-ai-trading") -> FeatureSet:
        db = self.require_db()
        existing = db.scalar(select(FeatureSet).where(FeatureSet.name == name))
        if existing:
            return existing
        feature_set = FeatureSet(
            name=name,
            description="Default reusable feature set for AI training, prediction, strategy builder, scanners, and backtesting.",
            features=FEATURE_COLUMNS,
            version=1,
            status="active",
        )
        db.add(feature_set)
        db.commit()
        db.refresh(feature_set)
        return feature_set

    def require_db(self) -> Session:
        if self.db is None:
            raise RuntimeError("FeatureService requires a database session for store operations")
        return self.db


def market_feature_to_schema(feature: MarketFeature) -> MarketFeatureRead:
    return MarketFeatureRead(
        id=feature.id,
        symbol=feature.symbol_ref.symbol,
        timeframe=feature.timeframe,
        feature_set=feature.feature_set_ref.name,
        candle_opened_at=feature.candle_opened_at,
        values=feature.feature_values,
        source=feature.source,
        calculated_at=feature.calculated_at,
    )

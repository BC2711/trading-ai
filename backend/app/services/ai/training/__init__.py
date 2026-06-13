from sqlalchemy.orm import Session

from app.models import AIModelMetadata, MarketCandle
from app.services.ai.features import FeatureService
from app.services.ai.training_service import TrainingService


def build_dataset(candles: list[MarketCandle]) -> tuple[list[list[float]], list[int]]:
    dataset = FeatureService().build_dataset(candles)
    return dataset.features, dataset.labels


def train_model(
    db: Session,
    *,
    name: str,
    symbol: str,
    timeframe: str,
    lookback: int,
    model_type: str = "random_forest",
    training_params: dict | None = None,
    selected_features: list[str] | None = None,
) -> AIModelMetadata:
    return TrainingService(db).train(
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        lookback=lookback,
        model_type=model_type,
        training_params=training_params,
        selected_features=selected_features,
    )


def retrain_model(
    db: Session,
    model_id: int,
    *,
    lookback: int | None = None,
    training_params: dict | None = None,
) -> AIModelMetadata:
    return TrainingService(db).retrain(model_id, lookback=lookback, training_params=training_params)


def deploy_model(db: Session, model_id: int) -> AIModelMetadata:
    return TrainingService(db).deploy(model_id)


def approve_model(db: Session, model_id: int, *, approved_by: str | None = None, notes: str | None = None) -> AIModelMetadata:
    return TrainingService(db).approve(model_id, approved_by=approved_by, notes=notes)


def reject_model(db: Session, model_id: int, *, approved_by: str | None = None, notes: str | None = None) -> AIModelMetadata:
    return TrainingService(db).reject(model_id, approved_by=approved_by, notes=notes)


def disable_model(db: Session, model_id: int) -> AIModelMetadata:
    return TrainingService(db).disable(model_id)


def compare_models(db: Session, model_ids: list[int]) -> list[dict]:
    return TrainingService(db).compare(model_ids)


def predict(db: Session, model_id: int) -> dict:
    return TrainingService(db).predict(model_id)


def set_retrain_schedule(db: Session, model_id: int, interval_hours: int | None) -> AIModelMetadata:
    return TrainingService(db).set_retrain_schedule(model_id, interval_hours)


def check_model_drift(db: Session, model_id: int) -> AIModelMetadata:
    return TrainingService(db).check_drift(model_id)


def retrain_due_models(db: Session, limit: int = 10) -> list[AIModelMetadata]:
    return TrainingService(db).retrain_due_models(limit=limit)

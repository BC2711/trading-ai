from sqlalchemy.orm import Session

from app.services.ai.registry import ModelRegistryService
from app.services.ai.training_service import TrainingService


class PredictionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.registry = ModelRegistryService(db)
        self.training_service = TrainingService(db)

    def predict(
        self,
        *,
        symbol: str,
        timeframe: str | None = None,
        model_id: int | None = None,
        model_type: str | None = None,
    ) -> dict:
        if model_id is not None:
            return self.training_service.predict(model_id)

        model = self.registry.active_model(symbol, timeframe=timeframe, model_type=model_type)
        if model is None:
            raise ValueError("No active model found for prediction")
        return self.training_service.predict(model.id)

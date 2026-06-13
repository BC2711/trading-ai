from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AIModelMetadata
from app.services.ai.evaluation import evaluation_for_model
from app.services.ai.training_service import TrainingService


class ModelRegistryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.training_service = TrainingService(db)

    def list_models(self) -> list[AIModelMetadata]:
        return list(self.db.scalars(select(AIModelMetadata).order_by(AIModelMetadata.created_at.desc())).all())

    def get_model(self, model_id: int) -> AIModelMetadata:
        return self.training_service.get_model(model_id)

    def activate(self, model_id: int) -> AIModelMetadata:
        return self.training_service.deploy(model_id)

    def approve(self, model_id: int, *, approved_by: str | None = None, notes: str | None = None) -> AIModelMetadata:
        return self.training_service.approve(model_id, approved_by=approved_by, notes=notes)

    def reject(self, model_id: int, *, reviewed_by: str | None = None, notes: str | None = None) -> AIModelMetadata:
        return self.training_service.reject(model_id, approved_by=reviewed_by, notes=notes)

    def active_model(self, symbol: str, timeframe: str | None = None, model_type: str | None = None) -> AIModelMetadata | None:
        statement = select(AIModelMetadata).where(AIModelMetadata.symbol == symbol.upper(), AIModelMetadata.deployed.is_(True))
        if timeframe:
            statement = statement.where(AIModelMetadata.timeframe == timeframe)
        if model_type:
            statement = statement.where(AIModelMetadata.model_type == model_type)
        return self.db.scalars(statement.order_by(AIModelMetadata.champion.desc(), AIModelMetadata.created_at.desc()).limit(1)).first()

    def evaluation(self, model_id: int) -> dict:
        return evaluation_for_model(self.get_model(model_id))

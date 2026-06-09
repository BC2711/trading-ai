from sqlalchemy import select, update
from sqlalchemy.orm import Session
from sklearn.model_selection import train_test_split

from app.models import AIModelMetadata
from app.services.ai.evaluation import ModelEvaluationService
from app.services.ai.features import FeatureService
from app.services.ai.models import ModelService, normalize_model_type
from app.services.audit import record_event
from app.services.repository import get_symbol, list_candles, seed_defaults


class TrainingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.feature_service = FeatureService()
        self.model_service = ModelService()
        self.evaluation_service = ModelEvaluationService()

    def train(
        self,
        *,
        name: str,
        symbol: str,
        timeframe: str,
        lookback: int,
        model_type: str = "random_forest",
        training_params: dict | None = None,
        parent_model_id: int | None = None,
    ) -> AIModelMetadata:
        seed_defaults(self.db)
        symbol_model = get_symbol(self.db, symbol)
        if symbol_model is None:
            raise ValueError(f"Symbol {symbol.upper()} is not configured")

        normalized_type = normalize_model_type(model_type)
        candles = list_candles(self.db, symbol_model.symbol, timeframe, lookback)
        dataset = self.feature_service.build_dataset(candles)
        if len(set(dataset.labels)) < 2:
            raise ValueError("Not enough varied candle history to train a model")

        train_features, test_features, train_labels, test_labels = train_test_split(
            dataset.features,
            dataset.labels,
            test_size=0.25,
            shuffle=False,
        )
        model, resolved_params = self.model_service.create_model(normalized_type, training_params)
        model.fit(train_features, train_labels)
        predictions = [int(value) for value in model.predict(test_features)]
        probabilities = positive_class_probabilities(model, test_features)
        metrics = self.evaluation_service.evaluate(test_labels, predictions, probabilities)
        metrics.update(
            {
                "feature_rows": dataset.rows,
                "feature_count": len(dataset.feature_names),
                "model_type": normalized_type,
            }
        )

        version = self.next_version(name, symbol_model.symbol, timeframe, normalized_type)
        model_path = self.model_service.save_model(
            model,
            name=name,
            symbol=symbol_model.symbol,
            timeframe=timeframe,
            model_type=normalized_type,
            version=version,
        )
        metadata = AIModelMetadata(
            name=name,
            symbol=symbol_model.symbol,
            timeframe=timeframe,
            model_type=normalized_type,
            version=version,
            parent_model_id=parent_model_id,
            model_path=str(model_path),
            metrics=metrics,
            feature_names=dataset.feature_names,
            training_params=resolved_params,
            target="next_close_direction",
            deployed=False,
            status="trained",
        )
        self.db.add(metadata)
        self.db.commit()
        self.db.refresh(metadata)
        record_event(
            self.db,
            event_type="ai_model.trained",
            entity_type="ai_model",
            entity_id=metadata.id,
            message=f"Trained {metadata.model_type} model {metadata.name} v{metadata.version} for {metadata.symbol}.",
            metadata=metrics,
            commit=True,
        )
        return metadata

    def retrain(self, model_id: int, *, lookback: int | None = None, training_params: dict | None = None) -> AIModelMetadata:
        existing = self.get_model(model_id)
        params = dict(existing.training_params or {})
        params.pop("runtime_adapter", None)
        if training_params:
            params.update(training_params)
        return self.train(
            name=existing.name,
            symbol=existing.symbol,
            timeframe=existing.timeframe,
            lookback=lookback or int((existing.metrics or {}).get("feature_rows", 240) + 80),
            model_type=existing.model_type,
            training_params=params,
            parent_model_id=existing.id,
        )

    def deploy(self, model_id: int) -> AIModelMetadata:
        model = self.get_model(model_id)
        self.db.execute(
            update(AIModelMetadata)
            .where(
                AIModelMetadata.symbol == model.symbol,
                AIModelMetadata.timeframe == model.timeframe,
                AIModelMetadata.model_type == model.model_type,
            )
            .values(deployed=False)
        )
        model.deployed = True
        model.status = "deployed"
        self.db.commit()
        self.db.refresh(model)
        record_event(
            self.db,
            event_type="ai_model.deployed",
            entity_type="ai_model",
            entity_id=model.id,
            message=f"Deployed model {model.name} v{model.version} for {model.symbol}.",
            metadata={"model_type": model.model_type, "version": model.version},
            commit=True,
        )
        return model

    def disable(self, model_id: int) -> AIModelMetadata:
        model = self.get_model(model_id)
        model.deployed = False
        model.status = "disabled"
        self.db.commit()
        self.db.refresh(model)
        record_event(
            self.db,
            event_type="ai_model.disabled",
            entity_type="ai_model",
            entity_id=model.id,
            message=f"Disabled model {model.name} v{model.version}.",
            metadata={"model_type": model.model_type, "version": model.version},
            commit=True,
        )
        return model

    def compare(self, model_ids: list[int]) -> list[dict]:
        models = [self.get_model(model_id) for model_id in model_ids]
        ranked = sorted(models, key=lambda item: float((item.metrics or {}).get("f1", item.metrics.get("accuracy", 0.0))), reverse=True)
        return [
            {
                "id": model.id,
                "name": model.name,
                "symbol": model.symbol,
                "timeframe": model.timeframe,
                "model_type": model.model_type,
                "version": model.version,
                "status": model.status,
                "deployed": model.deployed,
                "metrics": model.metrics,
                "rank": index + 1,
            }
            for index, model in enumerate(ranked)
        ]

    def predict(self, model_id: int) -> dict:
        metadata = self.get_model(model_id)
        candles = list_candles(self.db, metadata.symbol, metadata.timeframe, 240)
        dataset = self.feature_service.build_dataset(candles)
        model = self.model_service.load_model(metadata.model_path)
        probability = positive_class_probabilities(model, [dataset.latest_features])[0]
        direction = "buy" if probability >= 0.5 else "sell"
        confidence = probability if direction == "buy" else 1 - probability
        return {
            "model_id": metadata.id,
            "symbol": metadata.symbol,
            "direction": direction,
            "confidence": round(float(confidence), 6),
            "features": dataset.latest_feature_map,
        }

    def get_model(self, model_id: int) -> AIModelMetadata:
        model = self.db.get(AIModelMetadata, model_id)
        if model is None:
            raise ValueError("AI model not found")
        return model

    def next_version(self, name: str, symbol: str, timeframe: str, model_type: str) -> int:
        current = self.db.scalars(
            select(AIModelMetadata)
            .where(
                AIModelMetadata.name == name,
                AIModelMetadata.symbol == symbol.upper(),
                AIModelMetadata.timeframe == timeframe,
                AIModelMetadata.model_type == model_type,
            )
            .order_by(AIModelMetadata.version.desc())
            .limit(1)
        ).first()
        return 1 if current is None else current.version + 1


def positive_class_probabilities(model, features: list[list[float]]) -> list[float]:
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(features)
        return [float(row[1]) if len(row) > 1 else float(row[0]) for row in probabilities]
    predictions = model.predict(features)
    return [float(value) for value in predictions]

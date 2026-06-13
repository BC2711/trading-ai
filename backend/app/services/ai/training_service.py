from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session
from sklearn.model_selection import train_test_split

from app.models import AIModelMetadata, Prediction
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
        selected_features: list[str] | None = None,
    ) -> AIModelMetadata:
        seed_defaults(self.db)
        symbol_model = get_symbol(self.db, symbol)
        if symbol_model is None:
            raise ValueError(f"Symbol {symbol.upper()} is not configured")

        normalized_type = normalize_model_type(model_type)
        candles = list_candles(self.db, symbol_model.symbol, timeframe, lookback)
        dataset = self.feature_service.build_dataset(candles, selected_features=selected_features)
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
                "profit_factor": profit_factor_from_predictions(test_labels, predictions),
                "feature_baseline": dataset.latest_feature_map,
            }
        )

        parent_model = self.db.get(AIModelMetadata, parent_model_id) if parent_model_id else None
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
            champion=False,
            approval_status="pending",
            challenger_of_id=parent_model_id,
            lifecycle_metadata={
                "stage": "challenger" if parent_model_id else "candidate",
                "approval_required": True,
                "parent_model_id": parent_model_id,
                "champion_model_id": parent_model.id if parent_model and parent_model.champion else None,
            },
            model_drift=default_drift_state("model"),
            feature_drift=default_drift_state("feature"),
            last_retrained_at=datetime.now(timezone.utc) if parent_model_id else None,
            retrain_interval_hours=parent_model.retrain_interval_hours if parent_model else None,
            next_retrain_at=next_retrain_time(parent_model.retrain_interval_hours) if parent_model and parent_model.retrain_interval_hours else None,
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

    def approve(self, model_id: int, *, approved_by: str | None = None, notes: str | None = None) -> AIModelMetadata:
        model = self.get_model(model_id)
        model.approval_status = "approved"
        model.approved_at = datetime.now(timezone.utc)
        model.approved_by = approved_by
        model.lifecycle_metadata = {
            **(model.lifecycle_metadata or {}),
            "approval_notes": notes,
            "approved_by": approved_by,
            "approved_at": model.approved_at.isoformat(),
        }
        self.db.commit()
        self.db.refresh(model)
        record_event(
            self.db,
            event_type="ai_model.approved",
            entity_type="ai_model",
            entity_id=model.id,
            message=f"Approved model {model.name} v{model.version}.",
            metadata={"approved_by": approved_by, "notes": notes},
            commit=True,
        )
        return model

    def reject(self, model_id: int, *, approved_by: str | None = None, notes: str | None = None) -> AIModelMetadata:
        model = self.get_model(model_id)
        model.approval_status = "rejected"
        model.deployed = False
        model.champion = False
        model.status = "rejected"
        model.lifecycle_metadata = {
            **(model.lifecycle_metadata or {}),
            "rejection_notes": notes,
            "reviewed_by": approved_by,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }
        self.db.commit()
        self.db.refresh(model)
        record_event(
            self.db,
            event_type="ai_model.rejected",
            entity_type="ai_model",
            entity_id=model.id,
            message=f"Rejected model {model.name} v{model.version}.",
            metadata={"reviewed_by": approved_by, "notes": notes},
            commit=True,
        )
        return model

    def deploy(self, model_id: int) -> AIModelMetadata:
        model = self.get_model(model_id)
        if model.approval_status == "rejected":
            raise ValueError("Rejected models cannot be deployed")
        if model.approval_status != "approved":
            self.approve(model.id, approved_by="system", notes="Auto-approved during deployment for backward-compatible deploy endpoint.")
            model = self.get_model(model_id)
        self.db.execute(
            update(AIModelMetadata)
            .where(
                AIModelMetadata.symbol == model.symbol,
                AIModelMetadata.timeframe == model.timeframe,
                AIModelMetadata.model_type == model.model_type,
            )
            .values(deployed=False, champion=False)
        )
        model.deployed = True
        model.champion = True
        model.status = "deployed"
        model.lifecycle_metadata = {
            **(model.lifecycle_metadata or {}),
            "stage": "champion",
            "deployed_at": datetime.now(timezone.utc).isoformat(),
        }
        self.db.commit()
        self.db.refresh(model)
        record_event(
            self.db,
            event_type="ai_model.deployed",
            entity_type="ai_model",
            entity_id=model.id,
            message=f"Deployed model {model.name} v{model.version} for {model.symbol}.",
            metadata={"model_type": model.model_type, "version": model.version, "champion": model.champion},
            commit=True,
        )
        return model

    def disable(self, model_id: int) -> AIModelMetadata:
        model = self.get_model(model_id)
        model.deployed = False
        model.champion = False
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
        champions = {
            (model.symbol, model.timeframe, model.model_type): model
            for model in models
            if model.champion or model.deployed
        }
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
                "champion": model.champion,
                "challenger_of_id": model.challenger_of_id,
                "approval_status": model.approval_status,
                "comparison": comparison_to_champion(model, champions.get((model.symbol, model.timeframe, model.model_type))),
                "metrics": model.metrics,
                "rank": index + 1,
            }
            for index, model in enumerate(ranked)
        ]

    def predict(self, model_id: int) -> dict:
        metadata = self.get_model(model_id)
        candles = list_candles(self.db, metadata.symbol, metadata.timeframe, 240)
        dataset = self.feature_service.build_dataset(candles, selected_features=metadata.feature_names)
        model = self.model_service.load_model(metadata.model_path)
        probability = positive_class_probabilities(model, [dataset.latest_features])[0]
        direction = "buy" if probability >= 0.5 else "sell"
        confidence = probability if direction == "buy" else 1 - probability
        prediction = self.log_prediction(metadata, direction, confidence, dataset.latest_feature_map, probability)
        self.update_drift_state(metadata, dataset.latest_feature_map, confidence)
        return {
            "model_id": metadata.id,
            "prediction_id": prediction.id,
            "symbol": metadata.symbol,
            "direction": direction,
            "confidence": round(float(confidence), 6),
            "features": dataset.latest_feature_map,
        }

    def log_prediction(self, metadata: AIModelMetadata, direction: str, confidence: float, features: dict, probability: float) -> Prediction:
        symbol_model = get_symbol(self.db, metadata.symbol)
        if symbol_model is None:
            raise ValueError(f"Symbol {metadata.symbol} is not configured")
        prediction_time = datetime.now(timezone.utc)
        prediction = Prediction(
            symbol_id=symbol_model.id,
            model_id=metadata.id,
            timeframe=metadata.timeframe,
            prediction_time=prediction_time,
            target=metadata.target,
            horizon="next_candle",
            direction=direction,
            confidence=round(float(confidence), 6),
            predicted_value=round(float(probability), 6),
            features=features,
            prediction_metadata={
                "model_version": metadata.version,
                "model_type": metadata.model_type,
                "approval_status": metadata.approval_status,
                "champion": metadata.champion,
            },
        )
        metadata.last_prediction_at = prediction_time
        self.db.add(prediction)
        self.db.add(metadata)
        self.db.commit()
        self.db.refresh(prediction)
        self.db.refresh(metadata)
        return prediction

    def update_drift_state(self, metadata: AIModelMetadata, features: dict, confidence: float) -> None:
        baseline = ((metadata.metrics or {}).get("feature_baseline") or {}) if isinstance(metadata.metrics, dict) else {}
        feature_checks = []
        for name, current in features.items():
            baseline_value = baseline.get(name)
            if baseline_value in (None, 0):
                continue
            delta_pct = abs(float(current) - float(baseline_value)) / max(abs(float(baseline_value)), 1e-9)
            feature_checks.append({"feature": name, "delta_pct": round(delta_pct, 6), "drifted": delta_pct >= 0.25})
        drifted_features = [item for item in feature_checks if item["drifted"]]
        checked_at = datetime.now(timezone.utc).isoformat()
        metadata.feature_drift = {
            "status": "drifted" if drifted_features else "stable",
            "checked_at": checked_at,
            "threshold_delta_pct": 0.25,
            "drifted_feature_count": len(drifted_features),
            "checks": feature_checks[:25],
        }
        model_status = "watch" if confidence < 0.55 else "stable"
        metadata.model_drift = {
            "status": model_status,
            "checked_at": checked_at,
            "confidence": round(float(confidence), 6),
            "signals": ["low_confidence"] if model_status == "watch" else [],
        }
        self.db.add(metadata)
        self.db.commit()
        self.db.refresh(metadata)

    def set_retrain_schedule(self, model_id: int, interval_hours: int | None) -> AIModelMetadata:
        model = self.get_model(model_id)
        model.retrain_interval_hours = interval_hours
        model.next_retrain_at = next_retrain_time(interval_hours) if interval_hours else None
        model.lifecycle_metadata = {
            **(model.lifecycle_metadata or {}),
            "scheduled_retraining_enabled": bool(interval_hours),
        }
        self.db.commit()
        self.db.refresh(model)
        return model

    def check_drift(self, model_id: int) -> AIModelMetadata:
        model = self.get_model(model_id)
        candles = list_candles(self.db, model.symbol, model.timeframe, 240)
        dataset = self.feature_service.build_dataset(candles, selected_features=model.feature_names)
        last_confidence = 1.0
        if isinstance(model.model_drift, dict):
            last_confidence = float(model.model_drift.get("confidence") or last_confidence)
        self.update_drift_state(model, dataset.latest_feature_map, last_confidence)
        return self.get_model(model_id)

    def retrain_due_models(self, limit: int = 10) -> list[AIModelMetadata]:
        now = datetime.now(timezone.utc)
        due_models = list(
            self.db.scalars(
                select(AIModelMetadata)
                .where(
                    AIModelMetadata.retrain_interval_hours.is_not(None),
                    AIModelMetadata.next_retrain_at.is_not(None),
                    AIModelMetadata.next_retrain_at <= now,
                    AIModelMetadata.status.in_(["deployed", "trained"]),
                )
                .order_by(AIModelMetadata.next_retrain_at.asc())
                .limit(limit)
            ).all()
        )
        retrained = []
        for model in due_models:
            retrained_model = self.retrain(model.id)
            retrained.append(retrained_model)
            model.next_retrain_at = next_retrain_time(model.retrain_interval_hours)
            self.db.add(model)
        if due_models:
            self.db.commit()
        return retrained

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


def profit_factor_from_predictions(labels: list[int], predictions: list[int]) -> float:
    wins = sum(1 for label, prediction in zip(labels, predictions) if label == prediction)
    losses = max(1, len(labels) - wins)
    return round(float(wins / losses), 6)


def default_drift_state(kind: str) -> dict:
    return {
        "status": "pending",
        "kind": kind,
        "checked_at": None,
        "signals": [],
    }


def next_retrain_time(interval_hours: int | None) -> datetime | None:
    if not interval_hours:
        return None
    return datetime.now(timezone.utc) + timedelta(hours=interval_hours)


def metric_value(model: AIModelMetadata, metric: str) -> float:
    metrics = model.metrics or {}
    return float(metrics.get(metric, 0.0) or 0.0)


def comparison_to_champion(model: AIModelMetadata, champion: AIModelMetadata | None) -> dict:
    if champion is None or champion.id == model.id:
        return {"role": "champion" if model.champion else "candidate", "champion_model_id": champion.id if champion else None}
    return {
        "role": "challenger",
        "champion_model_id": champion.id,
        "accuracy_delta": round(metric_value(model, "accuracy") - metric_value(champion, "accuracy"), 6),
        "f1_delta": round(metric_value(model, "f1") - metric_value(champion, "f1"), 6),
        "profit_factor_delta": round(metric_value(model, "profit_factor") - metric_value(champion, "profit_factor"), 6),
    }

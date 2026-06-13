from app.core.celery_app import celery_app
from app.core.config import settings
from app.db.session import SessionLocal
from app.services.ai.training import retrain_due_models
from app.services.market_data.jobs import run_market_data_refresh


@celery_app.task(name="app.workers.tasks.refresh_market_data")
def refresh_market_data(
    symbols: list[str] | None = None,
    timeframe: str | None = None,
    limit: int | None = None,
    regenerate_signals: bool | None = None,
) -> dict:
    with SessionLocal() as db:
        result = run_market_data_refresh(
            db,
            symbols=symbols,
            timeframe=timeframe,
            limit=limit,
            regenerate_signals=regenerate_signals,
        )
    return result.model_dump(mode="json")


@celery_app.task(name="app.workers.tasks.retrain_due_ai_models")
def retrain_due_ai_models(limit: int | None = None) -> dict:
    with SessionLocal() as db:
        models = retrain_due_models(db, limit=limit or settings.ai_retraining_batch_size)
        return {
            "retrained_count": len(models),
            "model_ids": [model.id for model in models],
        }

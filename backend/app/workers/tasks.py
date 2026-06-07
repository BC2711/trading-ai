from app.core.celery_app import celery_app
from app.db.session import SessionLocal
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

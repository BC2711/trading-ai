from app.core.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.refresh_market_data")
def refresh_market_data() -> dict[str, str]:
    return {"status": "queued", "task": "refresh_market_data"}

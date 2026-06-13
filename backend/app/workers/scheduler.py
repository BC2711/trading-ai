import time

from app.core.config import settings
from app.core.scheduler import create_scheduler
from app.workers.tasks import refresh_market_data, retrain_due_ai_models


MARKET_SYNC_JOB_ID = "market-data-sync"
AI_RETRAIN_JOB_ID = "ai-model-retraining"


def scheduled_market_sync() -> None:
    task = refresh_market_data.delay()
    print(f"queued {MARKET_SYNC_JOB_ID} task={task.id}", flush=True)


def scheduled_ai_retraining() -> None:
    task = retrain_due_ai_models.delay()
    print(f"queued {AI_RETRAIN_JOB_ID} task={task.id}", flush=True)


def main() -> None:
    scheduler = create_scheduler()
    scheduler.add_job(
        scheduled_market_sync,
        "interval",
        minutes=settings.market_sync_interval_minutes,
        id=MARKET_SYNC_JOB_ID,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    if settings.ai_retraining_scheduler_enabled:
        scheduler.add_job(
            scheduled_ai_retraining,
            "interval",
            minutes=settings.ai_retraining_check_interval_minutes,
            id=AI_RETRAIN_JOB_ID,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
    scheduled_market_sync()
    scheduler.start()

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


if __name__ == "__main__":
    main()

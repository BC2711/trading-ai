import sentry_sdk
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings


def configure_monitoring(app: FastAPI) -> None:
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.sentry_environment,
            traces_sample_rate=0.1,
        )

    if settings.enable_metrics:
        Instrumentator().instrument(app).expose(app, endpoint="/metrics")

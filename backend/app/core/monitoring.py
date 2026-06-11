import time
from collections import deque
from dataclasses import dataclass
from threading import Lock

import sentry_sdk
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


@dataclass(frozen=True)
class ApiMetricSnapshot:
    requests_total: int
    errors_total: int
    recent_request_count: int
    recent_error_count: int
    average_latency_ms: float
    p95_latency_ms: float
    error_rate: float


class ApiMetricsRecorder:
    def __init__(self, window_seconds: int = 300, max_events: int = 5000) -> None:
        self.window_seconds = window_seconds
        self.max_events = max_events
        self._events: deque[tuple[float, float, int]] = deque()
        self._requests_total = 0
        self._errors_total = 0
        self._lock = Lock()

    def record(self, *, duration_ms: float, status_code: int) -> None:
        now = time.time()
        with self._lock:
            self._requests_total += 1
            if status_code >= 500:
                self._errors_total += 1
            self._events.append((now, duration_ms, status_code))
            self._trim(now)

    def snapshot(self) -> ApiMetricSnapshot:
        now = time.time()
        with self._lock:
            self._trim(now)
            events = list(self._events)
            requests_total = self._requests_total
            errors_total = self._errors_total

        latencies = sorted(duration_ms for _timestamp, duration_ms, _status_code in events)
        recent_errors = sum(1 for _timestamp, _duration_ms, status_code in events if status_code >= 500)
        recent_request_count = len(events)
        average_latency_ms = sum(latencies) / len(latencies) if latencies else 0.0
        p95_latency_ms = latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))] if latencies else 0.0
        error_rate = recent_errors / recent_request_count if recent_request_count else 0.0
        return ApiMetricSnapshot(
            requests_total=requests_total,
            errors_total=errors_total,
            recent_request_count=recent_request_count,
            recent_error_count=recent_errors,
            average_latency_ms=round(average_latency_ms, 2),
            p95_latency_ms=round(p95_latency_ms, 2),
            error_rate=round(error_rate, 4),
        )

    def _trim(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self._events and (self._events[0][0] < cutoff or len(self._events) > self.max_events):
            self._events.popleft()


api_metrics_recorder = ApiMetricsRecorder()


def configure_monitoring(app: FastAPI) -> None:
    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.sentry_environment,
            traces_sample_rate=0.1,
        )

    if settings.enable_metrics:
        Instrumentator().instrument(app).expose(app, endpoint="/metrics")

    @app.middleware("http")
    async def record_api_metrics(request: Request, call_next) -> Response:
        started_at = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = (time.perf_counter() - started_at) * 1000
            if request.url.path.startswith(settings.api_prefix):
                api_metrics_recorder.record(duration_ms=duration_ms, status_code=status_code)

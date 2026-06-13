import secrets
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.requests import Request

from app.api.routes import domain_routers
from app.api.legacy_routes import (
    websocket_notifications,
    websocket_orders,
    websocket_portfolio,
    websocket_positions,
    websocket_prices,
    websocket_signals,
)
from app.api.monitoring import router as monitoring_router
from app.core.config import settings
from app.core.monitoring import configure_monitoring
from app.db.init_db import init_db

_RATE_LIMIT_BUCKETS: dict[str, list[float]] = {}


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    docs_url="/docs" if settings.expose_docs else None,
    redoc_url="/redoc" if settings.expose_docs else None,
    openapi_url="/openapi.json" if settings.expose_docs else None,
    lifespan=lifespan,
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if settings.is_production:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


@app.middleware("http")
async def rate_limit_requests(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    if request.method == "OPTIONS" or not settings.rate_limit_enabled:
        return await call_next(request)
    if not request.url.path.startswith(settings.api_prefix):
        return await call_next(request)

    client_host = request.client.host if request.client else "unknown"
    now = time.monotonic()
    window_start = now - settings.rate_limit_window_seconds
    bucket_key = f"{client_host}:{request.url.path}"
    bucket = [timestamp for timestamp in _RATE_LIMIT_BUCKETS.get(bucket_key, []) if timestamp >= window_start]

    if len(bucket) >= settings.rate_limit_requests:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
            headers={"Retry-After": str(settings.rate_limit_window_seconds)},
        )

    bucket.append(now)
    _RATE_LIMIT_BUCKETS[bucket_key] = bucket
    return await call_next(request)


@app.middleware("http")
async def require_api_key(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    if request.method == "OPTIONS" or not settings.api_key_auth_enabled:
        return await call_next(request)

    public_paths = {
        "/",
        f"{settings.api_prefix}/health",
        f"{settings.api_prefix}/auth/login",
        f"{settings.api_prefix}/auth/register",
        f"{settings.api_prefix}/auth/refresh",
    }
    if request.url.path in public_paths:
        return await call_next(request)

    if request.url.path.startswith(settings.api_prefix):
        provided_api_key = request.headers.get("X-API-Key", "")
        if not secrets.compare_digest(provided_api_key, settings.api_key or ""):
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid API key"},
                headers={"WWW-Authenticate": "ApiKey"},
            )

    return await call_next(request)


for domain_router in domain_routers:
    app.include_router(domain_router, prefix=settings.api_prefix)
app.include_router(monitoring_router, prefix=f"{settings.api_prefix}/monitoring")
app.add_api_websocket_route("/ws/prices", websocket_prices)
app.add_api_websocket_route("/ws/signals", websocket_signals)
app.add_api_websocket_route("/ws/orders", websocket_orders)
app.add_api_websocket_route("/ws/positions", websocket_positions)
app.add_api_websocket_route("/ws/portfolio", websocket_portfolio)
app.add_api_websocket_route("/ws/notifications", websocket_notifications)
configure_monitoring(app)


@app.get("/", tags=["root"])
def read_root() -> dict[str, str]:
    return {"message": "Trading AI API"}

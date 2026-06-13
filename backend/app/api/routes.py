from fastapi import APIRouter

from app.api import ai_models, audit, auth, backtests, brokers, market_data, notifications, paper_trading, portfolio, rbac, risk, signals, strategies, users
from app.api.monitoring import legacy_router as monitoring_router
from app.api.legacy_routes import (
    websocket_notifications,
    websocket_orders,
    websocket_portfolio,
    websocket_positions,
    websocket_prices,
    websocket_signals,
)

domain_routers = [
    auth.router,
    users.router,
    rbac.router,
    market_data.router,
    signals.router,
    strategies.router,
    backtests.router,
    ai_models.router,
    brokers.router,
    paper_trading.router,
    portfolio.router,
    risk.router,
    notifications.router,
    audit.router,
    monitoring_router,
]

router = APIRouter()
for domain_router in domain_routers:
    router.include_router(domain_router)


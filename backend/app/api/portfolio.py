from app.api.domain_router import build_domain_router

router = build_domain_router(
    [
        "/ws/portfolio",
        "/analytics/performance",
        "/analytics/equity-curve",
        "/analytics/strategies",
        "/analytics/trades",
        "/portfolio/summary",
        "/portfolio/performance",
        "/portfolio/exposure",
        "/portfolio/allocation",
        "/portfolio/pnl",
        "/portfolio/equity-curve",
    ]
)


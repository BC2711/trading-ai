from app.api.domain_router import build_domain_router

router = build_domain_router(
    [
        "/backtests",
        "/backtests/run",
        "/backtests/walk-forward",
        "/backtests/walk-forward/{run_id}",
        "/backtests/{run_id}/report",
    ]
)


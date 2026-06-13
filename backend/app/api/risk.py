from app.api.domain_router import build_domain_router

router = build_domain_router(
    [
        "/risk-settings",
        "/risk-settings/{risk_setting_id}",
        "/risk/summary",
        "/risk/validate-trade",
        "/risk/position-size",
        "/risk/limits",
        "/risk/circuit-breaker/enable",
        "/risk/circuit-breaker/disable",
        "/risk/monte-carlo",
        "/risk/monte-carlo/{run_id}",
    ]
)


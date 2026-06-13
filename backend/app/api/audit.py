from app.api.domain_router import build_domain_router

router = build_domain_router(
    [
        "/audit",
        "/audit/trades",
        "/audit/users",
        "/audit/ai",
        "/audit/risk",
        "/audit/events",
    ]
)


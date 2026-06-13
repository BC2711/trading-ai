from app.api.domain_router import build_domain_router

router = build_domain_router(
    [
        "/ws/signals",
        "/signals",
        "/signals/generate",
    ]
)


from app.api.domain_router import build_domain_router

router = build_domain_router(
    [
        "/users",
        "/users/{user_id}",
    ]
)


from app.api.domain_router import build_domain_router

router = build_domain_router(
    [
        "/roles",
        "/roles/{role_id}",
        "/permissions",
        "/users/{user_id}/roles",
        "/users/{user_id}/permissions",
    ]
)


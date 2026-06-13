from app.api.domain_router import build_domain_router

router = build_domain_router(
    [
        "/auth/register",
        "/auth/login",
        "/auth/logout",
        "/auth/refresh",
        "/me",
        "/navigation",
    ]
)


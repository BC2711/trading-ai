from app.api.domain_router import build_domain_router

router = build_domain_router(
    [
        "/ws/notifications",
        "/notifications",
        "/notifications/mark-read",
        "/notifications/settings",
        "/notifications/{notification_id}/read",
    ]
)


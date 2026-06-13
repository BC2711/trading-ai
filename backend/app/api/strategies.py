from app.api.domain_router import build_domain_router

router = build_domain_router(
    [
        "/strategies",
        "/strategies/builder",
        "/strategies/{strategy_id}",
        "/strategies/{strategy_id}/rules",
        "/strategies/{strategy_id}/evaluate",
        "/strategies/{strategy_id}/enable",
        "/strategies/{strategy_id}/disable",
    ]
)


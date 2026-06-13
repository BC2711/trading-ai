from app.api.domain_router import build_domain_router

router = build_domain_router(
    [
        "/ws/orders",
        "/ws/positions",
        "/paper/account",
        "/paper/orders",
        "/paper/positions",
        "/paper/positions/{position_id}/close",
        "/paper/performance",
        "/paper/reset",
        "/orders",
        "/orders/paper",
        "/orders/{order_id}/cancel",
        "/positions",
        "/positions/{position_id}/close",
    ]
)


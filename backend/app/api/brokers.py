from app.api.domain_router import build_domain_router

router = build_domain_router(
    [
        "/api-credentials",
        "/api-credentials/{credential_id}",
        "/brokers",
        "/brokers/connect",
        "/brokers/disconnect",
        "/brokers/{broker}/balance",
        "/brokers/{broker}/positions",
        "/brokers/{broker}/orders",
        "/brokers/{broker}/orders/{order_id}",
    ]
)


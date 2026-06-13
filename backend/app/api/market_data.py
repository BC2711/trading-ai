from app.api.domain_router import build_domain_router

router = build_domain_router(
    [
        "/ws/market-data",
        "/ws/prices",
        "/symbols",
        "/candles",
        "/market/candles",
        "/market/candles/import",
        "/market/history/{symbol}",
        "/market/history/sync",
        "/market-data/import",
        "/market-data/validate",
        "/market-data/repair",
        "/market-data/ticks",
        "/market-data/trades",
        "/market-data/order-books",
        "/market-data/stream",
        "/market-data/sync",
        "/market-data/refresh",
        "/market-data/refresh-task",
        "/market-data/schedule",
        "/features",
        "/features/calculate",
        "/features/sets",
        "/features/{symbol}",
        "/scanner",
        "/scanner/run",
        "/scanner/signals",
        "/sentiment",
        "/sentiment/analyze",
        "/sentiment/{symbol}",
        "/calendar/events",
        "/calendar/high-impact",
    ]
)


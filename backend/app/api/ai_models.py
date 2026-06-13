from app.api.domain_router import build_domain_router

router = build_domain_router(
    [
        "/copilot/chat",
        "/copilot/history",
        "/ai/analyze-signal",
        "/ai/analyses",
        "/ai/provider",
        "/ai/analyses/{analysis_id}",
        "/ai/models",
        "/ai/train",
        "/ai/models/train",
        "/ai/models/{model_id}",
        "/ai/models/{model_id}/retrain",
        "/ai/models/{model_id}/deploy",
        "/ai/models/{model_id}/activate",
        "/ai/models/{model_id}/disable",
        "/ai/evaluation/{model_id}",
        "/ai/models/compare",
        "/ai/models/{model_id}/predict",
        "/ai/predict",
    ]
)


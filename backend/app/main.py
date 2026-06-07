from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.core.config import settings
from app.core.monitoring import configure_monitoring
from app.db.init_db import init_db

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)
configure_monitoring(app)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/", tags=["root"])
def read_root() -> dict[str, str]:
    return {"message": "Trading AI API"}

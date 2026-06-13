import logging
import time
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import make_url

from app import models  # noqa: F401
from app.core.config import settings
from app.db.schema_compat import ensure_schema_compatibility
from app.db.session import Base, SessionLocal, engine
from app.services.repository import seed_defaults

logger = logging.getLogger(__name__)


def init_db(retries: int = 8, delay_seconds: float = 1.5) -> None:
    for attempt in range(1, retries + 1):
        try:
            if not settings.is_production and settings.development_auto_create_schema:
                ensure_sqlite_parent_directory()
                Base.metadata.create_all(bind=engine)
            if not settings.is_production and settings.development_schema_repair_enabled:
                ensure_schema_compatibility(engine)
            with SessionLocal() as db:
                seed_defaults(db)
            return
        except SQLAlchemyError as exc:
            if attempt == retries:
                raise
            logger.warning("Database initialization attempt %s/%s failed: %s", attempt, retries, exc)
            time.sleep(delay_seconds)


def ensure_sqlite_parent_directory() -> None:
    url = make_url(settings.database_url)
    if url.drivername != "sqlite" or not url.database or url.database == ":memory:":
        return
    database_path = Path(url.database)
    if database_path.parent != Path("."):
        database_path.parent.mkdir(parents=True, exist_ok=True)

import logging
import time

from sqlalchemy.exc import SQLAlchemyError

from app import models  # noqa: F401
from app.db.session import Base, SessionLocal, engine
from app.services.repository import seed_defaults

logger = logging.getLogger(__name__)


def init_db(retries: int = 8, delay_seconds: float = 1.5) -> None:
    for attempt in range(1, retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            with SessionLocal() as db:
                seed_defaults(db)
            return
        except SQLAlchemyError as exc:
            if attempt == retries:
                raise
            logger.warning("Database initialization attempt %s/%s failed: %s", attempt, retries, exc)
            time.sleep(delay_seconds)

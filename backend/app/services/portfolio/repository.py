from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PaperOrder, PaperPosition


class PortfolioRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_orders(self) -> list[PaperOrder]:
        return list(self.db.scalars(select(PaperOrder)).all())

    def list_positions(self) -> list[PaperPosition]:
        return list(self.db.scalars(select(PaperPosition)).all())

    def list_closed_positions(self) -> list[PaperPosition]:
        return list(
            self.db.scalars(
                select(PaperPosition)
                .where(PaperPosition.status == "closed", PaperPosition.closed_at.is_not(None))
                .order_by(PaperPosition.closed_at)
            ).all()
        )

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PaperAccount, PaperOrder, PaperPosition, PaperTradeLedger


class PaperTradingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_account(self) -> PaperAccount | None:
        return self.db.scalar(select(PaperAccount).where(PaperAccount.name == "default"))

    def list_orders(self, limit: int = 100) -> list[PaperOrder]:
        return list(self.db.scalars(select(PaperOrder).order_by(PaperOrder.created_at.desc()).limit(limit)).all())

    def list_positions(self, status: str = "open") -> list[PaperPosition]:
        statement = select(PaperPosition)
        if status != "all":
            statement = statement.where(PaperPosition.status == status)
        return list(self.db.scalars(statement.order_by(PaperPosition.created_at.desc())).all())

    def list_ledger(self, limit: int = 200) -> list[PaperTradeLedger]:
        return list(self.db.scalars(select(PaperTradeLedger).order_by(PaperTradeLedger.created_at.asc()).limit(limit)).all())

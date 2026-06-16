from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.auth import require_permission
from app.db.deps import get_db
from app.models import User
from app.schemas.automation import AutomatedTradingRunResponse
from app.services.automation import automation_status, run_automated_trading

router = APIRouter()


@router.get("/automation/status", response_model=AutomatedTradingRunResponse, tags=["automation"])
def get_automation_status(
    _user: User = Depends(require_permission("orders:manage")),
) -> AutomatedTradingRunResponse:
    return automation_status()


@router.post("/automation/run", response_model=AutomatedTradingRunResponse, tags=["automation"])
def post_automation_run(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("orders:manage")),
) -> AutomatedTradingRunResponse:
    return run_automated_trading(db)

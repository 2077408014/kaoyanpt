from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..services.report_service import report_service
from ..core.deps import get_current_user

router = APIRouter(prefix="/api/report", tags=["report"])


@router.get("/study")
def get_study_report(
    period: str = "week",
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return report_service.generate_study_report(db, current_user.id, period)


@router.get("/weekly-trend")
def get_weekly_trend(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return report_service.get_weekly_trend(db, current_user.id)
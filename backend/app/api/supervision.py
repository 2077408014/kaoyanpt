from typing import Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, Query
import base64
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..schemas.supervision import (
    SupervisionCheckRequest,
    SupervisionCheckResponse,
    SupervisionSessionStats,
    SupervisionDailyStats,
)
from ..services.supervision_service import supervision_service
from ..core.deps import get_current_user
from ..models.user import User

router = APIRouter(prefix="/api/supervision", tags=["supervision"])


@router.post("/session/start")
async def start_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session_id = supervision_service.start_session(current_user.id)
    return {"session_id": session_id, "started_at": date.today().isoformat()}


@router.post("/check", response_model=SupervisionCheckResponse)
async def check_supervision(
    data: SupervisionCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    image_bytes = base64.b64decode(data.image_base64.split(",")[-1])
    result = supervision_service.detect_status(image_bytes)
    supervision_service.record_check(db, current_user.id, data.session_id, result)
    return SupervisionCheckResponse(
        status=result["status"],
        confidence=result["confidence"],
        face_count=result["face_count"],
        overlay_base64=result.get("overlay_base64"),
    )


@router.get("/session/{session_id}/stats", response_model=SupervisionSessionStats)
async def get_session_stats(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stats = supervision_service.get_session_stats(db, current_user.id, session_id)
    return SupervisionSessionStats(**stats)


@router.get("/daily-stats", response_model=SupervisionDailyStats)
async def get_daily_stats(
    target_date: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if target_date is None:
        target_date = date.today()
    stats = supervision_service.get_daily_stats(db, current_user.id, target_date)
    return SupervisionDailyStats(**stats)
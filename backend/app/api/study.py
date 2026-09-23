"""学习时长跟踪路由（独立模块）

为前端提供：
- POST /api/study/heartbeat  心跳累计学习时长（按秒）
- POST /api/study/event      记录学习事件（错题/单词/题目）
- GET  /api/study/today      查看今日统计
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.deps import get_current_user
from ..services.study_tracker import study_tracker_service


router = APIRouter(prefix="/api/study", tags=["学习时长跟踪"])


class HeartbeatRequest(BaseModel):
    seconds: int = Field(default=0, ge=0, le=30 * 60)


class EventRequest(BaseModel):
    event_type: str = Field(..., description="mistake_added | word_learned | question_completed")
    count: int = Field(default=1, ge=1, le=100)


_EVENT_FIELD_MAP = {
    "mistake_added": "mistakes_added",
    "word_learned": "words_studied",
    "question_completed": "questions_completed",
}


@router.post("/heartbeat")
def heartbeat(
    payload: HeartbeatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """前端每 30s 发送一次心跳，累计学习时长。"""
    try:
        return study_tracker_service.add_study_time(
            db, current_user.id, payload.seconds
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"心跳记录失败: {e}")


@router.post("/event")
def track_event(
    payload: EventRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """记录学习事件。event_type: mistake_added | word_learned | question_completed"""
    field = _EVENT_FIELD_MAP.get(payload.event_type)
    if not field:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的事件类型: {payload.event_type}",
        )
    try:
        return study_tracker_service.increment_counter(
            db, current_user.id, field, payload.count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"事件记录失败: {e}")


@router.get("/today")
def today_stats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取今日学习统计。"""
    return study_tracker_service._today_snapshot(db, current_user.id)
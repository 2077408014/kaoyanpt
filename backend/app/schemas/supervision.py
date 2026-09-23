from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SupervisionCheckRequest(BaseModel):
    image_base64: str
    session_id: str


class SupervisionCheckResponse(BaseModel):
    status: str
    confidence: float
    face_count: int
    overlay_base64: Optional[str] = None


class SupervisionSessionCreate(BaseModel):
    session_id: str
    started_at: datetime


class SupervisionSessionStats(BaseModel):
    session_id: str
    total_checks: int
    focused_count: int
    distracted_count: int
    absent_count: int
    unknown_count: int
    focus_rate: float
    duration_seconds: int


class SupervisionDailyStats(BaseModel):
    date: str
    total_focused_seconds: int
    total_checks: int
    focus_rate: float
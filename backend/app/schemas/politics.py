from typing import Optional
from pydantic import BaseModel, Field, field_serializer
from datetime import date, datetime


class PoliticsRecitationCreate(BaseModel):
    title: str
    category: Optional[str] = "马原"
    content: str
    image_path: Optional[str] = None


class PoliticsRecitationUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    content: Optional[str] = None
    image_path: Optional[str] = None
    mastery_level: Optional[str] = None


class PoliticsRecitationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    category: str
    content: str
    image_path: Optional[str]
    mastery_level: str
    review_count: int
    next_review_date: Optional[date]
    last_review_date: Optional[date]
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}

    @field_serializer("next_review_date", "last_review_date")
    def serialize_date(self, value: Optional[date]) -> Optional[str]:
        return value.isoformat() if value else None

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class PoliticsRecognizeRequest(BaseModel):
    image_path: str


class PoliticsRecognizeResponse(BaseModel):
    content: str
    confidence: float


class PoliticsReviewRequest(BaseModel):
    result: str


class RecitationReminderCreate(BaseModel):
    reminder_type: str = Field(..., description="提醒类型：单词/政治")
    reminder_time: str = Field(..., description="提醒时间 HH:MM")
    frequency: str = Field(..., description="频率：每天/工作日/周末/自定义")


class RecitationReminderUpdate(BaseModel):
    reminder_time: Optional[str] = None
    frequency: Optional[str] = None
    enabled: Optional[int] = None


class RecitationReminderResponse(BaseModel):
    id: int
    user_id: int
    reminder_type: str
    reminder_time: str
    frequency: str
    enabled: int
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None

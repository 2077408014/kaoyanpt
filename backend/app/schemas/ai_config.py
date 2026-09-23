from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class AIConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    provider: str = Field(..., min_length=1, max_length=50)
    api_key: str = Field(..., min_length=1, max_length=500)
    base_url: str = Field(..., min_length=1, max_length=255)
    model: str = Field(..., min_length=1, max_length=100)


class AIConfigUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    provider: Optional[str] = Field(None, max_length=50)
    api_key: Optional[str] = Field(None, max_length=500)
    base_url: Optional[str] = Field(None, max_length=255)
    model: Optional[str] = Field(None, max_length=100)


class AIConfigResponse(BaseModel):
    id: int
    user_id: int
    name: str
    provider: str
    api_key: str
    base_url: str
    model: str
    created_at: datetime

    class Config:
        from_attributes = True


class AIConfigListItem(BaseModel):
    id: int
    name: str
    provider: str
    model: str
    created_at: datetime

    class Config:
        from_attributes = True
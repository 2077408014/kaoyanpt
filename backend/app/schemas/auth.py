from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    code: str = Field(..., min_length=6, max_length=6, description="邮箱验证码")

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    avatar: Optional[str]
    ai_api_provider: Optional[str]
    ai_api_model: Optional[str]
    ai_api_base_url: Optional[str]
    active_ai_config_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AIConfigUpdate(BaseModel):
    ai_api_provider: Optional[str]
    ai_api_key: Optional[str]
    ai_api_base_url: Optional[str]
    ai_api_model: Optional[str]

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshTokenRequest(BaseModel):
    refresh_token: str
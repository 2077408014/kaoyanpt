from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import timedelta
from ..core.database import get_db
from ..core.deps import get_current_user
from ..core.security import decode_access_token, create_access_token
from ..core.config import settings
from ..schemas.auth import (
    UserCreate, UserLogin, UserResponse, TokenResponse, AIConfigUpdate,
    RefreshTokenRequest
)
from ..services.auth_service import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    try:
        user = auth_service.register(db, user_data)
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/login", response_model=TokenResponse)
async def login(login_data: UserLogin, db: Session = Depends(get_db)):
    try:
        token = auth_service.login(db, login_data)
        return token
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

@router.get("/me", response_model=UserResponse)
async def get_me(current_user = Depends(get_current_user)):
    return current_user


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    payload = decode_access_token(request.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌"
        )

    token_type = payload.get("type")
    if token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌类型"
        )

    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的用户ID"
        )

    user = auth_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id, "type": "access"},
        expires_delta=access_token_expires
    )

    refresh_token_expires = timedelta(days=7)
    new_refresh_token = create_access_token(
        data={"sub": user.email, "user_id": user.id, "type": "refresh"},
        expires_delta=refresh_token_expires
    )

    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)


class SendVerificationCodeRequest(BaseModel):
    email: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    email: str
    code: str
    new_password: str


@router.post("/send-verification-code")
async def send_verification_code(request: SendVerificationCodeRequest, db: Session = Depends(get_db)):
    try:
        auth_service.send_email_verification_code(db, request.email)
        return {"message": "验证码已发送到您的邮箱，请查收"}
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"发送验证码失败: {str(e)}")


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    try:
        auth_service.send_password_reset_code(db, request.email)
        return {"message": "验证码已发送到您的邮箱，请查收"}
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"发送验证码失败: {str(e)}")


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    try:
        auth_service.reset_password(db, request.email, request.code, request.new_password)
        return {"message": "密码重置成功，请使用新密码登录"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="密码重置失败，请稍后重试")

@router.put("/ai-config", response_model=UserResponse)
async def update_ai_config(
    config: AIConfigUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        if config.ai_api_key is not None:
            current_user.ai_api_key = config.ai_api_key
        if config.ai_api_base_url is not None:
            current_user.ai_api_base_url = config.ai_api_base_url
        if config.ai_api_model is not None:
            current_user.ai_api_model = config.ai_api_model
        if config.ai_api_provider is not None:
            current_user.ai_api_provider = config.ai_api_provider
        
        db.commit()
        db.refresh(current_user)
        return current_user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
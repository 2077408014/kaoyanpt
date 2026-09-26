from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .security import decode_access_token
from ..models.organization import (
    ROLE_STUDENT, ROLE_TEACHER, ROLE_INSTITUTION_ADMIN, ROLE_SUPER_ADMIN,
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _resolve_user(token: str, db: Session):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的访问令牌",
        )
    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的用户ID",
        )

    from ..services.auth_service import auth_service

    user = auth_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )
    return user


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    return _resolve_user(token, db)


def get_current_user_from_query(token: str = None, db: Session = Depends(get_db)):
    """从 query/token 参数中解析登录用户（用于 SSE / 文件下载等场景）。"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供访问令牌",
        )
    return _resolve_user(token, db)


def require_role(*roles: str):
    """生成角色校验依赖：current_user.role 必须在 roles 内，否则 403。"""
    allowed = set(roles)

    def _checker(current_user=Depends(get_current_user)):
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限执行该操作",
            )
        return current_user

    return _checker


# 便捷封装
require_super_admin = require_role(ROLE_SUPER_ADMIN)
require_teacher = require_role(ROLE_TEACHER, ROLE_SUPER_ADMIN)
require_institution_admin = require_role(ROLE_INSTITUTION_ADMIN, ROLE_SUPER_ADMIN)
require_student = require_role(ROLE_STUDENT)
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.deps import require_super_admin
from ..models.user import User
from ..services.organization_service import organization_service as svc
from ..schemas.organization import (
    InstitutionCreate, InstitutionResponse,
    StaffUserCreate, StaffUserUpdate, StaffUserResponse,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _bad(exc: ValueError):
    message = str(exc)
    code = status.HTTP_404_NOT_FOUND if "不存在" in message else status.HTTP_400_BAD_REQUEST
    raise HTTPException(status_code=code, detail=message)


# ---------- 机构 ----------

@router.post("/institutions", response_model=InstitutionResponse)
async def create_institution(
    data: InstitutionCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    try:
        return svc.create_institution(db, data.name)
    except ValueError as e:
        _bad(e)


@router.get("/institutions", response_model=list[InstitutionResponse])
async def list_institutions(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    items = svc.list_institutions(db)
    result = []
    for inst in items:
        class_count = len(svc.get_institution_class_ids(db, inst.id))
        result.append(InstitutionResponse(
            id=inst.id, name=inst.name, created_at=inst.created_at,
            class_count=class_count,
        ))
    return result


# ---------- 员工账号 ----------

def _staff_response(db: Session, user: User) -> StaffUserResponse:
    inst = svc.get_institution(db, user.institution_id) if user.institution_id else None
    return StaffUserResponse(
        id=user.id, username=user.username, email=user.email,
        role=user.role, institution_id=user.institution_id,
        institution_name=inst.name if inst else None,
        is_active=getattr(user, "is_active", True),
        must_change_password=bool(getattr(user, "must_change_password", False)),
        created_at=user.created_at,
    )


@router.post("/users", response_model=StaffUserResponse)
async def create_staff_user(
    data: StaffUserCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    try:
        user = svc.create_staff_user(
            db, data.username, data.email, data.password,
            data.role, data.institution_id,
        )
    except ValueError as e:
        _bad(e)
    return _staff_response(db, user)


@router.put("/users/{user_id}", response_model=StaffUserResponse)
async def update_staff_user(
    user_id: int,
    data: StaffUserUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    user = svc.get_staff_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="账号不存在")
    try:
        user = svc.update_staff_user(
            db, user,
            username=data.username, email=data.email, password=data.password,
            role=data.role, institution_id=data.institution_id,
        )
    except ValueError as e:
        _bad(e)
    return _staff_response(db, user)


@router.delete("/users/{user_id}")
async def delete_staff_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    user = svc.get_staff_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="账号不存在")
    svc.delete_staff_user(db, user)
    return {"message": "账号已删除"}


@router.get("/users", response_model=list[StaffUserResponse])
async def list_staff_users(
    role: Optional[str] = None,
    institution_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_super_admin),
):
    users = svc.list_staff_users(db, role=role, institution_id=institution_id)
    inst_cache = {}
    result = []
    for u in users:
        inst_name = None
        if u.institution_id:
            inst_name = inst_cache.setdefault(
                u.institution_id,
                (svc.get_institution(db, u.institution_id) or None),
            )
            inst_name = inst_name.name if inst_name else None
        result.append(StaffUserResponse(
            id=u.id, username=u.username, email=u.email, role=u.role,
            institution_id=u.institution_id, institution_name=inst_name,
            is_active=getattr(u, "is_active", True),
            must_change_password=bool(getattr(u, "must_change_password", False)),
            created_at=u.created_at,
        ))
    return result

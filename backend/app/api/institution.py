from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.deps import require_institution_admin
from ..models.user import User
from ..models.organization import ROLE_SUPER_ADMIN
from ..services.organization_service import organization_service as svc
from ..services.stats_query_service import stats_query_service as stats
from ..services.mistake_service import mistake_service
from ..schemas.organization import (
    ClassSummary, StudentSummary, StudentOverview,
    ClassResponse, ClassSettingsUpdate,
    StaffUserResponse, TeacherBrief,
    InstitutionClassCreate, InstitutionTeacherCreate, InstitutionTeacherUpdate,
    TeacherAssignRequest,
)
from ..schemas.mistake import MistakeResponse

router = APIRouter(prefix="/api/institution", tags=["institution"])


def _denied(exc: PermissionError):
    raise HTTPException(status_code=403, detail=str(exc))


def _resolve_institution_id(db: Session, current_user: User, institution_id: Optional[int]) -> int:
    """机构管理者固定操作本机构；超管必须显式指定机构。"""
    if current_user.role == ROLE_SUPER_ADMIN:
        if institution_id is None:
            raise HTTPException(status_code=400, detail="请指定要操作的机构")
        if not svc.get_institution(db, institution_id):
            raise HTTPException(status_code=404, detail="机构不存在")
        return institution_id
    return current_user.institution_id


def _assert_institution_admin(current_user: User):
    """写操作仅机构管理者；超管只有只读权限。"""
    if current_user.role == ROLE_SUPER_ADMIN:
        _denied(PermissionError("班级管理仅机构管理者可操作"))


def _assert_class_writable(db: Session, current_user: User, class_id: int):
    _assert_institution_admin(current_user)
    cls = svc.get_class(db, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")
    if cls.institution_id != current_user.institution_id:
        _denied(PermissionError("无权限操作其他机构的班级"))
    return cls


def _class_response(db, cls) -> ClassResponse:
    inst = svc.get_institution(db, cls.institution_id)
    teachers = svc.class_teachers(db, cls.id)
    return ClassResponse(
        id=cls.id, name=cls.name, institution_id=cls.institution_id,
        institution_name=inst.name if inst else None,
        join_code=cls.join_code,
        code_expires_at=cls.code_expires_at,
        code_max_uses=cls.code_max_uses,
        code_uses=cls.code_uses or 0,
        student_count=svc.student_count(db, cls.id),
        teacher_count=len(teachers),
        teachers=[TeacherBrief(id=t.id, username=t.username) for t in teachers],
        created_at=cls.created_at,
    )


def _bad(exc: ValueError):
    message = str(exc)
    code = 404 if "不存在" in message else 400
    raise HTTPException(status_code=code, detail=message)


def _class_summary_item(db, cls) -> ClassSummary:
    agg = stats.class_summary(db, cls.id)
    inst = svc.get_institution(db, cls.institution_id)
    return ClassSummary(
        id=cls.id, name=cls.name, institution_id=cls.institution_id,
        institution_name=inst.name if inst else None,
        join_code=cls.join_code,
        code_expires_at=cls.code_expires_at,
        code_max_uses=cls.code_max_uses,
        code_uses=cls.code_uses or 0,
        **agg,
    )


@router.get("/classes", response_model=list[ClassSummary])
async def institution_classes(
    institution_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_institution_admin),
):
    # 机构管理者固定取自身机构；超管必须显式指定 institution_id
    if current_user.role == ROLE_SUPER_ADMIN:
        if institution_id is None:
            raise HTTPException(status_code=400, detail="请指定要查看的机构")
    classes = svc.list_institution_classes(db, current_user)
    if current_user.role == ROLE_SUPER_ADMIN:
        classes = svc.list_classes(db, institution_id)
    return [_class_summary_item(db, c) for c in classes]


@router.get("/classes/{class_id}/students", response_model=list[StudentSummary])
async def class_students(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_institution_admin),
):
    try:
        svc.assert_class_in_scope(db, current_user, class_id)
    except PermissionError as e:
        _denied(e)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return [StudentSummary(**item) for item in stats.class_student_summaries(db, class_id)]


@router.get("/classes/{class_id}/teachers", response_model=list[TeacherBrief])
async def class_teachers(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_institution_admin),
):
    try:
        svc.assert_class_in_scope(db, current_user, class_id)
    except PermissionError as e:
        _denied(e)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return [
        TeacherBrief(id=t.id, username=t.username)
        for t in svc.class_teachers(db, class_id)
    ]


@router.get("/students/{student_id}/overview", response_model=StudentOverview)
async def student_overview(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_institution_admin),
):
    student_ids = svc.get_institution_student_ids(db, current_user)
    if student_ids is not None and student_id not in student_ids:
        raise HTTPException(status_code=403, detail="无权限查看该学生")
    student = db.query(User).filter(User.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    data = stats.student_overview(db, student_id)
    return StudentOverview(id=student.id, username=student.username, **data)


@router.get("/students/{student_id}/mistakes", response_model=list[MistakeResponse])
async def student_mistakes(
    student_id: int,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_institution_admin),
):
    student_ids = svc.get_institution_student_ids(db, current_user)
    if student_ids is not None and student_id not in student_ids:
        raise HTTPException(status_code=403, detail="无权限查看该学生")
    filters = {"subject": subject} if subject else None
    return mistake_service.get_mistakes(db, student_id, filters)


@router.get("/students/{student_id}/mistakes/{mistake_id}", response_model=MistakeResponse)
async def student_mistake_detail(
    student_id: int,
    mistake_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_institution_admin),
):
    student_ids = svc.get_institution_student_ids(db, current_user)
    if student_ids is not None and student_id not in student_ids:
        raise HTTPException(status_code=403, detail="无权限查看该学生")
    mistake = mistake_service.get_mistake_by_id(db, student_id, mistake_id)
    if not mistake:
        raise HTTPException(status_code=404, detail="错题不存在")
    return mistake


# ---------- 写操作：班级 / 教师 / 分配（本机构内） ----------

@router.post("/classes", response_model=ClassResponse)
async def create_class(
    data: InstitutionClassCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_institution_admin),
):
    _assert_institution_admin(current_user)
    institution_id = current_user.institution_id
    # 机构管理者只能在本机构建班；显式指定其他机构属于越权
    if data.institution_id is not None and data.institution_id != institution_id:
        raise HTTPException(status_code=403, detail="无权为其他机构创建班级")
    if not svc.get_institution(db, institution_id):
        raise HTTPException(status_code=404, detail="机构不存在")
    try:
        cls = svc.create_class(
            db, institution_id, data.name,
            code_expires_at=data.code_expires_at,
            code_max_uses=data.code_max_uses,
        )
    except ValueError as e:
        _bad(e)
    return _class_response(db, cls)


@router.patch("/classes/{class_id}", response_model=ClassResponse)
async def update_class(
    class_id: int,
    data: ClassSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_institution_admin),
):
    _assert_class_writable(db, current_user, class_id)
    kwargs = {}
    for field in ("name", "code_expires_at", "code_max_uses"):
        if field in data.model_fields_set:
            kwargs[field] = getattr(data, field)
    try:
        cls = svc.update_class(db, class_id, **kwargs)
    except ValueError as e:
        _bad(e)
    return _class_response(db, cls)


@router.post("/classes/{class_id}/reset-code", response_model=ClassResponse)
async def reset_join_code(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_institution_admin),
):
    _assert_class_writable(db, current_user, class_id)
    try:
        cls = svc.reset_join_code(db, class_id)
    except ValueError as e:
        _bad(e)
    return _class_response(db, cls)


def _staff_response(db, u) -> StaffUserResponse:
    inst = svc.get_institution(db, u.institution_id)
    return StaffUserResponse(
        id=u.id, username=u.username, email=u.email, role=u.role,
        institution_id=u.institution_id,
        institution_name=inst.name if inst else None,
        is_active=getattr(u, "is_active", True),
        must_change_password=bool(getattr(u, "must_change_password", False)),
        created_at=u.created_at,
    )


@router.get("/teachers", response_model=list[StaffUserResponse])
async def list_teachers(
    institution_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_institution_admin),
):
    target_institution = _resolve_institution_id(db, current_user, institution_id)
    users = svc.list_staff_users(db, role="teacher", institution_id=target_institution)
    return [_staff_response(db, u) for u in users]


@router.post("/teachers", response_model=StaffUserResponse)
async def create_teacher(
    data: InstitutionTeacherCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_institution_admin),
):
    _assert_institution_admin(current_user)
    target_institution = current_user.institution_id
    try:
        user = svc.create_staff_user(
            db, data.username, data.email, data.password,
            "teacher", target_institution,
        )
    except ValueError as e:
        _bad(e)
    return _staff_response(db, user)


def _assert_teacher_in_scope(current_user: User, user: User):
    """机构管理者只能操作本机构的教师账号。"""
    if user.role != "teacher" or user.institution_id != current_user.institution_id:
        _denied(PermissionError("无权限操作该教师账号"))


@router.put("/teachers/{teacher_id}", response_model=StaffUserResponse)
async def update_teacher(
    teacher_id: int,
    data: InstitutionTeacherUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_institution_admin),
):
    _assert_institution_admin(current_user)
    user = svc.get_staff_user(db, teacher_id)
    if not user:
        raise HTTPException(status_code=404, detail="教师账号不存在")
    _assert_teacher_in_scope(current_user, user)
    try:
        user = svc.update_staff_user(
            db, user,
            username=data.username, email=data.email, password=data.password,
        )
    except ValueError as e:
        _bad(e)
    return _staff_response(db, user)


@router.delete("/teachers/{teacher_id}")
async def delete_teacher(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_institution_admin),
):
    _assert_institution_admin(current_user)
    user = svc.get_staff_user(db, teacher_id)
    if not user:
        raise HTTPException(status_code=404, detail="教师账号不存在")
    _assert_teacher_in_scope(current_user, user)
    svc.delete_staff_user(db, user)
    return {"message": "教师账号已删除"}


@router.post("/classes/{class_id}/teachers")
async def assign_teacher(
    class_id: int,
    data: TeacherAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_institution_admin),
):
    _assert_class_writable(db, current_user, class_id)
    try:
        svc.assign_teacher(db, class_id, data.teacher_id)
    except ValueError as e:
        _bad(e)
    return {"message": "教师分配成功"}


@router.delete("/classes/{class_id}/teachers/{teacher_id}")
async def unassign_teacher(
    class_id: int,
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_institution_admin),
):
    _assert_class_writable(db, current_user, class_id)
    try:
        svc.unassign_teacher(db, class_id, teacher_id)
    except ValueError as e:
        _bad(e)
    return {"message": "已取消教师分配"}

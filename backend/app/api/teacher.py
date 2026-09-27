import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..core.config import UPLOAD_PATH
from ..core.database import get_db
from ..core.deps import require_teacher
from ..models.user import User
from ..services.organization_service import organization_service as svc
from ..services.stats_query_service import stats_query_service as stats
from ..services.class_content_service import (
    class_content_service as content,
    load_images,
)
from ..services.mistake_service import mistake_service
from ..schemas.organization import (
    ClassListResponse, StudentSummary, StudentOverview,
    AddStudentRequest,
    AnnouncementCreate, AnnouncementUpdate, AnnouncementResponse,
    AssignmentCreate, AssignmentUpdate, AssignmentResponse,
    SubmissionResponse, GradeRequest,
)
from ..schemas.mistake import MistakeResponse

router = APIRouter(prefix="/api/teacher", tags=["teacher"])


def _denied(exc: PermissionError):
    raise HTTPException(status_code=403, detail=str(exc))


def _not_found_or_bad(exc: ValueError):
    message = str(exc)
    code = 404 if "不存在" in message else 400
    raise HTTPException(status_code=code, detail=message)


def _class_list_item(db, cls) -> ClassListResponse:
    inst = svc.get_institution(db, cls.institution_id)
    return ClassListResponse(
        id=cls.id, name=cls.name, institution_id=cls.institution_id,
        institution_name=inst.name if inst else None,
        join_code=cls.join_code,
        code_expires_at=cls.code_expires_at,
        code_max_uses=cls.code_max_uses,
        code_uses=cls.code_uses or 0,
        student_count=svc.student_count(db, cls.id),
        teacher_count=svc.teacher_count(db, cls.id),
    )


@router.get("/classes", response_model=list[ClassListResponse])
async def my_classes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    return [_class_list_item(db, c) for c in svc.list_teacher_classes(db, current_user)]


@router.get("/classes/{class_id}/students", response_model=list[StudentSummary])
async def class_students(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    try:
        svc.assert_class_in_scope(db, current_user, class_id)
    except PermissionError as e:
        _denied(e)
    except ValueError as e:
        _not_found_or_bad(e)
    return [StudentSummary(**item) for item in stats.class_student_summaries(db, class_id)]


@router.get("/students/{student_id}/overview", response_model=StudentOverview)
async def student_overview(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    student_ids = svc.get_teacher_student_ids(db, current_user)
    try:
        svc.assert_student_in_scope(db, current_user, student_id, student_ids)
    except PermissionError as e:
        _denied(e)
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
    current_user: User = Depends(require_teacher),
):
    student_ids = svc.get_teacher_student_ids(db, current_user)
    try:
        svc.assert_student_in_scope(db, current_user, student_id, student_ids)
    except PermissionError as e:
        _denied(e)
    filters = {"subject": subject} if subject else None
    return mistake_service.get_mistakes(db, student_id, filters)


@router.get("/students/{student_id}/mistakes/{mistake_id}", response_model=MistakeResponse)
async def student_mistake_detail(
    student_id: int,
    mistake_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    student_ids = svc.get_teacher_student_ids(db, current_user)
    try:
        svc.assert_student_in_scope(db, current_user, student_id, student_ids)
    except PermissionError as e:
        _denied(e)
    mistake = mistake_service.get_mistake_by_id(db, student_id, mistake_id)
    if not mistake:
        raise HTTPException(status_code=404, detail="错题不存在")
    return mistake


@router.delete("/classes/{class_id}/students/{student_id}")
async def remove_student(
    class_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    try:
        svc.remove_student_from_class(db, current_user, class_id, student_id)
    except PermissionError as e:
        _denied(e)
    except ValueError as e:
        _not_found_or_bad(e)
    return {"message": "已将学生移出班级"}


@router.post("/classes/{class_id}/students/add")
async def add_student(
    class_id: int,
    data: AddStudentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    try:
        student = svc.add_student_by_email(db, current_user, class_id, data.email)
    except PermissionError as e:
        _denied(e)
    except ValueError as e:
        _not_found_or_bad(e)
    return {"message": f"已将 {student.username} 加入班级"}


@router.post("/classes/{class_id}/students/{student_id}/suspend")
async def suspend_student(
    class_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    try:
        svc.set_member_status(db, current_user, class_id, student_id, "suspended")
    except PermissionError as e:
        _denied(e)
    except ValueError as e:
        _not_found_or_bad(e)
    return {"message": "已暂停该学生"}


@router.post("/classes/{class_id}/students/{student_id}/restore")
async def restore_student(
    class_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    try:
        svc.set_member_status(db, current_user, class_id, student_id, "active")
    except PermissionError as e:
        _denied(e)
    except ValueError as e:
        _not_found_or_bad(e)
    return {"message": "已恢复该学生"}


# ---------- 公告 ----------

def _announcement_response(db, ann) -> AnnouncementResponse:
    author = db.query(User).filter(User.id == ann.author_id).first() if ann.author_id else None
    return AnnouncementResponse(
        id=ann.id, class_id=ann.class_id, author_id=ann.author_id,
        author_name=author.username if author else None,
        title=ann.title, content=ann.content,
        created_at=ann.created_at, updated_at=ann.updated_at,
    )


@router.get("/classes/{class_id}/announcements", response_model=list[AnnouncementResponse])
async def list_announcements(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    try:
        svc.assert_class_in_scope(db, current_user, class_id)
    except PermissionError as e:
        _denied(e)
    except ValueError as e:
        _not_found_or_bad(e)
    return [_announcement_response(db, a) for a in content.list_announcements(db, class_id)]


@router.post("/classes/{class_id}/announcements", response_model=AnnouncementResponse)
async def create_announcement(
    class_id: int,
    data: AnnouncementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    try:
        svc.assert_can_manage_class(db, current_user, class_id)
        ann = content.create_announcement(
            db, class_id, current_user.id, data.title, data.content
        )
    except PermissionError as e:
        _denied(e)
    except ValueError as e:
        _not_found_or_bad(e)
    return _announcement_response(db, ann)


@router.put("/announcements/{announcement_id}", response_model=AnnouncementResponse)
async def update_announcement(
    announcement_id: int,
    data: AnnouncementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    ann = content.get_announcement(db, announcement_id)
    if not ann:
        raise HTTPException(status_code=404, detail="公告不存在")
    try:
        svc.assert_can_manage_class(db, current_user, ann.class_id)
        ann = content.update_announcement(
            db, ann,
            data.title if data.title is not None else ann.title,
            data.content if data.content is not None else ann.content,
        )
    except PermissionError as e:
        _denied(e)
    return _announcement_response(db, ann)


@router.delete("/announcements/{announcement_id}")
async def delete_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    ann = content.get_announcement(db, announcement_id)
    if not ann:
        raise HTTPException(status_code=404, detail="公告不存在")
    try:
        svc.assert_can_manage_class(db, current_user, ann.class_id)
    except PermissionError as e:
        _denied(e)
    content.delete_announcement(db, ann)
    return {"message": "公告已删除"}


# ---------- 作业 ----------

def _submission_response(db, sub) -> SubmissionResponse:
    student = db.query(User).filter(User.id == sub.student_id).first()
    return SubmissionResponse(
        id=sub.id, assignment_id=sub.assignment_id, student_id=sub.student_id,
        student_name=student.username if student else None,
        content=sub.content, images=load_images(sub.images), submitted_at=sub.submitted_at,
        score=sub.score, feedback=sub.feedback, graded_at=sub.graded_at,
    )


def _assignment_teacher_response(db, asm) -> AssignmentResponse:
    subs = content.list_submissions(db, asm.id)
    graded = sum(1 for s in subs if s.score is not None)
    return AssignmentResponse(
        id=asm.id, class_id=asm.class_id, title=asm.title, content=asm.content,
        images=load_images(asm.images),
        due_at=asm.due_at, created_at=asm.created_at,
        submission_count=len(subs), graded_count=graded,
    )


@router.post("/assignments/upload-image")
async def upload_assignment_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_teacher),
):
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="仅支持 JPG/PNG/WEBP 图片")

    images_dir = UPLOAD_PATH / "assignments"
    images_dir.mkdir(parents=True, exist_ok=True)

    ext = file.filename.split(".")[-1] if file.filename else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"

    with open(images_dir / filename, "wb") as f:
        f.write(await file.read())

    return {
        "image_path": f"assignments/{filename}",
        "image_url": f"/uploads/assignments/{filename}",
    }


@router.get("/classes/{class_id}/assignments", response_model=list[AssignmentResponse])
async def list_assignments(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    try:
        svc.assert_class_in_scope(db, current_user, class_id)
    except PermissionError as e:
        _denied(e)
    except ValueError as e:
        _not_found_or_bad(e)
    return [_assignment_teacher_response(db, a) for a in content.list_assignments(db, class_id)]


@router.post("/classes/{class_id}/assignments", response_model=AssignmentResponse)
async def create_assignment(
    class_id: int,
    data: AssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    try:
        svc.assert_can_manage_class(db, current_user, class_id)
        asm = content.create_assignment(
            db, class_id, current_user.id, data.title, data.content, data.due_at,
            images=data.images,
        )
    except PermissionError as e:
        _denied(e)
    except ValueError as e:
        _not_found_or_bad(e)
    return _assignment_teacher_response(db, asm)


@router.get("/assignments/{assignment_id}", response_model=AssignmentResponse)
async def get_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    asm = content.get_assignment(db, assignment_id)
    if not asm:
        raise HTTPException(status_code=404, detail="作业不存在")
    try:
        svc.assert_class_in_scope(db, current_user, asm.class_id)
    except PermissionError as e:
        _denied(e)
    return _assignment_teacher_response(db, asm)


@router.put("/assignments/{assignment_id}", response_model=AssignmentResponse)
async def update_assignment(
    assignment_id: int,
    data: AssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    asm = content.get_assignment(db, assignment_id)
    if not asm:
        raise HTTPException(status_code=404, detail="作业不存在")
    try:
        svc.assert_can_manage_class(db, current_user, asm.class_id)
        updates = {}
        for field in ("title", "content", "due_at", "images"):
            if field in data.model_fields_set:
                updates[field] = getattr(data, field)
        content.update_assignment(db, asm, **updates)
    except PermissionError as e:
        _denied(e)
    except ValueError as e:
        _not_found_or_bad(e)
    return _assignment_teacher_response(db, asm)


@router.delete("/assignments/{assignment_id}")
async def delete_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    asm = content.get_assignment(db, assignment_id)
    if not asm:
        raise HTTPException(status_code=404, detail="作业不存在")
    try:
        svc.assert_can_manage_class(db, current_user, asm.class_id)
    except PermissionError as e:
        _denied(e)
    content.delete_assignment(db, asm)
    return {"message": "作业已删除"}


@router.get("/assignments/{assignment_id}/submissions", response_model=list[SubmissionResponse])
async def list_submissions(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    asm = content.get_assignment(db, assignment_id)
    if not asm:
        raise HTTPException(status_code=404, detail="作业不存在")
    try:
        svc.assert_class_in_scope(db, current_user, asm.class_id)
    except PermissionError as e:
        _denied(e)
    return [_submission_response(db, s) for s in content.list_submissions(db, assignment_id)]


@router.post("/assignments/{assignment_id}/grade", response_model=SubmissionResponse)
async def grade_submission(
    assignment_id: int,
    data: GradeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    asm = content.get_assignment(db, assignment_id)
    if not asm:
        raise HTTPException(status_code=404, detail="作业不存在")
    try:
        svc.assert_can_manage_class(db, current_user, asm.class_id)
    except PermissionError as e:
        _denied(e)
    sub = content.get_submission(db, assignment_id, data.student_id)
    if not sub:
        raise HTTPException(status_code=404, detail="该学生尚未提交作业")
    sub = content.grade(db, sub, data.score, data.feedback, current_user.id)
    return _submission_response(db, sub)

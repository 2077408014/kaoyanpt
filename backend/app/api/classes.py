from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.deps import get_current_user
from ..models.user import User
from ..services.organization_service import organization_service as svc
from ..services.class_content_service import (
    class_content_service as content,
    load_images,
)
from fastapi import File, UploadFile
from ..core.config import UPLOAD_PATH
import uuid
from ..schemas.organization import (
    JoinClassRequest, MyClassResponse, TeacherBrief,
    AnnouncementResponse, AssignmentResponse, SubmissionResponse,
    SubmissionUpsert,
)

router = APIRouter(prefix="/api/classes", tags=["classes"])


def _to_my_class(db, cls, joined_at=None, status="active") -> MyClassResponse:
    inst = svc.get_institution(db, cls.institution_id)
    teachers = svc.class_teachers(db, cls.id)
    return MyClassResponse(
        id=cls.id,
        name=cls.name,
        institution_name=inst.name if inst else None,
        join_code=cls.join_code,
        teachers=[TeacherBrief(id=t.id, username=t.username) for t in teachers],
        joined_at=joined_at,
        status=status,
    )


@router.post("/join", response_model=MyClassResponse)
async def join_class(
    data: JoinClassRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """凭码入班：任意角色都可以学生身份加入（支持双重角色）。"""
    try:
        cls = svc.join_class(db, current_user, data.code)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    member = svc.get_membership(db, cls.id, current_user.id)
    return _to_my_class(db, cls, member.joined_at if member else None,
                        member.status if member else "active")


@router.get("/my", response_model=list[MyClassResponse])
async def my_classes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = svc.my_class_memberships(db, current_user.id)
    return [_to_my_class(db, cls, joined_at, status) for cls, joined_at, status in rows]


# ---------- 班级公告（本班 active 成员可读） ----------

def _announcement_response(db, ann) -> AnnouncementResponse:
    author = db.query(User).filter(User.id == ann.author_id).first() if ann.author_id else None
    return AnnouncementResponse(
        id=ann.id, class_id=ann.class_id, author_id=ann.author_id,
        author_name=author.username if author else None,
        title=ann.title, content=ann.content,
        created_at=ann.created_at, updated_at=ann.updated_at,
    )


@router.get("/{class_id}/announcements", response_model=list[AnnouncementResponse])
async def class_announcements(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        svc.assert_active_member(db, current_user.id, class_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return [_announcement_response(db, a) for a in content.list_announcements(db, class_id)]


# ---------- 作业（本班 active 成员） ----------

def _submission_response(db, sub) -> SubmissionResponse:
    student = db.query(User).filter(User.id == sub.student_id).first()
    return SubmissionResponse(
        id=sub.id, assignment_id=sub.assignment_id, student_id=sub.student_id,
        student_name=student.username if student else None,
        content=sub.content, images=load_images(sub.images), submitted_at=sub.submitted_at,
        score=sub.score, feedback=sub.feedback, graded_at=sub.graded_at,
    )


def _student_assignment_response(db, asm, student_id: int) -> AssignmentResponse:
    sub = content.get_submission(db, asm.id, student_id)
    return AssignmentResponse(
        id=asm.id, class_id=asm.class_id, title=asm.title, content=asm.content,
        images=load_images(asm.images),
        due_at=asm.due_at, created_at=asm.created_at,
        my_submission=_submission_response(db, sub) if sub else None,
    )


@router.get("/{class_id}/assignments", response_model=list[AssignmentResponse])
async def class_assignments(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        svc.assert_active_member(db, current_user.id, class_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return [
        _student_assignment_response(db, a, current_user.id)
        for a in content.list_assignments(db, class_id)
    ]


@router.get("/assignments/{assignment_id}", response_model=AssignmentResponse)
async def get_assignment(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asm = content.get_assignment(db, assignment_id)
    if not asm:
        raise HTTPException(status_code=404, detail="作业不存在")
    try:
        svc.assert_active_member(db, current_user.id, asm.class_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return _student_assignment_response(db, asm, current_user.id)


@router.post("/assignments/{assignment_id}/submissions", response_model=SubmissionResponse)
async def submit_assignment(
    assignment_id: int,
    data: SubmissionUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asm = content.get_assignment(db, assignment_id)
    if not asm:
        raise HTTPException(status_code=404, detail="作业不存在")
    if not data.content.strip() and not data.images:
        raise HTTPException(status_code=400, detail="作业内容和图片至少填写一项")
    try:
        svc.assert_active_member(db, current_user.id, asm.class_id)
        sub = content.submit(db, asm, current_user.id, data.content, data.images)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _submission_response(db, sub)


@router.post("/assignments/upload-image")
async def upload_submission_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
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

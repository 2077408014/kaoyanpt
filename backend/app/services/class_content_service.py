"""班级公告与作业服务。

权限前提由 API 层保证：
- 写操作：organization_service.assert_can_manage_class（本班教师 / 超管）
- 学生读写：organization_service.assert_active_member（本班 active 成员）
"""
import json
from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..models.user import User
from ..models.organization import Class, ClassAnnouncement, Assignment, AssignmentSubmission
from .organization_service import naive_local, UNSET


def dump_images(images) -> str:
    """作业图片列表 -> JSON 存储。仅保留字符串项。"""
    return json.dumps([str(p) for p in (images or []) if p], ensure_ascii=False)


def load_images(raw) -> list[str]:
    """JSON 存储 -> 作业图片列表，坏数据容错为空列表。"""
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    return [p for p in data if isinstance(p, str)] if isinstance(data, list) else []


class ClassContentService:
    # ---------- 公告 ----------
    def create_announcement(
        self, db: Session, class_id: int, author_id: int, title: str, content: str
    ) -> ClassAnnouncement:
        ann = ClassAnnouncement(
            class_id=class_id, author_id=author_id,
            title=title.strip(), content=content or "",
        )
        db.add(ann)
        db.commit()
        db.refresh(ann)
        return ann

    def list_announcements(self, db: Session, class_id: int) -> list[ClassAnnouncement]:
        return (
            db.query(ClassAnnouncement)
            .filter(ClassAnnouncement.class_id == class_id)
            .order_by(ClassAnnouncement.created_at.desc())
            .all()
        )

    def get_announcement(self, db: Session, announcement_id: int) -> Optional[ClassAnnouncement]:
        return db.query(ClassAnnouncement).filter(ClassAnnouncement.id == announcement_id).first()

    def update_announcement(
        self, db: Session, ann: ClassAnnouncement, title: str, content: str
    ) -> ClassAnnouncement:
        ann.title = title.strip()
        ann.content = content or ""
        db.commit()
        db.refresh(ann)
        return ann

    def delete_announcement(self, db: Session, ann: ClassAnnouncement) -> None:
        db.delete(ann)
        db.commit()

    # ---------- 作业 ----------
    def create_assignment(
        self, db: Session, class_id: int, creator_id: int,
        title: str, content: str, due_at: Optional[datetime],
        images: Optional[list[str]] = None,
    ) -> Assignment:
        asm = Assignment(
            class_id=class_id, creator_id=creator_id,
            title=title.strip(), content=content or "",
            images=dump_images(images),
            due_at=naive_local(due_at),
        )
        db.add(asm)
        db.commit()
        db.refresh(asm)
        return asm

    def list_assignments(self, db: Session, class_id: int) -> list[Assignment]:
        return (
            db.query(Assignment)
            .filter(Assignment.class_id == class_id)
            .order_by(Assignment.created_at.desc())
            .all()
        )

    def get_assignment(self, db: Session, assignment_id: int) -> Optional[Assignment]:
        return db.query(Assignment).filter(Assignment.id == assignment_id).first()

    def update_assignment(
        self, db: Session, asm: Assignment,
        title: object = UNSET, content: object = UNSET, due_at: object = UNSET,
        images: object = UNSET,
    ) -> Assignment:
        if title is not UNSET:
            asm.title = str(title).strip()
        if content is not UNSET:
            asm.content = content or ""
        if images is not UNSET:
            asm.images = dump_images(images)
        if due_at is not UNSET:
            asm.due_at = naive_local(due_at)  # 显式传 None 即清空截止时间
        db.commit()
        db.refresh(asm)
        return asm

    def delete_assignment(self, db: Session, asm: Assignment) -> None:
        db.delete(asm)
        db.commit()

    def is_overdue(self, asm: Assignment) -> bool:
        return asm.due_at is not None and datetime.now() >= naive_local(asm.due_at)

    # ---------- 提交 ----------
    def get_submission(
        self, db: Session, assignment_id: int, student_id: int
    ) -> Optional[AssignmentSubmission]:
        return db.query(AssignmentSubmission).filter(
            AssignmentSubmission.assignment_id == assignment_id,
            AssignmentSubmission.student_id == student_id,
        ).first()

    def submit(
        self, db: Session, asm: Assignment, student_id: int, content: str,
        images: Optional[list[str]] = None,
    ) -> AssignmentSubmission:
        if self.is_overdue(asm):
            raise ValueError("已过作业截止时间，无法提交")
        sub = self.get_submission(db, asm.id, student_id)
        if sub:
            sub.content = content
            sub.images = dump_images(images)
            sub.submitted_at = func.now()
            # 重新提交后旧评分失效
            sub.score = None
            sub.feedback = None
            sub.graded_at = None
            sub.graded_by = None
        else:
            sub = AssignmentSubmission(
                assignment_id=asm.id, student_id=student_id, content=content,
                images=dump_images(images),
            )
            db.add(sub)
        db.commit()
        db.refresh(sub)
        return sub

    def list_submissions(self, db: Session, assignment_id: int) -> list[AssignmentSubmission]:
        return (
            db.query(AssignmentSubmission)
            .filter(AssignmentSubmission.assignment_id == assignment_id)
            .order_by(AssignmentSubmission.submitted_at.asc())
            .all()
        )

    def grade(
        self, db: Session, sub: AssignmentSubmission,
        score: int, feedback: Optional[str], graded_by: int,
    ) -> AssignmentSubmission:
        sub.score = score
        sub.feedback = feedback
        sub.graded_at = datetime.now()
        sub.graded_by = graded_by
        db.commit()
        db.refresh(sub)
        return sub


class_content_service = ClassContentService()

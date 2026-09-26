from sqlalchemy import (
    Column, Integer, String, DateTime, Text, ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.sql import func
from ..core.database import Base

# 角色常量
ROLE_STUDENT = "student"
ROLE_TEACHER = "teacher"
ROLE_INSTITUTION_ADMIN = "institution_admin"
ROLE_SUPER_ADMIN = "super_admin"

STAFF_ROLES = (ROLE_TEACHER, ROLE_INSTITUTION_ADMIN)
ALL_ROLES = (ROLE_STUDENT, ROLE_TEACHER, ROLE_INSTITUTION_ADMIN, ROLE_SUPER_ADMIN)

# 班级成员状态
MEMBER_ACTIVE = "active"
MEMBER_SUSPENDED = "suspended"
MEMBER_STATUSES = (MEMBER_ACTIVE, MEMBER_SUSPENDED)


class Institution(Base):
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Class(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    join_code = Column(String(8), unique=True, nullable=False, index=True)
    code_expires_at = Column(DateTime(timezone=True), nullable=True)   # 入班码过期时间，NULL=长期有效
    code_max_uses = Column(Integer, nullable=True)                    # 入班码可用次数，NULL=不限
    code_uses = Column(Integer, nullable=False, default=0, server_default="0")  # 凭码新加入次数
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("institution_id", "name", name="uq_class_institution_name"),
    )


class ClassTeacher(Base):
    __tablename__ = "class_teachers"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("class_id", "teacher_id", name="uq_class_teacher"),
    )


class ClassStudent(Base):
    __tablename__ = "class_students"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default=MEMBER_ACTIVE, server_default=MEMBER_ACTIVE)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("class_id", "student_id", name="uq_class_student"),
    )


class ClassAnnouncement(Base):
    """班级公告：任课教师/超管发布，本班学生只读。"""
    __tablename__ = "class_announcements"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Assignment(Base):
    """班级作业：教师发布，学生提交，教师打分评语。"""
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True)
    creator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False, default="")
    images = Column(Text, nullable=False, default="[]")  # JSON 数组：相对图片路径（/uploads 下）
    due_at = Column(DateTime(timezone=True), nullable=True)  # NULL 表示不设截止时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AssignmentSubmission(Base):
    __tablename__ = "assignment_submissions"

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False, default="")
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    score = Column(Integer, nullable=True)
    feedback = Column(Text, nullable=True)
    graded_at = Column(DateTime(timezone=True), nullable=True)
    graded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        UniqueConstraint("assignment_id", "student_id", name="uq_assignment_student"),
    )

"""机构、班级、员工账号、入班与权限集合服务。"""
import random
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.user import User
from ..models.organization import (
    Institution, Class, ClassTeacher, ClassStudent,
    ROLE_TEACHER, ROLE_INSTITUTION_ADMIN, ROLE_SUPER_ADMIN, ROLE_STUDENT,
    STAFF_ROLES,
    MEMBER_ACTIVE, MEMBER_SUSPENDED,
)
from ..core.security import get_password_hash

# 去除易混字符：字母去 I/O，数字去 0/1
_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

# 更新班级设置时区分"未传"与"显式传 null（清除）"
UNSET = object()


def naive_local(dt: datetime) -> datetime:
    """统一转成本地 naive 时间，便于与 SQLite 中 datetime.now() 写入值比较。"""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone().replace(tzinfo=None)
    return dt


class OrganizationService:
    # ---------- 入班码 ----------
    def generate_join_code(self, db: Session, length: int = 6) -> str:
        for _ in range(5):
            code = "".join(random.choices(_CODE_ALPHABET, k=length))
            if not db.query(Class).filter(Class.join_code == code).first():
                return code
        raise ValueError("入班码生成失败，请重试")

    def normalize_code(self, code: str) -> str:
        return (code or "").strip().upper()

    # ---------- 机构 ----------
    def create_institution(self, db: Session, name: str) -> Institution:
        name = name.strip()
        if db.query(Institution).filter(Institution.name == name).first():
            raise ValueError("机构名称已存在")
        inst = Institution(name=name)
        db.add(inst)
        db.commit()
        db.refresh(inst)
        return inst

    def list_institutions(self, db: Session) -> list[Institution]:
        return db.query(Institution).order_by(Institution.id.asc()).all()

    def get_institution(self, db: Session, institution_id: int) -> Optional[Institution]:
        return db.query(Institution).filter(Institution.id == institution_id).first()

    # ---------- 班级 ----------
    def create_class(
        self, db: Session, institution_id: int, name: str,
        code_expires_at: Optional[datetime] = None,
        code_max_uses: Optional[int] = None,
    ) -> Class:
        name = name.strip()
        if not self.get_institution(db, institution_id):
            raise ValueError("所属机构不存在")
        exists = db.query(Class).filter(
            Class.institution_id == institution_id, Class.name == name
        ).first()
        if exists:
            raise ValueError("该机构下已存在同名班级")
        cls = Class(
            name=name,
            institution_id=institution_id,
            join_code=self.generate_join_code(db),
            code_expires_at=naive_local(code_expires_at),
            code_max_uses=code_max_uses,
        )
        db.add(cls)
        db.commit()
        db.refresh(cls)
        return cls

    def update_class(
        self, db: Session, class_id: int,
        name: object = UNSET,
        code_expires_at: object = UNSET,
        code_max_uses: object = UNSET,
    ) -> Class:
        cls = self.get_class(db, class_id)
        if not cls:
            raise ValueError("班级不存在")
        if name is not UNSET:
            new_name = str(name).strip()
            dup = db.query(Class).filter(
                Class.institution_id == cls.institution_id,
                Class.name == new_name,
                Class.id != class_id,
            ).first()
            if dup:
                raise ValueError("该机构下已存在同名班级")
            cls.name = new_name
        if code_expires_at is not UNSET:
            cls.code_expires_at = naive_local(code_expires_at)
        if code_max_uses is not UNSET:
            value = code_max_uses
            if value is not None and int(value) <= 0:
                raise ValueError("入班码次数上限必须大于 0")
            cls.code_max_uses = None if value is None else int(value)
        db.commit()
        db.refresh(cls)
        return cls

    def reset_join_code(self, db: Session, class_id: int) -> Class:
        cls = self.get_class(db, class_id)
        if not cls:
            raise ValueError("班级不存在")
        cls.join_code = self.generate_join_code(db)
        db.commit()
        db.refresh(cls)
        return cls

    def list_classes(
        self, db: Session, institution_id: Optional[int] = None
    ) -> list[Class]:
        q = db.query(Class)
        if institution_id is not None:
            q = q.filter(Class.institution_id == institution_id)
        return q.order_by(Class.institution_id.asc(), Class.id.asc()).all()

    def get_class(self, db: Session, class_id: int) -> Optional[Class]:
        return db.query(Class).filter(Class.id == class_id).first()

    def get_class_by_code(self, db: Session, code: str) -> Optional[Class]:
        return db.query(Class).filter(Class.join_code == self.normalize_code(code)).first()

    def class_teachers(self, db: Session, class_id: int) -> list[User]:
        rows = (
            db.query(User)
            .join(ClassTeacher, ClassTeacher.teacher_id == User.id)
            .filter(ClassTeacher.class_id == class_id)
            .order_by(User.id.asc())
            .all()
        )
        return rows

    def class_students(self, db: Session, class_id: int) -> list[tuple]:
        rows = (
            db.query(User, ClassStudent.joined_at, ClassStudent.status)
            .join(ClassStudent, ClassStudent.student_id == User.id)
            .filter(ClassStudent.class_id == class_id)
            .order_by(ClassStudent.joined_at.asc())
            .all()
        )
        return rows  # list of (User, joined_at, status)

    def get_membership(
        self, db: Session, class_id: int, student_id: int
    ) -> Optional[ClassStudent]:
        return db.query(ClassStudent).filter(
            ClassStudent.class_id == class_id,
            ClassStudent.student_id == student_id,
        ).first()

    def assert_active_member(self, db: Session, user_id: int, class_id: int) -> ClassStudent:
        """学生视角内容访问校验：须为本班 active 成员。"""
        member = self.get_membership(db, class_id, user_id)
        if not member:
            raise PermissionError("你还没有加入该班级")
        if member.status == MEMBER_SUSPENDED:
            raise PermissionError("你在该班级已被暂停，请联系任课教师")
        return member

    def assert_can_manage_class(self, db: Session, user: User, class_id: int) -> Class:
        """内容管理（公告/作业/成员）权限：本班任课教师或超管。"""
        cls = self.get_class(db, class_id)
        if not cls:
            raise ValueError("班级不存在")
        if user.role == ROLE_SUPER_ADMIN:
            return cls
        if user.role != ROLE_TEACHER:
            raise PermissionError("无权限操作该班级")
        assigned = db.query(ClassTeacher).filter(
            ClassTeacher.class_id == class_id,
            ClassTeacher.teacher_id == user.id,
        ).first()
        if not assigned:
            raise PermissionError("无权限操作该班级")
        return cls

    def student_count(self, db: Session, class_id: int) -> int:
        return (
            db.query(func.count(ClassStudent.id))
            .filter(
                ClassStudent.class_id == class_id,
                ClassStudent.status == MEMBER_ACTIVE,
            )
            .scalar()
        )

    def teacher_count(self, db: Session, class_id: int) -> int:
        return (
            db.query(func.count(ClassTeacher.id))
            .filter(ClassTeacher.class_id == class_id)
            .scalar()
        )

    # ---------- 员工账号 ----------
    def create_staff_user(
        self, db: Session, username: str, email: str, password: str,
        role: str, institution_id: int,
    ) -> User:
        if role not in STAFF_ROLES:
            raise ValueError("只能创建教师或机构管理者账号")
        if not self.get_institution(db, institution_id):
            raise ValueError("所属机构不存在")
        existing = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing:
            raise ValueError("用户名或邮箱已存在")
        user = User(
            username=username,
            email=email,
            password=get_password_hash(password),
            role=role,
            institution_id=institution_id,
            must_change_password=True,  # 管理员创建的账号首次登录强制改密
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def get_staff_user(self, db: Session, user_id: int) -> Optional[User]:
        user = db.query(User).filter(User.id == user_id).first()
        return user if user and user.role in STAFF_ROLES else None

    def update_staff_user(
        self, db: Session, user: User,
        username: Optional[str] = None, email: Optional[str] = None,
        password: Optional[str] = None, role: Optional[str] = None,
        institution_id: Optional[int] = None,
    ) -> User:
        if username and username != user.username:
            if db.query(User).filter(
                User.id != user.id, User.username == username
            ).first():
                raise ValueError("用户名已存在")
            user.username = username
        if email and email != user.email:
            if db.query(User).filter(
                User.id != user.id, User.email == email
            ).first():
                raise ValueError("邮箱已存在")
            user.email = email
        if role is not None:
            if role not in STAFF_ROLES:
                raise ValueError("只能设置为教师或机构管理者")
            user.role = role
        if institution_id is not None and institution_id != user.institution_id:
            if not self.get_institution(db, institution_id):
                raise ValueError("所属机构不存在")
            user.institution_id = institution_id
        if password:
            user.password = get_password_hash(password)
            user.must_change_password = True  # 管理员重置后首次登录强制改密
        db.commit()
        db.refresh(user)
        return user

    def delete_staff_user(self, db: Session, user: User) -> None:
        # SQLite 未强制外键级联，先手动清理班级关系
        # 任教关系；双重角色账号作为学生入班的成员关系
        db.query(ClassTeacher).filter(
            ClassTeacher.teacher_id == user.id
        ).delete(synchronize_session=False)
        db.query(ClassStudent).filter(
            ClassStudent.student_id == user.id
        ).delete(synchronize_session=False)
        db.delete(user)
        db.commit()

    def list_staff_users(
        self, db: Session, role: Optional[str] = None,
        institution_id: Optional[int] = None,
    ) -> list[User]:
        q = db.query(User).filter(User.role.in_(STAFF_ROLES))
        if role:
            q = q.filter(User.role == role)
        if institution_id is not None:
            q = q.filter(User.institution_id == institution_id)
        return q.order_by(User.institution_id.asc(), User.id.asc()).all()

    # ---------- 教师分配 ----------
    def assign_teacher(self, db: Session, class_id: int, teacher_id: int) -> None:
        cls = self.get_class(db, class_id)
        if not cls:
            raise ValueError("班级不存在")
        teacher = db.query(User).filter(User.id == teacher_id).first()
        if not teacher:
            raise ValueError("教师账号不存在")
        if teacher.role != ROLE_TEACHER:
            raise ValueError("该账号不是教师，无法分配")
        if teacher.institution_id != cls.institution_id:
            raise ValueError("教师与班级不属于同一机构")
        exists = db.query(ClassTeacher).filter(
            ClassTeacher.class_id == class_id,
            ClassTeacher.teacher_id == teacher_id,
        ).first()
        if exists:
            return  # 幂等
        db.add(ClassTeacher(class_id=class_id, teacher_id=teacher_id))
        db.commit()

    def unassign_teacher(self, db: Session, class_id: int, teacher_id: int) -> None:
        deleted = (
            db.query(ClassTeacher)
            .filter(
                ClassTeacher.class_id == class_id,
                ClassTeacher.teacher_id == teacher_id,
            )
            .delete()
        )
        db.commit()
        if not deleted:
            raise ValueError("该教师未分配到此班级")

    # ---------- 学生入班 / 退班 ----------
    def join_class(self, db: Session, user: User, code: str) -> Class:
        """凭码入班。任意角色均可作为学生加入（双重角色）。

        - 入班码大小写不敏感；重复加入幂等
        - 被暂停的成员拒绝凭码重新加入，须教师恢复
        - 校验入班码有效期与次数上限（仅对新加入计数）
        """
        cls = self.get_class_by_code(db, code)
        if not cls:
            raise ValueError("邀请码无效")
        existing = self.get_membership(db, cls.id, user.id)
        if existing:
            if existing.status == MEMBER_SUSPENDED:
                raise PermissionError("你在该班级已被暂停，请联系任课教师恢复")
            return cls
        if cls.code_expires_at is not None and datetime.now() >= naive_local(cls.code_expires_at):
            raise ValueError("入班码已过期")
        if cls.code_max_uses is not None and cls.code_uses >= cls.code_max_uses:
            raise ValueError("入班码使用次数已达上限")
        # 游离学生凭码入班时自动归属班级机构（不阻止跨机构重复入班）
        if user.role == ROLE_STUDENT and user.institution_id is None:
            user.institution_id = cls.institution_id
        db.add(ClassStudent(class_id=cls.id, student_id=user.id, status=MEMBER_ACTIVE))
        cls.code_uses = (cls.code_uses or 0) + 1
        db.commit()
        db.refresh(cls)
        return cls

    def add_student_by_email(
        self, db: Session, operator: User, class_id: int, email: str
    ) -> User:
        """教师/超管按邮箱手动把已有账号加入班级（幂等）。"""
        cls = self.assert_can_manage_class(db, operator, class_id)
        email = email.strip().lower()
        student = db.query(User).filter(func.lower(User.email) == email).first()
        if not student:
            raise ValueError("该邮箱尚未注册，请让学生先注册账号")
        member = self.get_membership(db, class_id, student.id)
        if member:
            if member.status == MEMBER_SUSPENDED:
                raise ValueError("该学生已被暂停，请先恢复后再添加")
            return student  # 已在班内，幂等
        if student.institution_id is None:
            # 游离学生自动归属到本班机构；教职工账号不动其归属
            if student.role == ROLE_STUDENT:
                student.institution_id = cls.institution_id
        elif student.institution_id != cls.institution_id:
            raise ValueError("该学生属于其他机构，无法加入本班")
        db.add(ClassStudent(class_id=class_id, student_id=student.id, status=MEMBER_ACTIVE))
        db.commit()
        db.refresh(student)
        return student

    def set_member_status(
        self, db: Session, operator: User, class_id: int, student_id: int, status: str
    ) -> None:
        self.assert_can_manage_class(db, operator, class_id)
        member = self.get_membership(db, class_id, student_id)
        if not member:
            raise ValueError("该学生不在此班级中")
        if member.status == status:
            return
        member.status = status
        db.commit()

    def my_classes(self, db: Session, student_id: int) -> list[Class]:
        return (
            db.query(Class)
            .join(ClassStudent, ClassStudent.class_id == Class.id)
            .filter(ClassStudent.student_id == student_id)
            .order_by(ClassStudent.joined_at.desc())
            .all()
        )

    def my_class_memberships(self, db: Session, student_id: int) -> list[tuple]:
        """返回 (Class, joined_at, status)，供学生端展示成员状态。"""
        return (
            db.query(Class, ClassStudent.joined_at, ClassStudent.status)
            .join(ClassStudent, ClassStudent.class_id == Class.id)
            .filter(ClassStudent.student_id == student_id)
            .order_by(ClassStudent.joined_at.desc())
            .all()
        )

    def remove_student_from_class(
        self, db: Session, operator: User, class_id: int, student_id: int
    ) -> None:
        """移出学生：仅班级任课教师（或超管）可操作；只删成员关系，不删学习数据。"""
        self.assert_can_manage_class(db, operator, class_id)
        deleted = (
            db.query(ClassStudent)
            .filter(
                ClassStudent.class_id == class_id,
                ClassStudent.student_id == student_id,
            )
            .delete()
        )
        db.commit()
        if not deleted:
            raise ValueError("该学生不在此班级中")

    # ---------- 权限集合（行级隔离核心） ----------
    def is_super_admin(self, user: User) -> bool:
        return user.role == ROLE_SUPER_ADMIN

    def get_teacher_class_ids(self, db: Session, teacher_id: int) -> set[int]:
        rows = (
            db.query(ClassTeacher.class_id)
            .filter(ClassTeacher.teacher_id == teacher_id)
            .all()
        )
        return {r[0] for r in rows}

    def _student_ids_for_classes(self, db: Session, class_ids) -> set[int]:
        if not class_ids:
            return set()
        rows = (
            db.query(ClassStudent.student_id)
            .filter(ClassStudent.class_id.in_(class_ids))
            .distinct()
            .all()
        )
        return {r[0] for r in rows}

    def get_teacher_student_ids(self, db: Session, user: User) -> Optional[set[int]]:
        """教师可见学生集合；超管返回 None（全集，不限）。"""
        if self.is_super_admin(user):
            return None
        class_ids = self.get_teacher_class_ids(db, user.id)
        return self._student_ids_for_classes(db, class_ids)

    def get_institution_class_ids(self, db: Session, institution_id: int) -> set[int]:
        rows = (
            db.query(Class.id)
            .filter(Class.institution_id == institution_id)
            .all()
        )
        return {r[0] for r in rows}

    def get_institution_student_ids(self, db: Session, user: User) -> Optional[set[int]]:
        """机构管理者可见学生集合；超管返回 None（全集，不限）。"""
        if self.is_super_admin(user):
            return None
        class_ids = self.get_institution_class_ids(db, user.institution_id)
        return self._student_ids_for_classes(db, class_ids)

    def list_teacher_classes(self, db: Session, user: User) -> list[Class]:
        if self.is_super_admin(user):
            return self.list_classes(db)
        return (
            db.query(Class)
            .join(ClassTeacher, ClassTeacher.class_id == Class.id)
            .filter(ClassTeacher.teacher_id == user.id)
            .order_by(Class.id.asc())
            .all()
        )

    def list_institution_classes(self, db: Session, user: User) -> list[Class]:
        if self.is_super_admin(user):
            return self.list_classes(db)
        return self.list_classes(db, institution_id=user.institution_id)

    def assert_class_in_scope(self, db: Session, user: User, class_id: int) -> None:
        """教师/机构视角的班级归属校验，越权抛 PermissionError；超管放行。"""
        if self.is_super_admin(user):
            if not self.get_class(db, class_id):
                raise ValueError("班级不存在")
            return
        if user.role == ROLE_TEACHER:
            if class_id not in self.get_teacher_class_ids(db, user.id):
                raise PermissionError("无权限查看该班级")
        elif user.role == ROLE_INSTITUTION_ADMIN:
            cls = self.get_class(db, class_id)
            if not cls:
                raise ValueError("班级不存在")
            if cls.institution_id != user.institution_id:
                raise PermissionError("无权限查看该班级")

    def assert_student_in_scope(self, db: Session, user: User, student_id: int,
                                student_ids: Optional[set[int]]) -> None:
        if self.is_super_admin(user):
            return
        if student_ids is None or student_id not in student_ids:
            raise PermissionError("无权限查看该学生")


organization_service = OrganizationService()

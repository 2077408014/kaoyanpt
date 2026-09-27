from typing import Optional, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field


# ---------- 机构 ----------

class InstitutionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class InstitutionResponse(BaseModel):
    id: int
    name: str
    created_at: Optional[datetime] = None
    class_count: Optional[int] = None

    class Config:
        from_attributes = True


# ---------- 班级 ----------

class ClassCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    institution_id: int
    code_expires_at: Optional[datetime] = None
    code_max_uses: Optional[int] = Field(default=None, ge=1)


class TeacherBrief(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True


class StudentBrief(BaseModel):
    id: int
    username: str
    joined_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ClassResponse(BaseModel):
    id: int
    name: str
    institution_id: int
    institution_name: Optional[str] = None
    join_code: str
    code_expires_at: Optional[datetime] = None
    code_max_uses: Optional[int] = None
    code_uses: int = 0
    student_count: int = 0
    teacher_count: int = 0
    teachers: List[TeacherBrief] = []
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ClassSettingsUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    code_expires_at: Optional[datetime] = None
    code_max_uses: Optional[int] = Field(default=None, ge=1)


class ClassListResponse(BaseModel):
    id: int
    name: str
    institution_id: int
    institution_name: Optional[str] = None
    join_code: Optional[str] = None
    code_expires_at: Optional[datetime] = None
    code_max_uses: Optional[int] = None
    code_uses: int = 0
    student_count: int = 0
    teacher_count: int = 0


# ---------- 员工账号（教师 / 机构管理者） ----------

class StaffUserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    email: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6)
    role: Literal["teacher", "institution_admin"]
    institution_id: int


class StaffUserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=1, max_length=50)
    email: Optional[str] = Field(None, min_length=3, max_length=100)
    password: Optional[str] = Field(None, min_length=6)  # 传值=重置密码，None=不改
    role: Optional[Literal["teacher", "institution_admin"]] = None
    institution_id: Optional[int] = None


class StaffUserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    institution_id: int
    institution_name: Optional[str] = None
    is_active: bool = True
    must_change_password: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TeacherAssignRequest(BaseModel):
    teacher_id: int


# ---------- 学生入班 ----------

class JoinClassRequest(BaseModel):
    code: str = Field(..., min_length=4, max_length=8)


class MyClassResponse(BaseModel):
    id: int
    name: str
    institution_name: Optional[str] = None
    join_code: str
    teachers: List[TeacherBrief] = []
    joined_at: Optional[datetime] = None
    status: str = "active"


# ---------- 学生学习情况 ----------

class StudentSummary(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    joined_at: Optional[datetime] = None
    status: str = "active"
    study_time_7d: int = 0           # 近7天学习总时长（分钟）
    words_7d: int = 0                # 近7天学习单词数
    questions_7d: int = 0            # 近7天做题数
    total_mistakes: int = 0          # 累计错题数
    supervision_abnormal: int = 0    # 累计监督异常次数


class DailyPoint(BaseModel):
    date: str
    study_time: int = 0
    words: int = 0
    questions: int = 0
    mistakes: int = 0
    abnormal: int = 0


class StudentOverview(BaseModel):
    id: int
    username: str
    study_time_7d: int = 0
    words_7d: int = 0
    questions_7d: int = 0
    total_mistakes: int = 0
    mastered_mistakes: int = 0
    supervision_abnormal: int = 0
    mastery_distribution: dict = {}
    daily: List[DailyPoint] = []


class ClassSummary(BaseModel):
    id: int
    name: str
    institution_id: int
    institution_name: Optional[str] = None
    join_code: Optional[str] = None
    code_expires_at: Optional[datetime] = None
    code_max_uses: Optional[int] = None
    code_uses: int = 0
    student_count: int = 0
    avg_study_time_7d: float = 0.0
    avg_words_7d: float = 0.0
    avg_questions_7d: float = 0.0
    avg_mistakes: float = 0.0
    total_mistakes: int = 0
    supervision_abnormal: int = 0


# ---------- 成员管理 ----------

class AddStudentRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=100)


# ---------- 班级公告 ----------

class AnnouncementCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(default="", max_length=5000)


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    content: Optional[str] = Field(default=None, max_length=5000)


class AnnouncementResponse(BaseModel):
    id: int
    class_id: int
    author_id: Optional[int] = None
    author_name: Optional[str] = None
    title: str
    content: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---------- 作业 ----------

class AssignmentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(default="", max_length=10000)
    images: List[str] = Field(default_factory=list, max_length=9)
    due_at: Optional[datetime] = None


class AssignmentUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    content: Optional[str] = Field(default=None, max_length=10000)
    images: Optional[List[str]] = Field(default=None, max_length=9)
    due_at: Optional[datetime] = None


class SubmissionUpsert(BaseModel):
    # 允许空内容但必须有图片，非空校验在 API 层做
    content: str = Field(default="", max_length=10000)
    images: List[str] = Field(default_factory=list, max_length=9)


class GradeRequest(BaseModel):
    student_id: int
    score: int = Field(..., ge=0, le=100)
    feedback: Optional[str] = Field(default=None, max_length=2000)


class SubmissionResponse(BaseModel):
    id: int
    assignment_id: int
    student_id: int
    student_name: Optional[str] = None
    content: str
    images: List[str] = []
    submitted_at: Optional[datetime] = None
    score: Optional[int] = None
    feedback: Optional[str] = None
    graded_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AssignmentResponse(BaseModel):
    id: int
    class_id: int
    title: str
    content: str = ""
    images: List[str] = []
    due_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    # 教师视角
    submission_count: Optional[int] = None
    graded_count: Optional[int] = None
    # 学生视角
    my_submission: Optional[SubmissionResponse] = None

    class Config:
        from_attributes = True


# ---------- 机构管理者写操作 ----------

class InstitutionClassCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    institution_id: Optional[int] = None  # 超管必填；机构管理者忽略此字段
    code_expires_at: Optional[datetime] = None
    code_max_uses: Optional[int] = Field(default=None, ge=1)


class InstitutionTeacherCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    email: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6)


class InstitutionTeacherUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=1, max_length=50)
    email: Optional[str] = Field(None, min_length=3, max_length=100)
    password: Optional[str] = Field(None, min_length=6)  # 传值=重置密码，None=不改

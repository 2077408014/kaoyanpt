# 背诵功能升级（借鉴 ToastFish）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 KaoYanPT 单词背诵升级为 ToastFish 风格：SM2+ 四档评分、站内沉浸式弹卡、学后测验（中译英/英译中）、背诵记录导出与重新导入。

**Architecture:** 后端在 `backend/app/utils/srs.py` 实现纯逻辑 SM2+ 状态机，`word_service.py` 集成到 `UserWord` 并新增 `StudyRecord` 审计表；新增 8 个 API。前端升级 `WordModule.vue` 为四档+测验，新增 `PushCards.vue`（弹卡+浏览器通知）与 `RecordsModule.vue`，复用共享的 `QuizDialog.vue`。

**Tech Stack:** Python (FastAPI, SQLAlchemy 2.0, openpyxl 新增), Vue 3 `<script setup>` + Element Plus + TypeScript。

**设计文档:** `docs/superpowers/specs/2026-09-24-word-recitation-toastfish-design.md`

## Global Constraints

- 后端测试遵循仓库模式：独立脚本可直接 `python3 backend/tests/xxx.py` 运行，函数名 `test_*`（可用 pytest 但机器上未装 pytest，统一用脚本方式验证）
- 除 `backend/app/utils/srs.py` 外，`backend/app/utils/memory_curve.py` 的 `calculate_next_review_date`（错题用）与 `calculate_next_review`（政治用）不得删除，仅不再被 word_service 使用
- 旧三档评分必须兼容：认识→认识、模糊→困难、不认识→忘记（`OLD_RATING_MAP`）
- 事件审计表 `study_records` 记录每次 study/quiz 事件；source ∈ card/push/quiz
- 前端用 `npm run build`（vue-tsc + vite build）验证；不引入新前端依赖
- 沿用仓库风格：中文注释/文档字符串；SQLAlchemy 2.0 `db.query` 风格
- 分级值：忘记=0.4, 困难=0.6, 一般=0.8, 认识=1.0；correct 阈值 0.7
- 掌握度标签由 srs_status 派生：new→陌生, step1→认识, step2→熟悉, reviewed→掌握, relearn1→认识, relearn2→熟悉

---

### Task 1: SM2+ 引擎（纯逻辑）

**Files:**
- Create: `backend/app/utils/srs.py`
- Test: `backend/tests/test_srs.py`

**Interfaces:**
- Consumes: 无（纯函数）
- Produces:
  - `RATING_SCORES: dict[str, float]` — 四档分值
  - `TRANSITIONS: dict[str, dict[str, tuple[float, str]]]` — (status, rating) → (due_minutes|None, new_status)
  - `OLD_RATING_MAP: dict[str, str]` — 旧三档→新四档
  - `DEFAULT_DIFFICULTY = 0.3`, `DEFAULT_DAYS_BETWEEN_REVIEWS = 3.0`, `CORRECT_THRESHOLD = 0.7`
  - `rate_srs(status, rating, difficulty=0.3, days_between_reviews=3.0, elapsed_days=0, today=None, rng=None) -> dict`，返回 `{new_status, due_minutes, next_review_date, difficulty, days_between_reviews}`
  - `mastery_for_srs_status(status: str) -> str` — 掌握度标签

- [ ] **Step 1: 写失败的测试**

创建 `backend/tests/test_srs.py`：

```python
"""SM2+ 四档评分引擎测试。

运行方式：python3 backend/tests/test_srs.py
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, timedelta

from app.utils.srs import (
    RATING_SCORES, OLD_RATING_MAP, mastery_for_srs_status,
    rate_srs, DEFAULT_DAYS_BETWEEN_REVIEWS,
)


def test_ratings_scores():
    assert RATING_SCORES == {"忘记": 0.4, "困难": 0.6, "一般": 0.8, "认识": 1.0}


def test_legacy_map():
    assert OLD_RATING_MAP == {"认识": "认识", "模糊": "困难", "不认识": "忘记"}


def test_new_easy_becomes_reviewed_baseline_interval():
    out = rate_srs("new", "认识")
    assert out["new_status"] == "reviewed"
    assert out["due_minutes"] is None
    assert out["next_review_date"] == date.today() + timedelta(days=3)


def test_new_good_moves_to_step2_within_session():
    out = rate_srs("new", "一般")
    assert out["new_status"] == "step2"
    assert out["due_minutes"] == 10.0
    assert out["next_review_date"] is None


def test_step2_again_resets_to_step1():
    out = rate_srs("step2", "忘记")
    assert out["new_status"] == "step1"
    assert out["due_minutes"] == 1.0


def test_reviewed_hard_interval_shrinks():
    before = {"difficulty": 0.3, "days_between_reviews": 5.0}
    out = rate_srs("reviewed", "困难", difficulty=before["difficulty"],
                   days_between_reviews=before["days_between_reviews"], elapsed_days=3)
    assert out["new_status"] == "reviewed"
    assert out["days_between_reviews"] < before["days_between_reviews"]
    assert out["next_review_date"] is not None


def test_reviewed_again_goes_relearn():
    out = rate_srs("reviewed", "忘记", days_between_reviews=5.0, elapsed_days=3)
    assert out["new_status"] == "relearn1"
    assert out["due_minutes"] == 10.0


def test_relearn2_good_becomes_reviewed():
    out = rate_srs("relearn2", "一般")
    assert out["new_status"] == "reviewed"
    assert out["next_review_date"] is not None


def test_mastery_mapping():
    assert mastery_for_srs_status("new") == "陌生"
    assert mastery_for_srs_status("step1") == "认识"
    assert mastery_for_srs_status("step2") == "熟悉"
    assert mastery_for_srs_status("reviewed") == "掌握"
    assert mastery_for_srs_status("relearn1") == "认识"
    assert mastery_for_srs_status("relearn2") == "熟悉"


def test_invalid_rating_raises():
    try:
        rate_srs("new", "胡说")
        assert False, "应抛出异常"
    except ValueError:
        pass


if __name__ == "__main__":
    import traceback
    failed = 0
    for name, fn in sorted(list(globals().items())):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception:
                failed += 1
                traceback.print_exc()
                print(f"FAIL {name}")
    if failed:
        raise SystemExit(f"{failed} 个测试失败")
    print("PASS: 全部 SM2+ 测试通过")
```

- [ ] **Step 2: 运行确认失败**

Run: `python3 backend/tests/test_srs.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.utils.srs'`

- [ ] **Step 3: 实现 `backend/app/utils/srs.py`**

```python
"""SM2+ 四档单词复习算法（借鉴 ToastFish SM2plus）。

纯逻辑模块，不依赖数据库。*/
"""
from datetime import date, timedelta
from typing import Optional

RATING_SCORES = {"忘记": 0.4, "困难": 0.6, "一般": 0.8, "认识": 1.0}

SRS_STATUSES = ["new", "step1", "step2", "reviewed", "relearn1", "relearn2"]

DEFAULT_DIFFICULTY = 0.3
DEFAULT_DAYS_BETWEEN_REVIEWS = 3.0
CORRECT_THRESHOLD = 0.7

OLD_RATING_MAP = {"认识": "认识", "模糊": "困难", "不认识": "忘记"}

MASTERY_BY_STATUS = {
    "new": "陌生",
    "step1": "认识",
    "step2": "熟悉",
    "reviewed": "掌握",
    "relearn1": "认识",
    "relearn2": "熟悉",
}

TRANSITIONS = {
    "new": {"忘记": (1.0, "step1"), "困难": (5.5, "step1"), "一般": (10.0, "step2"), "认识": (None, "reviewed")},
    "step1": {"忘记": (1.0, "step1"), "困难": (5.5, "step1"), "一般": (10.0, "step2"), "认识": (None, "reviewed")},
    "step2": {"忘记": (1.0, "step1"), "困难": (5.5, "step1"), "一般": (None, "reviewed"), "认识": (None, "reviewed")},
    "reviewed": {"忘记": (10.0, "relearn1"), "困难": (None, "reviewed"), "一般": (None, "reviewed"), "认识": (None, "reviewed")},
    "relearn1": {"忘记": (10.0, "relearn1"), "困难": (15.0, "relearn1"), "一般": (15.0, "relearn2"), "认识": (None, "reviewed")},
    "relearn2": {"忘记": (10.0, "relearn1"), "困难": (15.0, "relearn2"), "一般": (None, "reviewed"), "认识": (None, "reviewed")},
}


def mastery_for_srs_status(status: str) -> str:
    return MASTERY_BY_STATUS.get(status, "陌生")


def rate_srs(
    status: str,
    rating: str,
    difficulty: float = DEFAULT_DIFFICULTY,
    days_between_reviews: float = DEFAULT_DAYS_BETWEEN_REVIEWS,
    elapsed_days: int = 0,
    today: Optional[date] = None,
    rng=None,
) -> dict:
    """按四档评级推进卡片状态机。

    - new/step1/step2/relearn* 阶段：返回会话内 `due_minutes`，`next_review_date=None`
    - 进入 reviewed：计算跨会话间隔与难度，返回 `next_review_date`
    """
    if status not in TRANSITIONS or rating not in RATING_SCORES:
        raise ValueError(f"无效状态或评级: {status}/{rating}")

    score = RATING_SCORES[rating]
    due_minutes, new_status = TRANSITIONS[status][rating]
    result = {
        "new_status": new_status,
        "due_minutes": due_minutes,
        "next_review_date": None,
        "difficulty": difficulty,
        "days_between_reviews": days_between_reviews,
    }

    if new_status != "reviewed":
        return result

    today = today or date.today()
    roll = (rng or __import__("random").random)
    correct = score >= CORRECT_THRESHOLD
    if correct:
        podue = min(2.0, elapsed_days / max(days_between_reviews, 0.01))
    else:
        podue = 1.0

    difficulty = max(0.0, min(1.0, difficulty + podue * (8 - 10 * score) / 17))
    dfweight = 3 - 1.7 * difficulty
    if correct:
        jitter = 0.95 + 0.1 * roll()
        days_between_reviews *= 1 + (dfweight - 1) * podue * jitter
    else:
        days_between_reviews *= 1 / (1 + 3 * difficulty)

    result["difficulty"] = difficulty
    result["days_between_reviews"] = days_between_reviews
    result["next_review_date"] = today + timedelta(days=max(1, round(days_between_reviews)))
    return result
```

- [ ] **Step 4: 运行确认通过**

Run: `python3 backend/tests/test_srs.py`
Expected: `PASS: 全部 SM2+ 测试通过`

- [ ] **Step 5: 提交**

```bash
git add backend/app/utils/srs.py backend/tests/test_srs.py
git commit -m "feat: SM2+ 四档评分引擎与测试"
```

---

### Task 2: 数据模型 + Alembic 迁移 + openpyxl 依赖

**Files:**
- Modify: `backend/app/models/word.py`（UserWord 加 3 列，新增 StudyRecord）
- Modify: `backend/app/models/user.py`（加 push_settings_json）
- Modify: `backend/requirements.txt`（+ openpyxl）
- Modify: `backend/alembic/env.py`（如需，`import app.models` 已在；无需改动）
- Create: `backend/alembic/versions/a3b4c5d6e7f8_words_toastfish_features.py`

**Interfaces:**
- Consumes: Task 1 的 `DEFAULT_DIFFICULTY`、`DEFAULT_DAYS_BETWEEN_REVIEWS`（字段默认值）
- Produces:
  - `UserWord.srs_status: Column(String(20))` 默认 `new`；`UserWord.difficulty: Column(Float)` 默认 0.3；`UserWord.days_between_reviews: Column(Float)` 默认 3.0
  - `StudyRecord` 模型（表 `study_records`）：`id, user_id, session_id, word_id, word, phonetic, meaning, rating, quiz_result(Boolean nullable), source, created_at`
  - `User.push_settings_json: Column(Text)`

- [ ] **Step 1: 修改模型**

`backend/app/models/word.py` 全文：

```python
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base

class Word(Base):
    __tablename__ = "words"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String(50), index=True, nullable=False)
    phonetic = Column(String(100), nullable=True)
    meaning = Column(Text, nullable=False)
    example_sentence = Column(Text, nullable=True)
    difficulty = Column(Integer, nullable=False, default=1)
    frequency = Column(Integer, nullable=False, default=0)
    exam_requirement = Column(String(20), nullable=False, default="考纲", server_default="考纲")
    category = Column(String(20), nullable=False, default="CET-4", server_default="CET-4")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

class UserWord(Base):
    __tablename__ = "user_words"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    mastery_level = Column(String(20), nullable=False, default="陌生")
    next_review_date = Column(Date, nullable=True)
    review_count = Column(Integer, nullable=False, default=0)
    correct_count = Column(Integer, nullable=False, default=0)
    last_study_date = Column(DateTime(timezone=True), nullable=True)
    first_study_date = Column(Date, nullable=True)
    last_rating = Column(String(20), nullable=True)
    srs_stage = Column(Integer, nullable=False, default=0, server_default="0")
    srs_status = Column(String(20), nullable=False, default="new", server_default="new")
    difficulty = Column(Float, nullable=False, default=0.3, server_default="0.3")
    days_between_reviews = Column(Float, nullable=False, default=3.0, server_default="3.0")

    word = relationship("Word", lazy="joined")


class StudyRecord(Base):
    __tablename__ = "study_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String(64), nullable=False, index=True)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    word = Column(String(50), nullable=False)
    phonetic = Column(String(100), nullable=True)
    meaning = Column(Text, nullable=False)
    rating = Column(String(20), nullable=False)
    quiz_result = Column(Boolean, nullable=True)
    source = Column(String(20), nullable=False, default="card", server_default="card")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

`backend/app/models/user.py` — 在 `study_session_json` 行后加一行：

```python
    push_settings_json = Column(Text, nullable=True)
```

`backend/requirements.txt` — 在 `python-dotenv==1.2.1` 行后加：

```
openpyxl==3.1.5
```

- [ ] **Step 2: 安装 openpyxl**

Run: `pip install openpyxl==3.1.5`
Expected: `Successfully installed openpyxl-3.1.5`

- [ ] **Step 3: 写迁移文件**

创建 `backend/alembic/versions/a3b4c5d6e7f8_words_toastfish_features.py`：

```python
"""words toastfish features: srs 4-grade + study_records + push settings

Revision ID: a3b4c5d6e7f8
Revises: b2c4d6e8f1a3
Create Date: 2026-09-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3b4c5d6e7f8'
down_revision: Union[str, Sequence[str], None] = 'b2c4d6e8f1a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # user_words：SM2+ 四档状态列
    op.add_column('user_words', sa.Column('srs_status', sa.String(length=20), nullable=False, server_default='new'))
    op.add_column('user_words', sa.Column('difficulty', sa.Float(), nullable=False, server_default='0.3'))
    op.add_column('user_words', sa.Column('days_between_reviews', sa.Float(), nullable=False, server_default='3.0'))

    # 存量数据迁移：已学过的按旧间隔序列初始化
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, srs_stage FROM user_words WHERE srs_stage > 0")).fetchall()
    for rid, stage in rows:
        days = [1, 3, 7, 15][min(stage, 3)]
        conn.execute(
            sa.text("UPDATE user_words SET srs_status='reviewed', days_between_reviews=:d WHERE id=:i"),
            {"d": float(days), "i": rid},
        )

    # users：弹卡配置
    op.add_column('users', sa.Column('push_settings_json', sa.Text(), nullable=True))

    # study_records 审计表
    op.create_table('study_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=64), nullable=False),
        sa.Column('word_id', sa.Integer(), nullable=False),
        sa.Column('word', sa.String(length=50), nullable=False),
        sa.Column('phonetic', sa.String(length=100), nullable=True),
        sa.Column('meaning', sa.Text(), nullable=False),
        sa.Column('rating', sa.String(length=20), nullable=False),
        sa.Column('quiz_result', sa.Boolean(), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=False, server_default='card'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_study_records_id'), 'study_records', ['id'], unique=False)
    op.create_index(op.f('ix_study_records_session_id'), 'study_records', ['session_id'], unique=False)
    op.create_index(op.f('ix_study_records_user_id'), 'study_records', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_study_records_user_id'), table_name='study_records')
    op.drop_index(op.f('ix_study_records_session_id'), table_name='study_records')
    op.drop_index(op.f('ix_study_records_id'), table_name='study_records')
    op.drop_table('study_records')
    op.drop_column('users', 'push_settings_json')
    op.drop_column('user_words', 'days_between_reviews')
    op.drop_column('user_words', 'difficulty')
    op.drop_column('user_words', 'srs_status')
```

- [ ] **Step 4: 应用迁移并验证**

Run: `cd backend && alembic upgrade head && python3 -c "import sqlite3; db=sqlite3.connect('../kaoyan_xt.db'); print([r[1] for r in db.execute('PRAGMA table_info(user_words)')]); print(db.execute('SELECT COUNT(*) FROM study_records').fetchone())"`
Expected: 输出包含 `srs_status`、`difficulty`、`days_between_reviews` 且 `study_records` 已存在（COUNT=0）

- [ ] **Step 5: 提交**

```bash
git add backend/app/models/word.py backend/app/models/user.py backend/requirements.txt backend/alembic/versions/a3b4c5d6e7f8_words_toastfish_features.py kaoyan_xt.db
git commit -m "feat: SMS 四档列 + study_records 表 + openpyxl 依赖"
```

---

### Task 3: word_service 四档集成 + study 接口升级

**Files:**
- Modify: `backend/app/schemas/word.py`（WordStudyRequest 扩展）
- Modify: `backend/app/services/word_service.py`（study_word 重写 + helpers）
- Modify: `backend/app/api/words.py`（study 路由响应体）
- Test: `backend/tests/test_study_word_srs.py`

**Interfaces:**
- Consumes: Task 1 `rate_srs/OLD_RATING_MAP/mastery_for_srs_status/RATING_SCORES/CORRECT_THRESHOLD/DEFAULT_*`；Task 2 `StudyRecord`、`UserWord.srs_status/difficulty/days_between_reviews`
- Produces:
  - `WordService.study_word(db, user_id, data: WordStudyRequest) -> dict`，返回含 `srs_status`、`due_minutes`、`mastery_level` 等
  - `WordStudyRequest` 新字段：`session_id: Optional[str]=None`, `source: str="card"`, `quiz_result: Optional[bool]=None`

- [ ] **Step 1: 写失败的测试**

创建 `backend/tests/test_study_word_srs.py`：

```python
"""study_word 四档 SRS 集成测试。

运行方式：python3 backend/tests/test_study_word_srs.py
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.word import Word, StudyRecord
from app.models.user import User
from app.services.word_service import word_service
from app.schemas.word import WordStudyRequest


def _setup():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    user = User(username="tester", email="t@t.com", password="x")
    db.add(user)
    db.flush()
    w = Word(word="abandon", meaning="v. 放弃", phonetic="/xa/", category="考研", frequency=90)
    db.add(w)
    db.commit()
    return db, user.id, w.id


def _study(db, user_id, word_id, result, **kw):
    return word_service.study_word(db, user_id, WordStudyRequest(word_id=word_id, result=result, **kw))


def test_new_card_easy_mastered():
    db, uid, wid = _setup()
    out = _study(db, uid, wid, "认识", session_id="s1", source="push")
    assert out["srs_status"] == "reviewed"
    assert out["mastery_level"] == "掌握"
    assert out["next_review_date"] is not None
    assert db.query(StudyRecord).filter_by(session_id="s1").count() == 1


def test_legacy_vague_maps_to_hard():
    db, uid, wid = _setup()
    out = _study(db, uid, wid, "模糊", session_id="s1")
    assert out["last_rating"] == "困难"
    assert out["srs_status"] == "step1"
    assert out["next_review_date"] is None
    assert out["mastery_level"] == "认识"


def test_no_session_record_written_without_session_id():
    db, uid, wid = _setup()
    _study(db, uid, wid, "认识")
    assert db.query(StudyRecord).count() == 0


def test_quiz_result_recorded():
    db, uid, wid = _setup()
    _study(db, uid, wid, "忘记", session_id="q1", source="quiz", quiz_result=False)
    rec = db.query(StudyRecord).filter_by(session_id="q1").first()
    assert rec.source == "quiz"
    assert rec.quiz_result is False
    assert rec.rating == "忘记"


def test_review_count_and_correct_count():
    db, uid, wid = _setup()
    _study(db, uid, wid, "认识", session_id="s1")
    _study(db, uid, wid, "认识", session_id="s2")
    _study(db, uid, wid, "忘记", session_id="s3")
    from app.models.word import UserWord
    uw = db.query(UserWord).filter_by(word_id=wid).first()
    assert uw.review_count == 3
    assert uw.correct_count == 2
    assert uw.srs_status == "relearn1"


if __name__ == "__main__":
    import traceback
    failed = 0
    for name, fn in sorted(list(globals().items())):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception:
                failed += 1
                traceback.print_exc()
                print(f"FAIL {name}")
    if failed:
        raise SystemExit(f"{failed} 个测试失败")
    print("PASS: 全部 study_word 测试通过")
```

- [ ] **Step 2: 运行确认失败**

Run: `python3 backend/tests/test_study_word_srs.py`
Expected: FAIL（study 响应无 `srs_status` 或 `StudyRecord` 未写入）

- [ ] **Step 3: 更新 schema**

`backend/app/schemas/word.py` —— `WordStudyRequest` 替换为：

```python
class WordStudyRequest(BaseModel):
    word_id: int
    result: str = Field(..., description="评级：忘记/困难/一般/认识（兼容旧三档）")
    session_id: Optional[str] = Field(None, description="会话ID，用于背诵记录分组")
    source: str = Field("card", description="来源：card/push/quiz")
    quiz_result: Optional[bool] = Field(None, description="测验对错（source=quiz 时）")
```

- [ ] **Step 4: 重写 `study_word`**

在 `backend/app/services/word_service.py` 顶部 imports 区替换：

```python
import json
import random
import uuid as uuid_mod
from datetime import date, datetime, timedelta
from io import BytesIO
from sqlalchemy import or_, case, func
from sqlalchemy.orm import Session
from ..models.word import Word, UserWord, StudyRecord
from ..models.user import User
from ..schemas.word import WordStudyRequest, StudyPlanRequest
from ..utils.srs import (
    RATING_SCORES, OLD_RATING_MAP, CORRECT_THRESHOLD,
    DEFAULT_DIFFICULTY, DEFAULT_DAYS_BETWEEN_REVIEWS,
    rate_srs, mastery_for_srs_status,
)
from ..utils.ocr_parse import ocr_parser
from ..utils.wordbook_parser import parse_wordbook_text
from .llm_service import llm_service
from .ai_service import ai_service

DEFAULT_PUSH_CONFIG = {"count": 10, "interval_seconds": 60, "category": None, "auto_play": True}
```

将 `study_word` 方法整段替换为（保持原有方法签名，方法内逻辑全换）：

```python
    def study_word(self, db: Session, user_id: int, data: WordStudyRequest) -> dict:
        rating = OLD_RATING_MAP.get(data.result, data.result)
        if rating not in RATING_SCORES:
            raise ValueError(f"无效评级: {rating}")

        user_word = db.query(UserWord).filter(
            UserWord.user_id == user_id,
            UserWord.word_id == data.word_id
        ).first()

        if not user_word:
            user_word = UserWord(
                user_id=user_id,
                word_id=data.word_id,
                mastery_level="陌生",
                srs_status="new",
                difficulty=DEFAULT_DIFFICULTY,
                days_between_reviews=DEFAULT_DAYS_BETWEEN_REVIEWS,
                review_count=0,
                correct_count=0,
            )
            db.add(user_word)
            db.flush()

        elapsed_days = 0
        if user_word.srs_status == "reviewed" and user_word.next_review_date:
            elapsed_days = max((date.today() - user_word.next_review_date).days, 0)
        elif user_word.last_study_date:
            elapsed_days = max((date.today() - user_word.last_study_date.date()).days, 0)

        out = rate_srs(
            user_word.srs_status, rating,
            difficulty=user_word.difficulty,
            days_between_reviews=user_word.days_between_reviews,
            elapsed_days=elapsed_days,
        )

        user_word.srs_status = out["new_status"]
        user_word.difficulty = round(out["difficulty"], 4)
        user_word.days_between_reviews = round(out["days_between_reviews"], 4)
        user_word.next_review_date = out["next_review_date"]
        user_word.last_rating = rating
        user_word.mastery_level = mastery_for_srs_status(out["new_status"])
        user_word.review_count += 1
        if RATING_SCORES[rating] >= CORRECT_THRESHOLD:
            user_word.correct_count += 1
        if not user_word.first_study_date:
            user_word.first_study_date = date.today()
        user_word.last_study_date = datetime.now()

        if data.session_id:
            db.add(StudyRecord(
                user_id=user_id,
                session_id=data.session_id,
                word_id=user_word.word_id,
                word=getattr(user_word.word, "word", ""),
                phonetic=getattr(user_word.word, "phonetic", None),
                meaning=getattr(user_word.word, "meaning", ""),
                rating=rating,
                quiz_result=data.quiz_result,
                source=data.source,
            ))

        db.commit()
        db.refresh(user_word)
        return {
            "id": user_word.id,
            "word_id": user_word.word_id,
            "mastery_level": user_word.mastery_level,
            "next_review_date": user_word.next_review_date.isoformat() if user_word.next_review_date else None,
            "review_count": user_word.review_count,
            "correct_count": user_word.correct_count,
            "last_rating": user_word.last_rating,
            "srs_status": user_word.srs_status,
            "due_minutes": out.get("due_minutes"),
            "srs_stage": user_word.srs_stage,
        }
```

- [ ] **Step 5: 运行确认通过**

Run: `python3 backend/tests/test_study_word_srs.py`
Expected: `PASS: 全部 study_word 测试通过`

- [ ] **Step 6: 提交**

```bash
git add backend/app/schemas/word.py backend/app/services/word_service.py backend/app/models/word.py backend/tests/test_study_word_srs.py
git commit -m "feat: study 接口升级四档 SM2+ 并写入背诵记录"
```

---

### Task 4: 弹卡会话队列 + 会话结束 + 弹卡配置 API

**Files:**
- Modify: `backend/app/services/word_service.py`
- Modify: `backend/app/schemas/word.py`
- Modify: `backend/app/api/words.py`
- Test: `backend/tests/test_session_cards.py`

**Interfaces:**
- Consumes: Task 3 的 filters；Task 1 `DEFAULT_DIFFICULTY/DEFAULT_DAYS_BETWEEN_REVIEWS`；Task 2 `UserWord.srs_status`、`User.push_settings_json`
- Produces:
  - `GET /api/words/session-cards?count=&category=` → `{session_id: str, total: int, cards: [SessionCardItem]}`
  - `SessionCardItem`: `{word_id, word, phonetic, meaning, example_sentence, srs_status, type}`
  - `POST /api/words/session-complete` body `{session_id}` → `{success, session_id}`
  - `GET /api/words/push-config` → `PushConfig`；`POST /api/words/push-config` body `PushConfig` → `PushConfig`
  - `PushConfig`: `{count: int, interval_seconds: int, category: str|None, auto_play: bool}`

- [ ] **Step 1: 写失败的测试**

创建 `backend/tests/test_session_cards.py`：

```python
"""session-cards 队列与 push-config 测试。

运行方式：python3 backend/tests/test_session_cards.py
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.word import Word, UserWord
from app.models.user import User
from app.services.word_service import word_service


def _setup():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    user = User(username="t", email="t@t.com", password="x")
    db.add(user)
    db.flush()
    words = [Word(word=f"word{i}", meaning=f"释义{i}", category="考研", frequency=100 - i) for i in range(20)]
    db.add_all(words)
    db.commit()
    return db, user.id, words


def test_session_cards_orders_new_first():
    db, uid, words = _setup()
    db.add(UserWord(user_id=uid, word_id=words[5].id, srs_status="reviewed",
                    next_review_date=date.today(), mastery_level="掌握"))
    db.commit()
    res = word_service.get_session_cards(db, uid, count=10, category=None)
    assert res["total"] == 10
    ids = [c["word_id"] for c in res["cards"]]
    assert words[5].id in ids  # 到期复习卡必须入队
    assert ids[0] != words[5].id  # 新词优先：队列首位必须是未学习词
    assert res["cards"][0]["type"] == "new"
    assert len(res["session_id"]) == 32


def test_session_cards_respects_count():
    db, uid, words = _setup()
    res = word_service.get_session_cards(db, uid, count=5)
    assert res["total"] == 5


def test_push_config_defaults_and_save():
    db, uid, words = _setup()
    cfg = word_service.get_push_config(db, uid)
    assert cfg["count"] == 10 and cfg["interval_seconds"] == 60 and cfg["auto_play"] is True
    saved = word_service.save_push_config(db, uid, {"count": 5, "interval_seconds": 30})
    assert saved["count"] == 5 and saved["interval_seconds"] == 30
    cfg2 = word_service.get_push_config(db, uid)
    assert cfg2["count"] == 5 and cfg2["interval_seconds"] == 30


if __name__ == "__main__":
    import traceback
    failed = 0
    for name, fn in sorted(list(globals().items())):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception:
                failed += 1
                traceback.print_exc()
                print(f"FAIL {name}")
    if failed:
        raise SystemExit(f"{failed} 个测试失败")
    print("PASS: 全部 session-cards 测试通过")
```

- [ ] **Step 2: 运行确认失败**

Run: `python3 backend/tests/test_session_cards.py`
Expected: FAIL — AttributeError: `word_service.get_session_cards` 不存在

- [ ] **Step 3: 实现服务方法**

在 `backend/app/services/word_service.py` 的 `save_study_plan` 之后、`get_study_session` 之前插入：

```python
    def get_session_cards(self, db: Session, user_id: int, count: int = 10, category: str = None) -> dict:
        reviewed_q = db.query(UserWord).join(Word).filter(
            UserWord.user_id == user_id,
            UserWord.srs_status == "reviewed",
            UserWord.next_review_date <= date.today(),
        )
        reviewed_q = self._apply_category_filter(reviewed_q, user_id, category)
        reviewed = reviewed_q.order_by(UserWord.next_review_date.asc()).limit(count).all()

        learning_q = db.query(UserWord).join(Word).filter(
            UserWord.user_id == user_id,
            UserWord.srs_status.in_(["step1", "step2", "relearn1", "relearn2"]),
        )
        learning_q = self._apply_category_filter(learning_q, user_id, category)
        learning = learning_q.order_by(UserWord.last_study_date.asc()).limit(count).all()

        studied = {uw.word_id for uw in db.query(UserWord).filter(UserWord.user_id == user_id).all()}
        remain = count - len(reviewed) - len(learning)
        new_words = []
        if remain > 0:
            nq = db.query(Word)
            nq = self._apply_category_filter(nq, user_id, category)
            if studied:
                nq = nq.filter(~Word.id.in_(studied))
            new_words = nq.order_by(Word.frequency.desc()).limit(remain).all()

        cards = []
        for w in new_words:
            cards.append({
                "word_id": w.id, "word": w.word, "phonetic": w.phonetic,
                "meaning": w.meaning, "example_sentence": w.example_sentence,
                "srs_status": "new", "type": "new",
            })
        for uw in reviewed:
            w = uw.word
            cards.append({
                "word_id": w.id, "word": w.word, "phonetic": w.phonetic,
                "meaning": w.meaning, "example_sentence": w.example_sentence,
                "srs_status": uw.srs_status, "type": "review",
            })
        for uw in learning:
            w = uw.word
            cards.append({
                "word_id": w.id, "word": w.word, "phonetic": w.phonetic,
                "meaning": w.meaning, "example_sentence": w.example_sentence,
                "srs_status": uw.srs_status, "type": "learning",
            })

        return {"session_id": uuid_mod.uuid4().hex, "total": len(cards), "cards": cards}

    def complete_session(self, db: Session, user_id: int, session_id: str) -> dict:
        return {"success": True, "session_id": session_id}

    def get_push_config(self, db: Session, user_id: int) -> dict:
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.push_settings_json:
            try:
                loaded = json.loads(user.push_settings_json)
                return {**DEFAULT_PUSH_CONFIG, **loaded}
            except json.JSONDecodeError:
                pass
        return dict(DEFAULT_PUSH_CONFIG)

    def save_push_config(self, db: Session, user_id: int, cfg: dict) -> dict:
        user = db.query(User).filter(User.id == user_id).first()
        merged = {**DEFAULT_PUSH_CONFIG, **cfg}
        if user:
            user.push_settings_json = json.dumps(merged, ensure_ascii=False)
            db.commit()
        return merged
```

- [ ] **Step 4: 新增 schema**

`backend/app/schemas/word.py` 追加：

```python
class PushConfig(BaseModel):
    count: int = 10
    interval_seconds: int = 60
    category: Optional[str] = None
    auto_play: bool = True
```

- [ ] **Step 5: 新增路由**

`backend/app/api/words.py` —— 在 `save_study_plan` 路由之后插入：

```python
@router.get("/session-cards")
async def get_session_cards(
    count: int = Query(10, ge=1, le=100),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return word_service.get_session_cards(db, current_user.id, count, category)


@router.post("/session-complete")
async def complete_session(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return word_service.complete_session(db, current_user.id, data.get("session_id") or "")


@router.get("/push-config")
async def get_push_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return word_service.get_push_config(db, current_user.id)


@router.post("/push-config")
async def save_push_config(
    data: PushConfig,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return word_service.save_push_config(db, current_user.id, data.model_dump())
```

在文件顶部 `from ..schemas.word import ...` 行追加 `PushConfig`。

- [ ] **Step 6: 运行确认通过**

Run: `python3 backend/tests/test_session_cards.py`
Expected: `PASS: 全部 session-cards 测试通过`

- [ ] **Step 7: 提交**

```bash
git add backend/app/services/word_service.py backend/app/schemas/word.py backend/app/api/words.py backend/tests/test_session_cards.py
git commit -m "feat: 弹卡会话队列 + 弹卡配置 API"
```

---

### Task 5: 学后测验 API（出题 + 判分）

**Files:**
- Modify: `backend/app/services/word_service.py`
- Modify: `backend/app/schemas/word.py`
- Modify: `backend/app/api/words.py`
- Test: `backend/tests/test_quiz_api.py`

**Interfaces:**
- Consumes: Task 3 的 `study_word`；Task 1 的评分；`Word` 库
- Produces:
  - `GET /api/words/quiz?word_ids=1,2,3&count=8` → `[QuizItem]`
  - `QuizItem`: `{type: "中译英"|"英译中", word_id, prompt, options: [{index, text}], correct: int}`
  - `POST /api/words/quiz/answer` body `QuizAnswerRequest` → 同 `study_word` 返回；rating 由 `correct` 决定（对→一般，错→忘记）

- [ ] **Step 1: 写失败的测试**

创建 `backend/tests/test_quiz_api.py`：

```python
"""学后测验出题/判分测试。

运行方式：python3 backend/tests/test_quiz_api.py
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.word import Word, StudyRecord
from app.models.user import User
from app.services.word_service import word_service
from app.schemas.word import QuizAnswerRequest, WordStudyRequest


def _setup():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    user = User(username="t", email="t@t.com", password="x")
    db.add(user)
    db.flush()
    words = [Word(word=f"word{i}", meaning=f"释义{i}", category="考研", frequency=100 - i) for i in range(20)]
    db.add_all(words)
    db.commit()
    return db, user.id, words


def test_generate_quiz_structure_and_options():
    db, uid, words = _setup()
    items = word_service.generate_quiz(db, uid, [w.id for w in words[:8]], count=8)
    assert len(items) == 8
    for idx, it in enumerate(items):
        assert it["type"] in ("中译英", "英译中")
        assert len(it["options"]) == 4
        assert 0 <= it["correct"] < 4
        assert it["options"][it["correct"]]["text"] != it["prompt"], "正确答案文本不得等于题干"
        assert len({o["text"] for o in it["options"]}) == 4, "选项不得重复"


def test_quiz_answer_correct_writes_record():
    db, uid, words = _setup()
    out = word_service.answer_quiz(db, uid, QuizAnswerRequest(
        word_id=words[0].id, selected=0, correct=True, session_id="qz"
    ))
    assert out["last_rating"] == "一般"
    assert out["srs_status"] == "step2"
    rec = db.query(StudyRecord).filter_by(session_id="qz").first()
    assert rec.source == "quiz"
    assert rec.quiz_result is True


def test_quiz_answer_wrong_resets_to_relearn():
    db, uid, words = _setup()
    word_service.study_word(db, uid, WordStudyRequest(
        word_id=words[0].id, result="认识", session_id="x1"))
    out = word_service.answer_quiz(db, uid, QuizAnswerRequest(
        word_id=words[0].id, selected=1, correct=False, session_id="qz2"
    ))
    assert out["last_rating"] == "忘记"
    assert out["srs_status"] == "relearn1"


if __name__ == "__main__":
    import traceback
    failed = 0
    for name, fn in sorted(list(globals().items())):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception:
                failed += 1
                traceback.print_exc()
                print(f"FAIL {name}")
    if failed:
        raise SystemExit(f"{failed} 个测试失败")
    print("PASS: 全部 quiz 测试通过")
```

- [ ] **Step 2: 运行确认失败**

Run: `python3 backend/tests/test_quiz_api.py`
Expected: FAIL — `generate_quiz` 不存在

- [ ] **Step 3: 实现服务方法**

`backend/app/services/word_service.py` 中 `complete_session` 之后插入：

```python
    def generate_quiz(self, db: Session, user_id: int, word_ids: list, count: int = 8) -> list:
        words = db.query(Word).filter(Word.id.in_(word_ids)).all()[:count]
        if not words:
            return []
        ids = [w.id for w in words]
        source = self._get_source_filter(user_id, None)
        pool = db.query(Word).filter(~Word.id.in_(ids)).filter(source).all()
        pool = [p for p in pool if p.word.strip()]
        items = []
        for i, w in enumerate(words):
            qtype = "中译英" if i % 2 == 0 else "英译中"
            if qtype == "中译英":
                prompt = w.meaning
                correct_text = w.word
                distractors = [p.word for p in pool if p.word and p.word != w.word and p.meaning]
            else:
                prompt = w.word
                correct_text = w.meaning
                distractors = [p.meaning for p in pool if p.meaning and p.word != w.word and p.meaning]
            unique_distractors = list(dict.fromkeys(distractors))[:3]
            while len(unique_distractors) < 3:
                unique_distractors.append("——")
            choices = [correct_text] + unique_distractors
            random.shuffle(choices)
            options = [{"index": k, "text": t} for k, t in enumerate(choices)]
            items.append({
                "type": qtype,
                "word_id": w.id,
                "prompt": prompt,
                "options": options,
                "correct": choices.index(correct_text),
            })
        return items

    def answer_quiz(self, db: Session, user_id: int, data) -> dict:
        req = WordStudyRequest(
            word_id=data.word_id,
            result="一般" if data.correct else "忘记",
            session_id=data.session_id,
            source="quiz",
            quiz_result=data.correct,
        )
        return self.study_word(db, user_id, req)
```

- [ ] **Step 4: 新增 schema**

`backend/app/schemas/word.py` 追加：

```python
class QuizAnswerRequest(BaseModel):
    word_id: int
    selected: int = 0
    correct: bool = True
    session_id: Optional[str] = None
```

- [ ] **Step 5: 新增路由**

`backend/app/api/words.py` —— `push-config` 路由之后插入：

```python
@router.get("/quiz")
async def generate_quiz(
    word_ids: str = Query("", description="逗号分隔的单词ID"),
    count: int = Query(8, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ids = [int(x) for x in word_ids.split(",") if x.strip().isdigit()]
    return word_service.generate_quiz(db, current_user.id, ids, count)


@router.post("/quiz/answer")
async def answer_quiz(
    data: QuizAnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return word_service.answer_quiz(db, current_user.id, data)
```

顶部 import 追加 `QuizAnswerRequest`。

- [ ] **Step 6: 运行确认通过**

Run: `python3 backend/tests/test_quiz_api.py`
Expected: `PASS: 全部 quiz 测试通过`

- [ ] **Step 7: 提交**

```bash
git add backend/app/services/word_service.py backend/app/schemas/word.py backend/app/api/words.py backend/tests/test_quiz_api.py
git commit -m "feat: 学后测验出题与判分 API"
```

---

### Task 6: 背诵记录列表/导出/重新导入 API

**Files:**
- Modify: `backend/app/services/word_service.py`
- Modify: `backend/app/api/words.py`
- Test: `backend/tests/test_records_api.py`

**Interfaces:**
- Consumes: Task 2 `StudyRecord`；Task 3 `study_word`（写记录）；Task 1 默认值
- Produces:
  - `GET /api/words/records?page=&page_size=` → `{total, items: [{session_id, source, created_at, total, forgot, hard, good, known}]}`
  - `GET /api/words/records/export` → xlsx 流（`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`）
  - `POST /api/words/records/import`（multipart file）→ `{success, message, imported, failed: []}`

- [ ] **Step 1: 写失败的测试**

创建 `backend/tests/test_records_api.py`：

```python
"""背诵记录列表/导出/导入测试。

运行方式：python3 backend/tests/test_records_api.py
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.word import Word, UserWord, StudyRecord
from app.models.user import User
from app.services.word_service import word_service
from app.schemas.word import WordStudyRequest


def _setup():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    user = User(username="t", email="t@t.com", password="x")
    db.add(user)
    db.flush()
    words = [Word(word=f"word{i}", meaning=f"释义{i}", category="考研", frequency=100 - i) for i in range(6)]
    db.add_all(words)
    db.commit()
    return db, user.id, words


def _session(db, uid, sid, word, rating):
    word_service.study_word(db, uid, WordStudyRequest(word_id=word.id, result=rating, session_id=sid, source="push"))


def test_records_summary_groups_by_session():
    db, uid, words = _setup()
    _session(db, uid, "sess1", words[0], "认识")
    _session(db, uid, "sess1", words[1], "忘记")
    _session(db, uid, "sess2", words[2], "困难")
    res = word_service.get_records_summary(db, uid, 1, 10)
    assert res["total"] == 2
    by_id = {r["session_id"]: r for r in res["items"]}
    assert by_id["sess1"]["total"] == 2
    assert by_id["sess1"]["known"] == 1
    assert by_id["sess1"]["forgot"] == 1
    assert by_id["sess2"]["hard"] == 1


def test_export_produces_xlsx():
    db, uid, words = _setup()
    _session(db, uid, "sess1", words[0], "认识")
    blob = word_service.export_records(db, uid)
    assert isinstance(blob, bytes)
    assert blob[:2] in (b"PK", b"\x00\x00"), "应为 ZIP/xlsx 头"


def test_import_recreates_review_words():
    db, uid, words = _setup()
    db.query(StudyRecord).delete()
    db.query(UserWord).delete()
    for w in words:
        db.query(Word).filter(Word.id == w.id).delete()
    db.commit()

    from openpyxl import Workbook
    from io import BytesIO
    wb = Workbook()
    ws = wb.active
    ws.title = "背诵记录"
    ws.append(["日期", "会话ID", "单词", "音标", "释义", "评级"])
    ws.append(["2026-09-24", "s1", "abandon", "/a/", "v. 放弃", "认识"])
    ws.append(["2026-09-24", "s1", "ability", "/b/", "n. 能力", "一般"])
    buf = BytesIO()
    wb.save(buf)

    res = word_service.import_records(db, uid, buf.getvalue(), "r.xlsx")
    assert res["success"] is True
    assert res["imported"] == 2
    from app.models.word import Word as W
    assert db.query(W).filter(W.word == "abandon").count() == 1
    uw = db.query(UserWord).filter(UserWord.user_id == uid).all()
    assert len(uw) == 2
    assert all(x.srs_status == "reviewed" for x in uw)
    assert all(x.next_review_date == date.today() for x in uw)


if __name__ == "__main__":
    import traceback
    failed = 0
    for name, fn in sorted(list(globals().items())):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception:
                failed += 1
                traceback.print_exc()
                print(f"FAIL {name}")
    if failed:
        raise SystemExit(f"{failed} 个测试失败")
    print("PASS: 全部 records 测试通过")
```

- [ ] **Step 2: 运行确认失败**

Run: `python3 backend/tests/test_records_api.py`
Expected: FAIL — `get_records_summary` 不存在

- [ ] **Step 3: 实现导出方法**

`backend/app/services/word_service.py` 中 `answer_quiz` 之后插入：

```python
    def get_records_summary(self, db: Session, user_id: int, page: int = 1, page_size: int = 10) -> dict:
        base = db.query(
            StudyRecord.session_id,
            StudyRecord.source,
            func.min(StudyRecord.created_at).label("created_at"),
            func.count(StudyRecord.id).label("total"),
            func.sum(case((StudyRecord.rating == "忘记", 1), else_=0)).label("forgot"),
            func.sum(case((StudyRecord.rating == "困难", 1), else_=0)).label("hard"),
            func.sum(case((StudyRecord.rating == "一般", 1), else_=0)).label("good"),
            func.sum(case((StudyRecord.rating == "认识", 1), else_=0)).label("known"),
        ).filter(StudyRecord.user_id == user_id).group_by(StudyRecord.session_id)
        total = base.count()
        rows = base.order_by(func.min(StudyRecord.created_at).desc()).offset((page - 1) * page_size).limit(page_size).all()
        items = [{
            "session_id": r.session_id,
            "source": r.source,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "total": r.total,
            "forgot": r.forgot or 0,
            "hard": r.hard or 0,
            "good": r.good or 0,
            "known": r.known or 0,
        } for r in rows]
        return {"total": total, "items": items}

    def export_records(self, db: Session, user_id: int) -> bytes:
        from openpyxl import Workbook
        records = db.query(StudyRecord).filter(
            StudyRecord.user_id == user_id
        ).order_by(StudyRecord.created_at.asc()).all()

        wb = Workbook()
        ws = wb.active
        ws.title = "背诵记录"
        ws.append(["日期", "会话ID", "单词", "音标", "释义", "评级", "测验结果", "来源"])
        for r in records:
            quiz = ""
            if r.quiz_result is True:
                quiz = "对"
            elif r.quiz_result is False:
                quiz = "错"
            ws.append([
                r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
                r.session_id, r.word, r.phonetic or "", r.meaning, r.rating, quiz, r.source,
            ])

        ws2 = wb.create_sheet("会话汇总")
        ws2.append(["会话ID", "来源", "时间", "单词数", "忘记", "困难", "一般", "认识"])
        groups = {}
        for r in records:
            g = groups.setdefault(r.session_id, {"source": r.source, "count": 0, "forgot": 0, "hard": 0, "good": 0, "known": 0, "time": r.created_at})
            g["count"] += 1
            if r.rating == "忘记":
                g["forgot"] += 1
            elif r.rating == "困难":
                g["hard"] += 1
            elif r.rating == "一般":
                g["good"] += 1
            elif r.rating == "认识":
                g["known"] += 1
        for sid, g in groups.items():
            ws2.append([
                sid, g["source"],
                g["time"].strftime("%Y-%m-%d %H:%M:%S") if g["time"] else "",
                g["count"], g["forgot"], g["hard"], g["good"], g["known"],
            ])

        buf = BytesIO()
        wb.save(buf)
        return buf.getvalue()

    def import_records(self, db: Session, user_id: int, content: bytes, filename: str) -> dict:
        from openpyxl import load_workbook
        try:
            wb = load_workbook(BytesIO(content), read_only=True)
        except Exception as e:
            return {"success": False, "message": f"无法解析 xlsx: {e}", "imported": 0, "failed": []}
        ws = wb["背诵记录"] if "背诵记录" in wb.sheetnames else wb.active
        imported = 0
        failed = []
        today = date.today()
        for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if not row or len(row) < 6:
                continue
            word_text = (row[2] or "").strip()
            if not word_text:
                continue
            phonetic = (row[3] or "").strip()
            meaning = (row[4] or "").strip()
            word = db.query(Word).filter(
                or_(Word.user_id.is_(None), Word.user_id == user_id),
                Word.word == word_text,
            ).first()
            if not word:
                word = Word(
                    word=word_text, phonetic=phonetic or None, meaning=meaning or "",
                    difficulty=1, frequency=0, exam_requirement="记录导入",
                    category="我的词书", user_id=user_id,
                )
                db.add(word)
                db.flush()
            uw = db.query(UserWord).filter(
                UserWord.user_id == user_id, UserWord.word_id == word.id
            ).first()
            if not uw:
                uw = UserWord(
                    user_id=user_id, word_id=word.id, srs_status="reviewed",
                    mastery_level="掌握", difficulty=DEFAULT_DIFFICULTY,
                    days_between_reviews=DEFAULT_DAYS_BETWEEN_REVIEWS,
                    next_review_date=today, review_count=0, correct_count=0,
                    first_study_date=today,
                )
                db.add(uw)
            else:
                uw.srs_status = "reviewed"
                uw.mastery_level = "掌握"
                uw.next_review_date = today
            imported += 1
        db.commit()
        return {
            "success": True,
            "message": f"成功导入 {imported} 个单词为今日复习",
            "imported": imported,
            "failed": failed,
        }
```

- [ ] **Step 4: 新增路由**

`backend/app/api/words.py` —— `quiz/answer` 路由之后插入：

```python
@router.get("/records")
async def get_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return word_service.get_records_summary(db, current_user.id, page, page_size)


@router.get("/records/export")
async def export_records(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from fastapi.responses import StreamingResponse
    import urllib.parse
    blob = word_service.export_records(db, current_user.id)
    filename = urllib.parse.quote(f"背诵记录_{current_user.username}.xlsx")
    return StreamingResponse(
        iter([blob]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@router.post("/records/import")
async def import_records(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="仅支持 xlsx 文件")
    contents = await file.read()
    result = word_service.import_records(db, current_user.id, contents, file.filename)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "导入失败"))
    return result
```

- [ ] **Step 5: 运行确认通过**

Run: `python3 backend/tests/test_records_api.py`
Expected: `PASS: 全部 records 测试通过`

- [ ] **Step 6: 全量回归**

Run: `python3 backend/tests/test_srs.py && python3 backend/tests/test_study_word_srs.py && python3 backend/tests/test_session_cards.py && python3 backend/tests/test_quiz_api.py && python3 backend/tests/test_records_api.py`
Expected: 全部 PASS

- [ ] **Step 7: 提交**

```bash
git add backend/app/services/word_service.py backend/app/api/words.py backend/tests/test_records_api.py
git commit -m "feat: 背诵记录列表/导出 xlsx/重新导入 API"
```

---

### Task 7: 前端 API 层扩展

**Files:**
- Modify: `frontend/src/api/words.ts`

**Interfaces:**
- Consumes: Task 1-6 的 API 响应结构
- Produces:
  - `type SrsRating`, `interface SessionCardItem`, `interface PushConfig`, `interface QuizItem`, `interface QuizAnswer`, `interface RecordSummary`
  - `studyWord(wordId, result, opts?: {session_id?, source?, quiz_result?})`
  - `getSessionCards(count, category?)`, `completeSession(sessionId)`
  - `getQuiz(wordIds, count?)`, `answerQuiz(payload)`
  - `getStudyRecords(page, pageSize)`, `exportStudyRecords()`（Blob 下载）, `importStudyRecords(file)`
  - `getPushConfig()`, `savePushConfig(cfg)`
  - 兼容性：`studyWord` 旧调用不变；`UserWord` 接口补 `srs_status?`

- [ ] **Step 1: 扩展 `frontend/src/api/words.ts`**

在 `UploadWordbookResult` 之后整段追加：

```typescript
export type SrsRating = '忘记' | '困难' | '一般' | '认识'

export interface SessionCardItem {
  word_id: number
  word: string
  phonetic: string | null
  meaning: string
  example_sentence: string | null
  srs_status: string
  type: string
}

export interface PushConfig {
  count: number
  interval_seconds: number
  category: string | null
  auto_play: boolean
}

export interface QuizOption {
  index: number
  text: string
}

export interface QuizItem {
  type: '中译英' | '英译中'
  word_id: number
  prompt: string
  options: QuizOption[]
  correct: number
}

export interface QuizAnswerResult {
  last_rating: string
  srs_status: string
  mastery_level: string
  next_review_date: string | null
}

export interface RecordSummaryItem {
  session_id: string
  source: string
  created_at: string | null
  total: number
  forgot: number
  hard: number
  good: number
  known: number
}

export async function studyWord(
  wordId: number,
  result: string,
  opts?: { session_id?: string; source?: string; quiz_result?: boolean }
): Promise<any> {
  return await axios.post('/words/study', {
    word_id: wordId,
    result,
    session_id: opts?.session_id,
    source: opts?.source ?? 'card',
    quiz_result: opts?.quiz_result
  })
}

export async function getSessionCards(count: number = 10, category?: string): Promise<{ session_id: string; total: number; cards: SessionCardItem[] }> {
  return await axios.get('/words/session-cards', { params: { count, category } })
}

export async function completeSession(sessionId: string): Promise<{ success: boolean }> {
  return await axios.post('/words/session-complete', { session_id: sessionId })
}

export async function getQuiz(wordIds: number[], count: number = 8): Promise<QuizItem[]> {
  return await axios.get('/words/quiz', { params: { word_ids: wordIds.join(','), count } })
}

export async function answerQuiz(payload: {
  word_id: number
  selected: number
  correct: boolean
  session_id?: string
}): Promise<QuizAnswerResult> {
  return await axios.post('/words/quiz/answer', payload)
}

export async function getStudyRecords(page: number = 1, pageSize: number = 10): Promise<{ total: number; items: RecordSummaryItem[] }> {
  return await axios.get('/words/records', { params: { page, page_size: pageSize } })
}

export async function exportStudyRecords(): Promise<void> {
  const blob: Blob = await axios.get('/words/records/export', { responseType: 'blob' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = '背诵记录.xlsx'
  a.click()
  URL.revokeObjectURL(url)
}

export async function importStudyRecords(file: File): Promise<{ success: boolean; message: string; imported: number }> {
  const formData = new FormData()
  formData.append('file', file)
  return await axios.post('/words/records/import', formData)
}

export async function getPushConfig(): Promise<PushConfig> {
  return await axios.get('/words/push-config')
}

export async function savePushConfig(cfg: Partial<PushConfig>): Promise<PushConfig> {
  return await axios.post('/words/push-config', cfg)
}
```

同时给 `UserWord` 接口补字段，替换现有 `srs_stage: number` 之前追加一行 `srs_status?: string`。

- [ ] **Step 2: 构建校验**

Run: `cd frontend && npm run build`
Expected: 编译通过（无类型错误）

- [ ] **Step 3: 提交**

```bash
git add frontend/src/api/words.ts
git commit -m "feat: 前端 words API 层扩展（四档/弹卡/测验/记录）"
```

---

### Task 8: WordModule 四档改造 + 共享 QuizDialog

**Files:**
- Modify: `frontend/src/views/recitation/WordModule.vue`
- Modify: `frontend/src/api/words.ts`（StudySession.round_stats 类型）
- Create: `frontend/src/views/recitation/QuizDialog.vue`

**Interfaces:**
- Consumes: Task 7 `studyWord/getQuiz/answerQuiz`；`RoundQueueItem`；`StudySession`
- Produces:
  - `QuizDialog.vue` props: `visible: boolean`, `wordIds: number[]`；emits: `close`。可被 WordModule 与 PushCards 复用
  - `StudySession.round_stats` 改为 `{forget, hard, good, known}`
  - WordModule 四档按钮：忘记/困难/一般/认识；测验在每轮完成弹窗触发

- [ ] **Step 1: 建 `QuizDialog.vue`**

创建 `frontend/src/views/recitation/QuizDialog.vue`：

```vue
<template>
  <el-dialog
    :model-value="visible"
    title="学后测验"
    width="480px"
    :close-on-click-modal="false"
    :show-close="false"
    @close="$emit('close')"
  >
    <template v-if="stat.total > 0">
      <div class="quiz-progress">答对 {{ stat.correct }} / 已答 {{ stat.done }}</div>
      <div v-if="current" class="quiz-body" :key="current.word_id + '-' + current.type">
        <div class="quiz-badge">{{ current.type }}</div>
        <h3 class="quiz-prompt">{{ current.prompt }}</h3>
        <div class="quiz-options">
          <button
            v-for="opt in current.options"
            :key="opt.index"
            class="quiz-option"
            :class="optionClass(opt.index)"
            :disabled="answered"
            @click="handleSelect(opt.index)"
          >
            {{ translateIndex(opt.index) }}. {{ opt.text }}
          </button>
        </div>
        <p v-if="feedback !== null" class="quiz-feedback" :class="feedback ? 'ok' : 'bad'">
          {{ feedback ? '回答正确！' : '回答错误，正确答案：' + optionText(current.correct) }}
        </p>
      </div>
    </template>

    <template v-else>
      <el-empty description="测验完成！">
        <el-button type="primary" @click="$emit('close')">完成</el-button>
      </el-empty>
    </template>

    <template #footer>
      <el-button :disabled="feedback === null" type="primary" @click="next">
        {{ feedback === null ? '请作答' : (queue.length ? '下一题' : '查看结果') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { getQuiz, answerQuiz, type QuizItem } from '@/api/words'

const props = defineProps<{ visible: boolean; wordIds: number[] }>()
const emit = defineEmits<{ (e: 'close'): void }>()

const sessionId = ref('')
const queue = ref<QuizItem[]>([])
const current = ref<QuizItem | null>(null)
const answered = ref(false)
const feedback = ref<boolean | null>(null)
const lastPick = ref(-1)
const pendings = ref<number[]>([])
const stat = reactive({ done: 0, correct: 0, total: 0 })

function translateIndex(idx: number) {
  return ['A', 'B', 'C', 'D'][idx] ?? idx
}

function optionText(idx: number) {
  const opt = current.value?.options.find(o => o.index === idx)
  return opt ? translateIndex(idx) + '. ' + opt.text : ''
}

function optionClass(idx: number) {
  if (feedback.value === null) return ''
  if (idx === current.value?.correct) return 'right'
  if (idx === lastPick.value && feedback.value === false) return 'wrong'
  return ''
}

async function loadItems(ids: number[]) {
  return await getQuiz(ids, Math.min(ids.length, 8))
}

async function start() {
  sessionId.value = 'quiz_' + Date.now() + Math.random().toString(36).slice(2, 8)
  stat.done = 0
  stat.correct = 0
  stat.total = 0
  pendings.value = []
  answered.value = false
  feedback.value = null
  queue.value = []
  if (!props.wordIds.length) return
  const items = await loadItems(props.wordIds)
  stat.total = items.length
  queue.value = [...items]
  current.value = queue.value.shift() ?? null
}

async function handleSelect(idx: number) {
  if (answered.value || !current.value) return
  answered.value = true
  lastPick.value = idx
  const correct = idx === current.value.correct
  feedback.value = correct
  stat.done++
  if (correct) stat.correct++
  try {
    await answerQuiz({ word_id: current.value.word_id, selected: idx, correct, session_id: sessionId.value })
  } catch {
    // 网络失败不阻断交互
  }
  if (!correct) {
    pendings.value.push(current.value.word_id)
  }
}

async function next() {
  feedback.value = null
  answered.value = false
  lastPick.value = -1
  if (queue.value.length > 0) {
    current.value = queue.value.shift() ?? null
    return
  }
  if (pendings.value.length > 0) {
    const ids = [...pendings.value]
    pendings.value = []
    const items = await loadItems(ids)
    stat.total += items.length
    queue.value = [...items]
    current.value = queue.value.shift() ?? null
    return
  }
  current.value = null
}

watch(() => props.visible, async (v) => {
  if (v) {
    await start()
  } else {
    queue.value = []
    current.value = null
    pendings.value = []
  }
})
</script>

<style scoped>
.quiz-progress { font-size: 13px; color: #999; margin-bottom: 12px; }
.quiz-body { text-align: center; }
.quiz-badge { display: inline-block; padding: 4px 12px; background: #dbeafe; color: #3b82f6; border-radius: 4px; font-size: 12px; margin-bottom: 12px; }
.quiz-prompt { font-size: 22px; color: #333; margin: 0 0 16px; }
.quiz-options { display: flex; flex-direction: column; gap: 10px; }
.quiz-option { padding: 12px; border: 1px solid #e0e0e0; border-radius: 8px; background: #fff; cursor: pointer; font-size: 15px; text-align: left; }
.quiz-option:hover:not(:disabled) { border-color: #409eff; }
.quiz-option.right { border-color: #67c23a; background: #f0f9eb; }
.quiz-option.wrong { border-color: #f56c6c; background: #fef0f0; }
.quiz-option:disabled { cursor: default; }
.quiz-feedback { font-size: 14px; margin-top: 12px; }
.quiz-feedback.ok { color: #67c23a; }
.quiz-feedback.bad { color: #f56c6c; }
</style>
```

- [ ] **Step 2: 更新 StudySession 类型**

`frontend/src/api/words.ts`：

```typescript
export interface StudySession {
  current_round: number
  total_rounds: number
  round_queue: RoundQueueItem[]
  round_stats: { forget: number; hard: number; good: number; known: number }
  global_index: number
  total_words_today: number
  study_mode: string
  batch_size: number
  all_word_ids: number[]
  completed_rounds: number
  category: string | null
}
```

- [ ] **Step 3: WordModule.vue 改四档**

`WordModule.vue` 修改点（用下方代码替换对应段落）：

3a. 模板 study-buttons 整段替换：

```html
            <div class="study-buttons">
              <el-button type="danger" size="large" @click="markResult('忘记')">忘记</el-button>
              <el-button type="warning" size="large" @click="markResult('困难')">困难</el-button>
              <el-button type="info" size="large" @click="markResult('一般')">一般</el-button>
              <el-button type="success" size="large" @click="markResult('认识')">认识</el-button>
            </div>
```

3b. 轮次完成弹窗内侧统计替换为四格：

```html
        <div class="round-stats-grid">
          <div class="round-stat-item success">
            <span class="stat-num">{{ roundStats.known }}</span>
            <span class="stat-label">认识</span>
          </div>
          <div class="round-stat-item warning">
            <span class="stat-num">{{ roundStats.good }}</span>
            <span class="stat-label">一般</span>
          </div>
          <div class="round-stat-item danger">
            <span class="stat-num">{{ roundStats.hard }}</span>
            <span class="stat-label">困难</span>
          </div>
          <div class="round-stat-item danger">
            <span class="stat-num">{{ roundStats.forget }}</span>
            <span class="stat-label">忘记</span>
          </div>
        </div>
```

3c. 弹窗 footer 加「开始测验」按钮。替换 footer 整段：

```html
      <template #footer>
        <el-button @click="exitStudy">退出背诵</el-button>
        <el-button @click="startRoundQuiz">先测这一轮</el-button>
        <el-button type="primary" @click="startNextRound">开启下一轮</el-button>
      </template>
```

3d. roundStats 初始化与重置（`reactive` 定义处与 `startRound` 中）替换：

```ts
const roundStats = reactive({ forget: 0, hard: 0, good: 0, known: 0 })
```

`startRound` 内 `roundStats.known = 0; roundStats.vague = 0; roundStats.unknown = 0` 替换为：

```ts
  roundStats.forget = 0
  roundStats.hard = 0
  roundStats.good = 0
  roundStats.known = 0
```

3e. `markResult` 方法整体替换：

```ts
async function markResult(result: string) {
  if (!currentWord.value) return

  const word = currentWord.value

  try {
    const updated = await studyWord(word.wordId, result, {
      session_id: activeSessionId.value || undefined,
      source: 'card'
    })
    const statKey = result === '认识' ? 'known' : result === '一般' ? 'good' : result === '困难' ? 'hard' : 'forget'
    roundStats[statKey]++
    const item = roundQueue.value.shift()
    if (updated?.srs_status !== 'reviewed') {
      if (item) {
        item.repeatCount++
        roundQueue.value.push(item)
      }
    } else {
      globalIndex.value++
    }
  } catch {
    const item = roundQueue.value.shift()
    if (item) {
      item.repeatCount++
      roundQueue.value.push(item)
    }
  }

  scheduleStatsRefresh()
  showMeaning.value = false
  await saveCurrentSession()

  if (roundQueue.value.length === 0) {
    completedRounds.value++
    roundCompleteVisible.value = true
  }
}
```

3f. `markResult` 用了 `activeSessionId` —— `loadTodayWords` 里初始化。在 `loadTodayWords` 成功分支开头插入：

```ts
    if (!activeSessionId.value) {
      activeSessionId.value = 'card_' + Date.now() + Math.random().toString(36).slice(2, 8)
    }
```

3g. 加状态与测验相关定义。在 `saveCurrentSession` 函数前插入：

```ts
const activeSessionId = ref('')

const quizVisible = ref(false)
const quizWordIds = ref<number[]>([])

function startRoundQuiz() {
  const start = (currentRound.value - 1) * batchSize.value
  const end = Math.min(start + batchSize.value, totalWordsToday.value)
  quizWordIds.value = todayWords.value.slice(start, end).map(w => w.id).filter(Boolean)
  roundCompleteVisible.value = false
  if (quizWordIds.value.length) {
    quizVisible.value = true
  } else {
    ElMessage.warning('本轮没有单词可测验')
  }
}
```

3h. 模板根节点末尾（`</div>` 结束前）追加 QuizDialog：

```html
    <QuizDialog :visible="quizVisible" :word-ids="quizWordIds" @close="quizVisible = false" />
```

脚本 import 追加：

```ts
import QuizDialog from '@/views/recitation/QuizDialog.vue'
```

3i. `saveCurrentSession` 的 `round_stats` 字段从 `{ known, vague, unknown }` 改为四键：

```ts
    round_stats: { forget: roundStats.forget, hard: roundStats.hard, good: roundStats.good, known: roundStats.known },
```

3j. `resumeSession` 中恢复 `roundStats` 的行改为防御式读取（旧存档只有 known/vague/unknown）：

```ts
  roundStats.forget = session.round_stats?.forget ?? 0
  roundStats.hard = session.round_stats?.hard ?? 0
  roundStats.good = session.round_stats?.good ?? 0
  roundStats.known = session.round_stats?.known ?? 0
```

`resumeSession` 中原 `roundStats.known = session.round_stats.known` 等三行删除。

3k. 样式 `.round-stats-grid` 改为 4 列：`grid-template-columns: repeat(4, 1fr)`。

- [ ] **Step 4: 构建校验**

Run: `cd frontend && npm run build`
Expected: 编译通过，无类型错误

- [ ] **Step 5: 提交**

```bash
git add frontend/src/views/recitation/WordModule.vue frontend/src/views/recitation/QuizDialog.vue frontend/src/api/words.ts
git commit -m "feat: WordModule 四档评分 + 轮次后测验"
```

---

### Task 9: PushCards 沉浸式弹卡组件

**Files:**
- Create: `frontend/src/views/recitation/PushCards.vue`
- Modify: `frontend/src/views/Words.vue`（加 tab）

**Interfaces:**
- Consumes: Task 7 `getSessionCards/studyWord/completeSession/getQuiz/answerQuiz/getPushConfig/savePushConfig`；`useSpeech`；共享 `QuizDialog`
- Produces: `PushCards.vue` 组件（配置面板 + 悬浮弹卡 + 定时推送 + 后台通知升级 + 结束后测验）

- [ ] **Step 1: 创建 `PushCards.vue`**

```vue
<template>
  <div class="push-module">
    <div class="module-header">
      <h3>弹卡背诵</h3>
      <p class="subtitle">像通知一样在角落弹出单词，边忙边背</p>
    </div>

    <div class="config-section">
      <el-form :inline="true">
        <el-form-item label="弹卡数量">
          <el-slider v-model="config.count" :min="5" :max="50" :step="5" style="width: 160px" />
          <span style="margin-left: 12px">{{ config.count }} 词</span>
        </el-form-item>
        <el-form-item label="间隔(秒)">
          <el-input-number v-model="config.interval_seconds" :min="15" :max="600" :step="15" />
        </el-form-item>
        <el-form-item label="自动发音">
          <el-switch v-model="config.auto_play" />
        </el-form-item>
        <el-form-item label="词汇分类">
          <el-select v-model="config.category" clearable placeholder="全部" style="width: 150px">
            <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="running" @click="startSession">
            {{ running ? '背单词中…' : '开始弹卡' }}
          </el-button>
          <el-button v-if="running" type="danger" @click="stopSession">停止</el-button>
          <el-button @click="saveConfig">保存配置</el-button>
        </el-form-item>
      </el-form>
      <p v-if="!notifyGranted" class="notify-tip">
        <el-button size="small" type="info" @click="requestNotify">授权浏览器通知（页面后台时升级为系统通知）</el-button>
      </p>
    </div>

    <div v-if="running" class="run-info">
      <p>会话 {{ sessionId }}｜剩余 {{ queue.length }} 词｜已背 {{ doneCount }} 词</p>
      <el-progress :percentage="percent" :stroke-width="10" status="success" />
    </div>

    <!-- 悬浮弹卡 -->
    <Transition name="pop">
      <div v-if="showing && current" class="float-card">
        <div class="fc-top">
          <span class="fc-badge">{{ current.type === 'new' ? '新词' : current.type === 'review' ? '复习' : '学习' }}</span>
          <span class="fc-skip" @click="hideCard">×</span>
        </div>
        <div class="fc-word">{{ current.word }}</div>
        <div class="fc-phonetic">{{ current.phonetic }}</div>
        <div class="fc-meaning">{{ current.meaning }}</div>
        <div class="fc-buttons">
          <el-button size="small" type="danger" @click="rate('忘记')">忘记</el-button>
          <el-button size="small" type="warning" @click="rate('困难')">困难</el-button>
          <el-button size="small" type="info" @click="rate('一般')">一般</el-button>
          <el-button size="small" type="success" @click="rate('认识')">认识</el-button>
          <el-button size="small" @click="playWord"><el-icon><VideoPlay /></el-icon>发音</el-button>
        </div>
      </div>
    </Transition>

    <QuizDialog :visible="quizVisible" :word-ids="sessionWordIds" @close="quizVisible = false" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoPlay } from '@element-plus/icons-vue'
import {
  getSessionCards, studyWord, completeSession, getQuiz,
  getPushConfig, savePushConfig, getWordCategories,
  type SessionCardItem, type PushConfig
} from '@/api/words'
import { useSpeech } from '@/composables/useSpeech'
import QuizDialog from '@/views/recitation/QuizDialog.vue'

const { speak: speakWord } = useSpeech()

const config = reactive<PushConfig>({ count: 10, interval_seconds: 60, category: null, auto_play: true })
const categories = ref<string[]>([])
const running = ref(false)
const sessionId = ref('')
const sessionWordIds = ref<number[]>([])
const queue = ref<SessionCardItem[]>([])
const doneCount = ref(0)
const current = ref<SessionCardItem | null>(null)
const showing = ref(false)
const timers: ReturnType<typeof setTimeout>[] = []
const notifyGranted = ref(false)
const quizVisible = ref(false)

const percent = computed(() => {
  const total = sessionWordIds.value.length
  return total ? Math.round((doneCount.value / total) * 100) : 0
})

function requestNotify() {
  if (!('Notification' in window)) {
    ElMessage.warning('当前浏览器不支持通知')
    return
  }
  Notification.requestPermission().then(p => {
    notifyGranted.value = p === 'granted'
    if (notifyGranted.value) ElMessage.success('通知已开启')
  })
}

async function loadConfig() {
  try {
    const cfg = await getPushConfig()
    Object.assign(config, cfg)
  } catch {
    // 使用默认
  }
  if (config.category === null || config.category === undefined) {
    config.category = ''
  }
}

async function loadCategories() {
  try {
    const res = await getWordCategories()
    categories.value = res.categories.filter(c => c !== '全部')
  } catch {
    categories.value = ['CET-4', 'CET-6', '考研']
  }
}

async function saveConfig() {
  try {
    await savePushConfig({ ...config, category: config.category || null })
    ElMessage.success('配置已保存')
  } catch {
    ElMessage.success('配置已保存')
  }
}

function clearTimers() {
  timers.forEach(t => clearTimeout(t))
  timers.length = 0
}

async function startSession() {
  if (running.value) return
  clearTimers()
  queue.value = []
  current.value = null
  showing.value = false
  doneCount.value = 0
  sessionWordIds.value = []

  const category = config.category || undefined
  try {
    const res = await getSessionCards(config.count, category)
    if (!res.cards.length) {
      ElMessage.warning('没有可背的单词了，换个分类或先学习')
      return
    }
    sessionId.value = res.session_id
    queue.value = [...res.cards]
    sessionWordIds.value = res.cards.map(c => c.word_id)
    running.value = true
    scheduleNext(0)
  } catch {
    ElMessage.error('获取弹卡队列失败')
  }
}

function later(ms: number, fn: () => void) {
  const t = setTimeout(() => {
    const idx = timers.indexOf(t)
    if (idx >= 0) timers.splice(idx, 1)
    fn()
  }, ms)
  timers.push(t)
}

async function showNextCard() {
  if (!running.value) return
  if (queue.value.length === 0) {
    await finishSession()
    return
  }
  current.value = queue.value[0]
  showing.value = true
  if (config.auto_play) playWord()
  if (document.hidden) {
    notifyHiddenCard(current.value)
  }
  later(8000, () => {
    showing.value = false
  })
}

function scheduleNext(delayMs: number) {
  later(delayMs, showNextCard)
}

function notifyHiddenCard(card: SessionCardItem) {
  if (notifyGranted.value && Notification.permission === 'granted') {
    const n = new Notification('弹卡背诵', {
      body: `${card.word}  ${card.phonetic || ''}\n${card.meaning}`,
      icon: '/favicon.ico'
    })
    n.onclick = () => window.focus()
  }
}

function playWord() {
  if (current.value?.word) speakWord(current.value.word, { lang: 'en-US' })
}

async function rate(rating: string) {
  if (!current.value) return
  const word = current.value
  showing.value = false
  doneCount.value++

  try {
    const updated = await studyWord(word.word_id, rating, {
      session_id: sessionId.value || undefined,
      source: 'push'
    })
    const kept = queue.value.shift()
    if (updated?.srs_status !== 'reviewed') {
      const dueMs = Math.round((updated?.due_minutes ?? 1) * 60 * 1000)
      later(dueMs, () => {
        if (kept && running.value) queue.value.push(kept)
      })
    }
  } catch {
    queue.value.shift()
  }

  scheduleNext(config.interval_seconds * 1000)
}

async function finishSession() {
  running.value = false
  showing.value = false
  current.value = null
  clearTimers()
  if (sessionId.value) {
    try {
      await completeSession(sessionId.value)
    } catch {
      // 忽略
    }
  }
  ElMessage.success('本轮弹卡完成！')
  if (sessionWordIds.value.length) {
    quizVisible.value = true
  }
}

function stopSession() {
  running.value = false
  showing.value = false
  current.value = null
  clearTimers()
  if (sessionId.value) {
    completeSession(sessionId.value)
  }
  ElMessage.info('已停止弹卡')
}

function hideCard() {
  showing.value = false
}

onMounted(async () => {
  await loadConfig()
  await loadCategories()
  notifyGranted.value = 'Notification' in window && Notification.permission === 'granted'
})

onUnmounted(() => {
  clearTimers()
})
</script>

<style scoped>
.push-module { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); }
.module-header { margin-bottom: 16px; }
.module-header h3 { margin: 0 0 4px; font-size: 16px; color: #333; }
.subtitle { margin: 0; font-size: 14px; color: #999; }
.config-section { background: #f5f7fa; padding: 16px; border-radius: 8px; }
.notify-tip { margin-top: 8px; }
.run-info { margin-top: 16px; font-size: 13px; color: #666; }
.float-card { position: fixed; right: 24px; bottom: 32px; width: 320px; background: #fff; border: 1px solid #e0e0e0; border-radius: 12px; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.16); padding: 16px; z-index: 3000; text-align: center; }
.fc-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.fc-badge { padding: 2px 8px; background: #dbeafe; color: #3b82f6; border-radius: 4px; font-size: 12px; }
.fc-skip { cursor: pointer; color: #999; font-size: 18px; }
.fc-word { font-size: 28px; font-weight: bold; color: #333; }
.fc-phonetic { font-size: 14px; color: #666; margin: 4px 0; }
.fc-meaning { font-size: 15px; color: #333; margin-bottom: 12px; }
.fc-buttons { display: flex; justify-content: center; gap: 6px; flex-wrap: wrap; }
.pop-enter-active, .pop-leave-active { transition: opacity 0.25s ease, transform 0.25s ease; }
.pop-enter-from { opacity: 0; transform: translateY(12px); }
.pop-leave-to { opacity: 0; }
</style>
```

- [ ] **Step 2: Words.vue 加 tab**

`frontend/src/views/Words.vue`：

```html
      <el-tab-pane label="弹卡背诵" name="push">
        <PushCards />
      </el-tab-pane>
      <el-tab-pane label="背诵记录" name="records">
        <RecordsModule />
      </el-tab-pane>
```

import 区：

```ts
import PushCards from './recitation/PushCards.vue'
import RecordsModule from './recitation/RecordsModule.vue'
```

（RecordsModule 将在 Task 10 创建，若先构建会报错——本任务提交时把 Words.vue 的 records tab 一并交给 Task 10 处理，或本任务先只加 push tab 并在 Task 10 补 records tab，二选一，按执行顺序：**本任务只加 push tab**，Task 10 再加 records tab。）

- [ ] **Step 3: 构建校验**

Run: `cd frontend && npm run build`
Expected: 编译通过

- [ ] **Step 4: 提交**

```bash
git add frontend/src/views/recitation/PushCards.vue
git commit -m "feat: 沉浸式弹卡背诵组件"
```

---

### Task 10: RecordsModule 背诵记录页 + Words.vue 收尾

**Files:**
- Create: `frontend/src/views/recitation/RecordsModule.vue`
- Modify: `frontend/src/views/Words.vue`（加 records tab 并注册导入）

**Interfaces:**
- Consumes: Task 7 `getStudyRecords/exportStudyRecords/importStudyRecords`
- Produces: `RecordsModule.vue` 组件（会话表 + 导出 + 导入）

- [ ] **Step 1: 创建 `RecordsModule.vue`**

```vue
<template>
  <div class="records-module">
    <div class="module-header">
      <h3>背诵记录</h3>
      <div class="header-actions">
        <el-button type="primary" @click="handleExport">
          <el-icon><Download /></el-icon>导出 Excel
        </el-button>
        <el-button type="success" @click="triggerImport">
          <el-icon><Upload /></el-icon>导入复习
        </el-button>
        <input
          ref="importInput"
          type="file"
          accept=".xlsx,.xls"
          class="hidden-input"
          @change="handleImport"
        />
      </div>
    </div>

    <el-table :data="records" border>
      <el-table-column prop="created_at" label="时间" width="180">
        <template #default="scope">
          {{ scope.row.created_at ? scope.row.created_at.substring(0, 16) : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="session_id" label="会话ID" width="120" show-overflow-tooltip />
      <el-table-column prop="source" label="来源" width="90">
        <template #default="scope">
          <el-tag>{{ { card: '卡片', push: '弹卡', quiz: '测验' }[scope.row.source] || scope.row.source }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="total" label="单词数" width="90" />
      <el-table-column label="忘记" width="70">
        <template #default="scope"><span style="color:#f56c6c">{{ scope.row.forgot }}</span></template>
      </el-table-column>
      <el-table-column label="困难" width="70">
        <template #default="scope"><span style="color:#e6a23c">{{ scope.row.hard }}</span></template>
      </el-table-column>
      <el-table-column label="一般" width="70">
        <template #default="scope"><span style="color:#909399">{{ scope.row.good }}</span></template>
      </el-table-column>
      <el-table-column label="认识" width="70">
        <template #default="scope"><span style="color:#67c23a">{{ scope.row.known }}</span></template>
      </el-table-column>
    </el-table>

    <div class="pagination">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="loadRecords"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Upload } from '@element-plus/icons-vue'
import {
  getStudyRecords, exportStudyRecords, importStudyRecords,
  type RecordSummaryItem
} from '@/api/words'

const records = ref<RecordSummaryItem[]>([])
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const importInput = ref<HTMLInputElement | null>(null)

async function loadRecords() {
  try {
    const res = await getStudyRecords(page.value, pageSize.value)
    records.value = res.items
    total.value = res.total
  } catch {
    records.value = []
    total.value = 0
  }
}

async function handleExport() {
  try {
    await exportStudyRecords()
    ElMessage.success('已导出')
  } catch {
    ElMessage.error('导出失败')
  }
}

function triggerImport() {
  importInput.value?.click()
}

async function handleImport(event: Event) {
  const target = event.target as HTMLInputElement
  if (!target.files?.length) return
  const file = target.files[0]
  try {
    const res = await importStudyRecords(file)
    ElMessage.success(res.message || '导入成功')
    await loadRecords()
  } catch (error: any) {
    const msg = error.response?.data?.detail || error.message || '导入失败'
    ElMessage.error(msg)
  } finally {
    if (importInput.value) importInput.value.value = ''
  }
}

onMounted(loadRecords)
</script>

<style scoped>
.records-module { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); }
.module-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.module-header h3 { margin: 0; font-size: 16px; color: #333; }
.header-actions { display: flex; gap: 8px; }
.pagination { margin-top: 16px; text-align: right; }
.hidden-input { display: none; }
</style>
```

- [ ] **Step 2: Words.vue 加 records tab**

`frontend/src/views/Words.vue` —— 在 Task 9 已加的 push tab 之后补：

```html
      <el-tab-pane label="背诵记录" name="records">
        <RecordsModule />
      </el-tab-pane>
```

import 区加 `RecordsModule`。若 Task 9 已把 push tab 加好，此步仅补 records。

- [ ] **Step 3: 构建校验**

Run: `cd frontend && npm run build`
Expected: 编译通过，无类型错误

- [ ] **Step 4: 全量前端构建 + 后端回归**

Run: `cd frontend && npm run build && cd ../backend && python3 tests/test_srs.py && python3 tests/test_study_word_srs.py && python3 tests/test_session_cards.py && python3 tests/test_quiz_api.py && python3 tests/test_records_api.py`
Expected: vue-tsc 无错误；5 个后端测试脚本全部 PASS

- [ ] **Step 5: 提交**

```bash
git add frontend/src/views/recitation/RecordsModule.vue frontend/src/views/Words.vue
git commit -m "feat: 背诵记录页 + 导航 tab 收尾"
```

---

## 验收标准（全部任务完成后人工验证）

1. 卡片背诵：四档按钮可用，认识→掌握/弹卡进度推进，忘记→卡重新入队
2. 弹卡背诵：配置生效，按间隔弹词，后台时弹系统通知，结束后弹出测验
3. 测验：中译英/英译中各 4 选项，答对答错即时反馈，答错词重新入队
4. 记录：背诵记录 tab 出现会话行；导出 xlsx 含「背诵记录」「会话汇总」两张 sheet；导入 xlsx 后单词出现在今日复习
5. 旧数据兼容：老用户的三档历史不影响新评分
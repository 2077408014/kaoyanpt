"""回归测试：删除带有复习记录的错题必须成功。

背景：错题管理界面"删除"只弹确认框、点了没反应。根因是
Mistake 模型上的 reviews 关联未配置级联删除，SQLAlchemy 默认
把 mistake_reviews.mistake_id 置 NULL（而非删除子记录），而该列
nullable=False，导致删除错题抛 IntegrityError → 500；
前端 handleDelete 又把所有异常当成"用户取消"吞掉，用户只看到弹窗。

运行方式（无需 pytest）：
    python3 backend/tests/test_mistake_delete_with_reviews.py
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.mistake import Mistake, MistakeReview
from app.services.mistake_service import mistake_service
from app.schemas.mistake import MistakeCreate, MistakeReviewCreate


def _setup():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return Session()


def _create_mistake_with_review(db, user_id=1):
    mistake = mistake_service.create_mistake(
        db, user_id, MistakeCreate(subject="数学", knowledge_point="测试点", question_text="测试题目")
    )
    mistake_service.review_mistake(db, user_id, mistake.id, MistakeReviewCreate(result="正确"))
    return mistake


def test_delete_mistake_with_reviews_succeeds():
    """删除带复习记录的错题必须成功，且级联删除复习记录。"""
    db = _setup()
    mistake = _create_mistake_with_review(db)
    assert db.query(MistakeReview).count() == 1

    ok = mistake_service.delete_mistake(db, 1, mistake.id)

    assert ok is True
    assert db.query(Mistake).count() == 0
    assert db.query(MistakeReview).count() == 0, "删除错题应级联删除其复习记录"


def test_delete_mistake_without_reviews_succeeds():
    """普通错题删除仍然正常。"""
    db = _setup()
    mistake = mistake_service.create_mistake(
        db, 1, MistakeCreate(subject="数学", knowledge_point="测试点", question_text="测试题目")
    )

    ok = mistake_service.delete_mistake(db, 1, mistake.id)

    assert ok is True
    assert db.query(Mistake).count() == 0


if __name__ == "__main__":
    test_delete_mistake_without_reviews_succeeds()
    test_delete_mistake_with_reviews_succeeds()
    print("PASS: 所有错题删除测试通过")
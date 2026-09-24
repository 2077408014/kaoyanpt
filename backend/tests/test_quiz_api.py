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
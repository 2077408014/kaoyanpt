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
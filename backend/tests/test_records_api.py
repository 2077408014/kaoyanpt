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
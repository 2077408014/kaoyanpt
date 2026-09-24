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
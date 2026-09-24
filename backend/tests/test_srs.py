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

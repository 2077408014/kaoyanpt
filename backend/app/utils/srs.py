"""SM2+ 四档单词复习算法（借鉴 ToastFish SM2plus）。

纯逻辑模块，不依赖数据库。
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
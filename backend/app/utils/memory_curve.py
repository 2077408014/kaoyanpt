from datetime import date, timedelta
from typing import Optional

# ==== 单词 SRS 间隔 ====
KNOWN_INTERVALS = [1, 3, 7, 15]   # 认识
VAGUE_INTERVALS = [1, 2, 4, 8]    # 模糊
UNKNOWN_INTERVAL = 1              # 不认识（次日）

# ==== 错题复习（保留旧导出兼容 mistake_service） ====
MASTERY_LEVELS = ["生疏", "接触", "认识", "熟悉", "掌握"]
REVIEW_INTERVALS = [1, 3, 7, 14, 30]
DIFFICULTY_MULTIPLIER = {"简单": 0.8, "中等": 1.0, "困难": 1.5}


def calculate_word_next_review(
    last_rating: Optional[str],
    srs_stage: int
) -> tuple:
    """根据用户评级计算下次复习日期和新的SRS阶段。

    规则：
    - 认识：间隔序列 1→3→7→15 天，stage 递进
    - 模糊：间隔序列 1→2→4→8 天，stage 退回到 max(stage-1, 0)
    - 不认识：次日复习，stage 重置为 0

    返回: (next_review_date, new_srs_stage)
    """
    today = date.today()

    if last_rating == "认识":
        interval = KNOWN_INTERVALS[min(srs_stage, len(KNOWN_INTERVALS) - 1)]
        new_stage = min(srs_stage + 1, len(KNOWN_INTERVALS) - 1)
        return today + timedelta(days=interval), new_stage

    if last_rating == "模糊":
        interval = VAGUE_INTERVALS[min(srs_stage, len(VAGUE_INTERVALS) - 1)]
        new_stage = max(srs_stage - 1, 0)
        return today + timedelta(days=interval), new_stage

    if last_rating == "不认识":
        return today + timedelta(days=UNKNOWN_INTERVAL), 0

    # 默认（首次学习或无评级）
    return today + timedelta(days=1), 0


def get_mastery_level_from_rating(last_rating: Optional[str], current_level: str) -> str:
    """根据本次评级更新掌握程度标签（兼容旧逻辑）。"""
    levels = ["陌生", "认识", "熟悉", "掌握"]
    idx = levels.index(current_level) if current_level in levels else 0

    if last_rating == "认识":
        idx = min(idx + 1, len(levels) - 1)
    elif last_rating == "模糊":
        idx = max(idx - 1, 0)
    elif last_rating == "不认识":
        idx = 0

    return levels[idx]


def calculate_next_review_date(
    current_level: str,
    difficulty: str = "中等",
    review_count: int = 0,
    correct_count: int = 0
) -> tuple:
    """错题复习：根据掌握程度和难度计算下次复习日期。（兼容旧接口）"""
    try:
        base_multiplier = DIFFICULTY_MULTIPLIER.get(difficulty, 1.0)
    except Exception:
        base_multiplier = 1.0

    try:
        level_index = MASTERY_LEVELS.index(current_level)
    except ValueError:
        level_index = 0

    interval_index = min(review_count, len(REVIEW_INTERVALS) - 1)
    base_interval = REVIEW_INTERVALS[interval_index]

    adjusted_interval = max(1, round(base_interval * base_multiplier))

    if correct_count >= max(review_count * 0.8, 2):
        level_index = min(level_index + 1, len(MASTERY_LEVELS) - 1)
    elif correct_count < review_count * 0.5:
        level_index = max(level_index - 1, 0)

    next_date = date.today() + timedelta(days=adjusted_interval)
    return next_date, MASTERY_LEVELS[level_index]


def calculate_next_review(mastery_level: str) -> date:
    """政治复习：根据掌握程度计算下次复习日期。"""
    try:
        level_index = MASTERY_LEVELS.index(mastery_level)
    except ValueError:
        level_index = 0

    interval = REVIEW_INTERVALS[min(level_index, len(REVIEW_INTERVALS) - 1)]
    return date.today() + timedelta(days=interval)
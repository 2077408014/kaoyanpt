"""学习时长跟踪服务。

独立维护 UserStudyStat 写入逻辑：
- 接收前端心跳（按秒累计学习时长）
- 接收学习事件（错题/单词/题目计数）
- 自动 upsert 当日统计记录
"""
from datetime import datetime, date as date_type

from sqlalchemy.orm import Session

from ..models.study_stat import UserStudyStat


class StudyTrackerService:
    def _get_or_create_today(self, db: Session, user_id: int, today: date_type) -> UserStudyStat:
        stat = db.query(UserStudyStat).filter(
            UserStudyStat.user_id == user_id,
            UserStudyStat.study_date == today,
        ).first()

        if not stat:
            stat = UserStudyStat(
                user_id=user_id,
                study_date=today,
                total_time=0,
                words_studied=0,
                mistakes_added=0,
                questions_completed=0,
            )
            db.add(stat)
            db.commit()
            db.refresh(stat)

        return stat

    def add_study_time(self, db: Session, user_id: int, seconds: int) -> dict:
        if seconds <= 0:
            return self._today_snapshot(db, user_id)

        # 限制单次最多累计 30 分钟，防止异常数据
        seconds = min(seconds, 30 * 60)

        today = datetime.now().date()
        stat = self._get_or_create_today(db, user_id, today)
        stat.total_time = (stat.total_time or 0) + int(seconds)
        db.commit()
        db.refresh(stat)

        return self._today_snapshot(db, user_id)

    def increment_counter(self, db: Session, user_id: int, field: str, delta: int = 1) -> dict:
        if field not in {"words_studied", "mistakes_added", "questions_completed"}:
            raise ValueError(f"不支持的统计字段: {field}")
        if delta <= 0:
            return self._today_snapshot(db, user_id)

        today = datetime.now().date()
        stat = self._get_or_create_today(db, user_id, today)
        setattr(stat, field, (getattr(stat, field) or 0) + int(delta))
        db.commit()
        db.refresh(stat)

        return self._today_snapshot(db, user_id)

    def _today_snapshot(self, db: Session, user_id: int) -> dict:
        today = datetime.now().date()
        stat = db.query(UserStudyStat).filter(
            UserStudyStat.user_id == user_id,
            UserStudyStat.study_date == today,
        ).first()

        if not stat:
            return {
                "study_date": today.isoformat(),
                "total_time": 0,
                "words_studied": 0,
                "mistakes_added": 0,
                "questions_completed": 0,
            }

        return {
            "study_date": today.isoformat(),
            "total_time": stat.total_time or 0,
            "words_studied": stat.words_studied or 0,
            "mistakes_added": stat.mistakes_added or 0,
            "questions_completed": stat.questions_completed or 0,
        }


study_tracker_service = StudyTrackerService()
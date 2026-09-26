"""面向教师/机构看板的只读学习统计聚合。

所有方法都只做查询，不写数据。授权集合由调用方（API 层）先经
organization_service 计算后传入：student_ids 为集合时限权，None 表示超管不限。
"""
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.user import User
from ..models.study_stat import UserStudyStat
from ..models.mistake import Mistake
from ..models.supervision import StudySupervisionRecord
from ..models.organization import ClassStudent, MEMBER_ACTIVE

# 监督记录中只有 focused 视为正常，其余（走神/离开/未知）均计为异常
ABNORMAL_STATUSES = ("distracted", "absent", "unknown")
MASTERED_LEVEL = "掌握"


def _scope_filter(query, column, student_ids: Optional[set]):
    if student_ids is not None:
        if not student_ids:
            return query.filter(column.in_([-1]))  # 空集：永不命中
        query = query.filter(column.in_(student_ids))
    return query


class StatsQueryService:
    RECENT_DAYS = 7

    def _recent_start(self, days: Optional[int] = None) -> date:
        days = days or self.RECENT_DAYS
        return date.today() - timedelta(days=days - 1)

    # ---------- 单学生 ----------
    def student_summary(self, db: Session, student_id: int) -> dict:
        start = self._recent_start()
        agg = db.query(
            func.coalesce(func.sum(UserStudyStat.total_time), 0),
            func.coalesce(func.sum(UserStudyStat.words_studied), 0),
            func.coalesce(func.sum(UserStudyStat.questions_completed), 0),
        ).filter(
            UserStudyStat.user_id == student_id,
            UserStudyStat.study_date >= start,
        ).one()

        total_mistakes = db.query(func.count(Mistake.id)).filter(
            Mistake.user_id == student_id
        ).scalar()
        abnormal = db.query(func.count(StudySupervisionRecord.id)).filter(
            StudySupervisionRecord.user_id == student_id,
            StudySupervisionRecord.status.in_(ABNORMAL_STATUSES),
        ).scalar()

        return {
            "study_time_7d": int(agg[0] or 0) // 60,  # 秒 → 分钟
            "words_7d": int(agg[1] or 0),
            "questions_7d": int(agg[2] or 0),
            "total_mistakes": int(total_mistakes or 0),
            "supervision_abnormal": int(abnormal or 0),
        }

    def student_overview(self, db: Session, student_id: int) -> dict:
        summary = self.student_summary(db, student_id)

        # 错题掌握度分布
        rows = db.query(
            Mistake.mastery_level, func.count(Mistake.id)
        ).filter(Mistake.user_id == student_id).group_by(Mistake.mastery_level).all()
        distribution = {level: int(cnt) for level, cnt in rows}
        summary["mastery_distribution"] = distribution
        summary["mastered_mistakes"] = int(distribution.get(MASTERED_LEVEL, 0))

        # 近 7 天按日趋势：学习时长 / 单词 / 做题 / 新增错题 / 监督异常
        start = self._recent_start()
        stat_rows = db.query(
            UserStudyStat.study_date,
            func.coalesce(func.sum(UserStudyStat.total_time), 0),
            func.coalesce(func.sum(UserStudyStat.words_studied), 0),
            func.coalesce(func.sum(UserStudyStat.questions_completed), 0),
        ).filter(
            UserStudyStat.user_id == student_id,
            UserStudyStat.study_date >= start,
        ).group_by(UserStudyStat.study_date).all()
        stat_map = {
            r[0]: (int(r[1] or 0), int(r[2] or 0), int(r[3] or 0))
            for r in stat_rows
        }

        def _count_by_day(model, day_col, extra_filters=()):
            rows = db.query(
                func.date(day_col), func.count()
            ).filter(
                model.user_id == student_id,
                func.date(day_col) >= start,
                *extra_filters,
            ).group_by(func.date(day_col)).all()
            return {date.fromisoformat(str(day)): int(cnt) for day, cnt in rows}

        mistake_by_day = _count_by_day(Mistake, Mistake.created_at)
        abnormal_by_day = _count_by_day(
            StudySupervisionRecord, StudySupervisionRecord.created_at,
            (StudySupervisionRecord.status.in_(ABNORMAL_STATUSES),),
        )

        daily = []
        for i in range(self.RECENT_DAYS):
            d = start + timedelta(days=i)
            study_sec, words, questions = stat_map.get(d, (0, 0, 0))
            daily.append({
                "date": d.isoformat(),
                "study_time": study_sec // 60,
                "words": words,
                "questions": questions,
                "mistakes": mistake_by_day.get(d, 0),
                "abnormal": abnormal_by_day.get(d, 0),
            })
        summary["daily"] = daily
        return summary

    # ---------- 班级 ----------
    def class_member_ids(self, db: Session, class_id: int) -> list[int]:
        """聚合口径：仅统计 active 成员，暂停成员不计入班级看板。"""
        rows = db.query(ClassStudent.student_id).filter(
            ClassStudent.class_id == class_id,
            ClassStudent.status == MEMBER_ACTIVE,
        ).all()
        return [r[0] for r in rows]

    def class_student_summaries(self, db: Session, class_id: int) -> list[dict]:
        members = (
            db.query(User, ClassStudent.joined_at, ClassStudent.status)
            .join(ClassStudent, ClassStudent.student_id == User.id)
            .filter(ClassStudent.class_id == class_id)
            .order_by(ClassStudent.joined_at.asc())
            .all()
        )
        result = []
        for user, joined_at, status in members:
            item = {
                "id": user.id, "username": user.username,
                "email": user.email, "joined_at": joined_at,
                "status": status or MEMBER_ACTIVE,
            }
            item.update(self.student_summary(db, user.id))
            result.append(item)
        return result

    def class_summary(self, db: Session, class_id: int) -> dict:
        ids = self.class_member_ids(db, class_id)
        start = self._recent_start()
        n = len(ids)
        if n == 0:
            return {
                "student_count": 0,
                "avg_study_time_7d": 0.0,
                "avg_words_7d": 0.0,
                "avg_questions_7d": 0.0,
                "avg_mistakes": 0.0,
                "total_mistakes": 0,
                "supervision_abnormal": 0,
            }
        agg = db.query(
            func.coalesce(func.sum(UserStudyStat.total_time), 0),
            func.coalesce(func.sum(UserStudyStat.words_studied), 0),
            func.coalesce(func.sum(UserStudyStat.questions_completed), 0),
        ).filter(
            UserStudyStat.user_id.in_(ids),
            UserStudyStat.study_date >= start,
        ).one()
        total_mistakes = db.query(func.count(Mistake.id)).filter(
            Mistake.user_id.in_(ids)
        ).scalar()
        abnormal = db.query(func.count(StudySupervisionRecord.id)).filter(
            StudySupervisionRecord.user_id.in_(ids),
            StudySupervisionRecord.status.in_(ABNORMAL_STATUSES),
        ).scalar()
        return {
            "student_count": n,
            "avg_study_time_7d": round((int(agg[0] or 0) / 60) / n, 1),
            "avg_words_7d": round(int(agg[1] or 0) / n, 1),
            "avg_questions_7d": round(int(agg[2] or 0) / n, 1),
            "avg_mistakes": round(int(total_mistakes or 0) / n, 1),
            "total_mistakes": int(total_mistakes or 0),
            "supervision_abnormal": int(abnormal or 0),
        }


stats_query_service = StatsQueryService()

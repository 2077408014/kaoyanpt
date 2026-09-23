from datetime import date

from sqlalchemy.orm import Session

from ..models.study_stat import UserStudyStat


class StudyStatService:
    def record(
        self,
        db: Session,
        user_id: int,
        words: int = 0,
        mistakes: int = 0,
        questions: int = 0,
        time_seconds: int = 0,
    ) -> None:
        today = date.today()
        stat = db.query(UserStudyStat).filter(
            UserStudyStat.user_id == user_id,
            UserStudyStat.study_date == today,
        ).first()

        if not stat:
            stat = UserStudyStat(user_id=user_id, study_date=today)
            db.add(stat)

        stat.words_studied = (stat.words_studied or 0) + words
        stat.mistakes_added = (stat.mistakes_added or 0) + mistakes
        stat.questions_completed = (stat.questions_completed or 0) + questions
        stat.total_time = (stat.total_time or 0) + time_seconds
        db.commit()


study_stat_service = StudyStatService()
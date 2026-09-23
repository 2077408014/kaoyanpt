from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from ..models.word import UserWord
from ..models.mistake import Mistake
from ..models.recommendation import Recommendation
from ..models.study_stat import UserStudyStat


class ReportService:
    def generate_study_report(self, db: Session, user_id: int, period: str = "week") -> dict:
        now = datetime.now()
        
        if period == "day":
            start_date = now.date()
            end_date = now.date()
        elif period == "week":
            start_date = (now - timedelta(days=now.weekday())).date()
            end_date = (now + timedelta(days=6 - now.weekday())).date()
        elif period == "month":
            start_date = now.replace(day=1).date()
            end_date = now.date()
        else:
            start_date = (now - timedelta(days=30)).date()
            end_date = now.date()
        
        word_stats = self._get_word_stats(db, user_id, start_date, end_date)
        mistake_stats = self._get_mistake_stats(db, user_id, start_date, end_date)
        recommendation_stats = self._get_recommendation_stats(db, user_id, start_date, end_date)
        overall_stats = self._get_overall_stats(db, user_id)
        
        return {
            "period": period,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "word_stats": word_stats,
            "mistake_stats": mistake_stats,
            "recommendation_stats": recommendation_stats,
            "overall_stats": overall_stats
        }
    
    def _get_word_stats(self, db: Session, user_id: int, start_date, end_date) -> dict:
        total_words = db.query(UserWord).filter(UserWord.user_id == user_id).count()
        
        mastered_count = db.query(UserWord).filter(
            UserWord.user_id == user_id,
            UserWord.mastery_level == "掌握"
        ).count()
        
        learned_this_period = db.query(UserWord).filter(
            UserWord.user_id == user_id,
            UserWord.last_study_date != None,
            UserWord.last_study_date >= datetime.combine(start_date, datetime.min.time()),
            UserWord.last_study_date <= datetime.combine(end_date, datetime.max.time())
        ).count()
        
        today_review = db.query(UserWord).filter(
            UserWord.user_id == user_id,
            UserWord.next_review_date <= datetime.now().date()
        ).count()
        
        return {
            "total_words": total_words,
            "mastered_count": mastered_count,
            "learned_this_period": learned_this_period,
            "today_review": today_review,
            "mastery_rate": round(mastered_count / max(total_words, 1) * 100, 1)
        }
    
    def _get_mistake_stats(self, db: Session, user_id: int, start_date, end_date) -> dict:
        total_mistakes = db.query(Mistake).filter(Mistake.user_id == user_id).count()
        
        added_this_period = db.query(Mistake).filter(
            Mistake.user_id == user_id,
            Mistake.created_at >= datetime.combine(start_date, datetime.min.time()),
            Mistake.created_at <= datetime.combine(end_date, datetime.max.time())
        ).count()
        
        mastered_mistakes = db.query(Mistake).filter(
            Mistake.user_id == user_id,
            Mistake.mastery_level == "掌握"
        ).count()
        
        today_review = db.query(Mistake).filter(
            Mistake.user_id == user_id,
            Mistake.next_review_date <= datetime.now().date()
        ).count()
        
        by_subject = db.query(
            Mistake.subject,
            func.count(Mistake.id).label('count')
        ).filter(Mistake.user_id == user_id).group_by(Mistake.subject).all()
        
        return {
            "total_mistakes": total_mistakes,
            "added_this_period": added_this_period,
            "mastered_mistakes": mastered_mistakes,
            "today_review": today_review,
            "mastery_rate": round(mastered_mistakes / max(total_mistakes, 1) * 100, 1),
            "by_subject": [{"subject": s, "count": c} for s, c in by_subject]
        }
    
    def _get_recommendation_stats(self, db: Session, user_id: int, start_date, end_date) -> dict:
        total_recommendations = db.query(Recommendation).filter(
            Recommendation.user_id == user_id
        ).count()
        
        completed_this_period = db.query(Recommendation).filter(
            Recommendation.user_id == user_id,
            Recommendation.completed == True,
            Recommendation.completion_time >= datetime.combine(start_date, datetime.min.time()),
            Recommendation.completion_time <= datetime.combine(end_date, datetime.max.time())
        ).count()
        
        total_completed = db.query(Recommendation).filter(
            Recommendation.user_id == user_id,
            Recommendation.completed == True
        ).count()
        
        success_rate = 0
        if total_completed > 0:
            success_count = db.query(Recommendation).filter(
                Recommendation.user_id == user_id,
                Recommendation.completed == True,
                Recommendation.result == "正确"
            ).count()
            success_rate = round(success_count / total_completed * 100, 1)
        
        return {
            "total_recommendations": total_recommendations,
            "completed_this_period": completed_this_period,
            "total_completed": total_completed,
            "completion_rate": round(total_completed / max(total_recommendations, 1) * 100, 1),
            "success_rate": success_rate
        }
    
    def _get_overall_stats(self, db: Session, user_id: int) -> dict:
        total_days = db.query(UserStudyStat).filter(UserStudyStat.user_id == user_id).count()
        
        avg_daily_time = 0
        if total_days > 0:
            total_time = db.query(func.sum(UserStudyStat.total_time)).filter(
                UserStudyStat.user_id == user_id
            ).scalar() or 0
            avg_daily_time = round(total_time / total_days / 60, 0)
        
        return {
            "total_study_days": total_days,
            "avg_daily_time": avg_daily_time
        }
    
    def get_weekly_trend(self, db: Session, user_id: int) -> list:
        now = datetime.now()
        trend = []
        
        for i in range(6, -1, -1):
            date = (now - timedelta(days=i)).date()
            stats = db.query(UserStudyStat).filter(
            UserStudyStat.user_id == user_id,
            UserStudyStat.study_date == date
        ).first()
            
            trend.append({
                "date": date.isoformat(),
                "total_time": stats.total_time if stats else 0,
                "words_studied": stats.words_studied if stats else 0,
                "mistakes_added": stats.mistakes_added if stats else 0,
                "questions_completed": stats.questions_completed if stats else 0
            })
        
        return trend


report_service = ReportService()
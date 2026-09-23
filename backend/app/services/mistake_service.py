from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from datetime import date
from ..models.mistake import Mistake, MistakeReview
from ..schemas.mistake import MistakeCreate, MistakeUpdate, MistakeReviewCreate
from ..utils.memory_curve import calculate_next_review_date
from .study_stat_service import study_stat_service

class MistakeService:
    def create_mistake(self, db: Session, user_id: int, data: MistakeCreate) -> Mistake:
        if not data.question_text and not data.image_path:
            raise ValueError("题目文本和图片至少提供一项")

        difficulty = data.difficulty or "中等"
        next_review_date, _ = calculate_next_review_date(
            current_level="生疏",
            difficulty=difficulty,
            review_count=0,
            correct_count=0
        )

        mistake = Mistake(
            user_id=user_id,
            subject=data.subject,
            knowledge_point=data.knowledge_point or "未分类",
            error_type=data.error_type or "未分类",
            difficulty=difficulty,
            mastery_level="生疏",
            question_text=data.question_text or "",
            answer=data.answer or "",
            analysis=data.analysis,
            error_reason=data.error_reason,
            image_path=data.image_path,
            next_review_date=next_review_date
        )
        db.add(mistake)
        db.commit()
        db.refresh(mistake)
        study_stat_service.record(db, user_id, mistakes=1)
        return mistake

    def get_mistakes(self, db: Session, user_id: int, filters: Optional[dict] = None) -> list:
        query = db.query(Mistake).filter(Mistake.user_id == user_id)
        
        if filters:
            if filters.get("subject"):
                query = query.filter(Mistake.subject == filters["subject"])
            if filters.get("knowledge_point"):
                query = query.filter(Mistake.knowledge_point == filters["knowledge_point"])
            if filters.get("error_type"):
                query = query.filter(Mistake.error_type == filters["error_type"])
            if filters.get("difficulty"):
                query = query.filter(Mistake.difficulty == filters["difficulty"])
            if filters.get("mastery_level"):
                query = query.filter(Mistake.mastery_level == filters["mastery_level"])
        
        return query.order_by(Mistake.created_at.desc()).all()

    def get_mistake_by_id(self, db: Session, user_id: int, mistake_id: int) -> Optional[Mistake]:
        return db.query(Mistake).filter(
            and_(Mistake.id == mistake_id, Mistake.user_id == user_id)
        ).first()

    def update_mistake(self, db: Session, user_id: int, mistake_id: int, data: MistakeUpdate) -> Optional[Mistake]:
        mistake = self.get_mistake_by_id(db, user_id, mistake_id)
        if not mistake:
            return None
        
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(mistake, key, value)
        
        db.commit()
        db.refresh(mistake)
        return mistake

    def delete_mistake(self, db: Session, user_id: int, mistake_id: int) -> bool:
        mistake = self.get_mistake_by_id(db, user_id, mistake_id)
        if not mistake:
            return False
        
        db.delete(mistake)
        db.commit()
        return True

    def review_mistake(self, db: Session, user_id: int, mistake_id: int, data: MistakeReviewCreate) -> MistakeReview:
        mistake = self.get_mistake_by_id(db, user_id, mistake_id)
        if not mistake:
            raise ValueError("错题不存在")
        
        review = MistakeReview(
            mistake_id=mistake_id,
            user_id=user_id,
            result=data.result,
            notes=data.notes
        )
        db.add(review)
        
        mistake.review_count += 1
        if data.result == "正确":
            mistake.correct_count += 1
        
        next_date, new_level = calculate_next_review_date(
            current_level=mistake.mastery_level,
            difficulty=mistake.difficulty,
            review_count=mistake.review_count,
            correct_count=mistake.correct_count
        )
        
        mistake.next_review_date = next_date
        mistake.mastery_level = new_level
        
        db.commit()
        db.refresh(review)
        return review

    def get_today_reviews(self, db: Session, user_id: int) -> list:
        today = date.today()
        return db.query(Mistake).filter(
            and_(
                Mistake.user_id == user_id,
                Mistake.next_review_date <= today
            )
        ).all()

    def get_similar_mistakes(self, db: Session, user_id: int, mistake_id: int, limit: int = 5) -> list:
        mistake = self.get_mistake_by_id(db, user_id, mistake_id)
        if not mistake:
            return []

        query = db.query(Mistake).filter(
            and_(
                Mistake.user_id == user_id,
                Mistake.id != mistake_id,
                Mistake.subject == mistake.subject
            )
        )

        results = query.all()
        scored = []
        for m in results:
            score = 0.0
            if m.knowledge_point and mistake.knowledge_point:
                if m.knowledge_point == mistake.knowledge_point:
                    score += 0.5
                elif m.knowledge_point in mistake.knowledge_point or mistake.knowledge_point in m.knowledge_point:
                    score += 0.3
            if m.question_text and mistake.question_text:
                chars1 = set(mistake.question_text[:200])
                chars2 = set(m.question_text[:200])
                if chars1 and chars2:
                    score += len(chars1 & chars2) / len(chars1 | chars2) * 0.5
            scored.append((m, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [{"mistake": m, "similarity_score": s} for m, s in scored[:limit]]

mistake_service = MistakeService()
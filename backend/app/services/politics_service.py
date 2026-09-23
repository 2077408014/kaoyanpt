from sqlalchemy.orm import Session
from datetime import date
from ..models.politics import PoliticsRecitation, RecitationReminder
from ..schemas.politics import (
    PoliticsRecitationCreate, PoliticsRecitationUpdate,
    RecitationReminderCreate, RecitationReminderUpdate
)
from ..utils.memory_curve import calculate_next_review
from ..services.ocr_service import ocr_service
from ..core.config import UPLOAD_PATH
import os


class PoliticsService:
    def get_recitations(self, db: Session, user_id: int, category: str = None,
                        mastery_level: str = None) -> list:
        query = db.query(PoliticsRecitation).filter(PoliticsRecitation.user_id == user_id)
        if category:
            query = query.filter(PoliticsRecitation.category == category)
        if mastery_level:
            query = query.filter(PoliticsRecitation.mastery_level == mastery_level)
        return query.order_by(PoliticsRecitation.created_at.desc()).all()

    def get_recitation(self, db: Session, user_id: int, recitation_id: int) -> PoliticsRecitation:
        return db.query(PoliticsRecitation).filter(
            PoliticsRecitation.id == recitation_id,
            PoliticsRecitation.user_id == user_id
        ).first()

    def create_recitation(self, db: Session, user_id: int, data: PoliticsRecitationCreate) -> PoliticsRecitation:
        recitation = PoliticsRecitation(
            user_id=user_id,
            title=data.title,
            category=data.category or "马原",
            content=data.content,
            image_path=data.image_path,
            next_review_date=date.today()
        )
        db.add(recitation)
        db.commit()
        db.refresh(recitation)
        return recitation

    def update_recitation(self, db: Session, user_id: int, recitation_id: int,
                          data: PoliticsRecitationUpdate) -> PoliticsRecitation:
        recitation = self.get_recitation(db, user_id, recitation_id)
        if not recitation:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(recitation, key, value)
        db.commit()
        db.refresh(recitation)
        return recitation

    def delete_recitation(self, db: Session, user_id: int, recitation_id: int) -> bool:
        recitation = self.get_recitation(db, user_id, recitation_id)
        if not recitation:
            return False
        db.delete(recitation)
        db.commit()
        return True

    def review_recitation(self, db: Session, user_id: int, recitation_id: int,
                          result: str) -> PoliticsRecitation:
        recitation = self.get_recitation(db, user_id, recitation_id)
        if not recitation:
            return None
        recitation.review_count += 1
        if result == "已掌握":
            if recitation.mastery_level == "生疏":
                recitation.mastery_level = "熟悉"
            elif recitation.mastery_level == "熟悉":
                recitation.mastery_level = "掌握"
        elif result == "需复习":
            if recitation.mastery_level == "掌握":
                recitation.mastery_level = "熟悉"
            elif recitation.mastery_level == "熟悉":
                recitation.mastery_level = "生疏"
        elif result == "未掌握":
            recitation.mastery_level = "生疏"
        recitation.next_review_date = calculate_next_review(recitation.mastery_level)
        recitation.last_review_date = date.today()
        db.commit()
        db.refresh(recitation)
        return recitation

    def recognize_image(self, image_path: str) -> dict:
        full_path = UPLOAD_PATH / image_path
        if not os.path.exists(full_path):
            return {"content": "", "confidence": 0.0}
        return ocr_service.recognize_politics(str(full_path))

    def get_reminders(self, db: Session, user_id: int, reminder_type: str = None) -> list:
        query = db.query(RecitationReminder).filter(RecitationReminder.user_id == user_id)
        if reminder_type:
            query = query.filter(RecitationReminder.reminder_type == reminder_type)
        return query.order_by(RecitationReminder.reminder_time).all()

    def create_reminder(self, db: Session, user_id: int, data: RecitationReminderCreate) -> RecitationReminder:
        reminder = RecitationReminder(
            user_id=user_id,
            reminder_type=data.reminder_type,
            reminder_time=data.reminder_time,
            frequency=data.frequency,
            enabled=1
        )
        db.add(reminder)
        db.commit()
        db.refresh(reminder)
        return reminder

    def update_reminder(self, db: Session, user_id: int, reminder_id: int,
                        data: RecitationReminderUpdate) -> RecitationReminder:
        reminder = db.query(RecitationReminder).filter(
            RecitationReminder.id == reminder_id,
            RecitationReminder.user_id == user_id
        ).first()
        if not reminder:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(reminder, key, value)
        db.commit()
        db.refresh(reminder)
        return reminder

    def delete_reminder(self, db: Session, user_id: int, reminder_id: int) -> bool:
        reminder = db.query(RecitationReminder).filter(
            RecitationReminder.id == reminder_id,
            RecitationReminder.user_id == user_id
        ).first()
        if not reminder:
            return False
        db.delete(reminder)
        db.commit()
        return True


politics_service = PoliticsService()

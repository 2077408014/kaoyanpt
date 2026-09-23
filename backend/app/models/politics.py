from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.sql import func
from ..core.database import Base


class PoliticsRecitation(Base):
    __tablename__ = "politics_recitations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False, default="马原")
    content = Column(Text, nullable=False)
    image_path = Column(String(500), nullable=True)
    mastery_level = Column(String(20), nullable=False, default="生疏")
    review_count = Column(Integer, nullable=False, default=0)
    next_review_date = Column(Date, nullable=True)
    last_review_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class RecitationReminder(Base):
    __tablename__ = "recitation_reminders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reminder_type = Column(String(20), nullable=False, default="单词")
    reminder_time = Column(String(10), nullable=False, default="08:00")
    frequency = Column(String(20), nullable=False, default="每天")
    enabled = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

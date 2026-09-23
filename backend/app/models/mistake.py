from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..core.database import Base

class Mistake(Base):
    __tablename__ = "mistakes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject = Column(String(50), nullable=False)
    knowledge_point = Column(String(100), nullable=False)
    error_type = Column(String(50), nullable=False)
    difficulty = Column(String(20), nullable=False)
    mastery_level = Column(String(20), nullable=False, default="生疏")
    question_text = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    analysis = Column(Text, nullable=True)
    error_reason = Column(Text, nullable=True)
    image_path = Column(String(500), nullable=True)
    next_review_date = Column(Date, nullable=True)
    review_count = Column(Integer, nullable=False, default=0)
    correct_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    reviews = relationship("MistakeReview", back_populates="mistake")

class MistakeReview(Base):
    __tablename__ = "mistake_reviews"

    id = Column(Integer, primary_key=True, index=True)
    mistake_id = Column(Integer, ForeignKey("mistakes.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    result = Column(String(20), nullable=False)
    review_date = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text, nullable=True)

    mistake = relationship("Mistake", back_populates="reviews")
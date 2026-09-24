from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base

class Word(Base):
    __tablename__ = "words"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String(50), index=True, nullable=False)
    phonetic = Column(String(100), nullable=True)
    meaning = Column(Text, nullable=False)
    example_sentence = Column(Text, nullable=True)
    difficulty = Column(Integer, nullable=False, default=1)
    frequency = Column(Integer, nullable=False, default=0)
    exam_requirement = Column(String(20), nullable=False, default="考纲", server_default="考纲")
    category = Column(String(20), nullable=False, default="CET-4", server_default="CET-4")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

class UserWord(Base):
    __tablename__ = "user_words"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    mastery_level = Column(String(20), nullable=False, default="陌生")
    next_review_date = Column(Date, nullable=True)
    review_count = Column(Integer, nullable=False, default=0)
    correct_count = Column(Integer, nullable=False, default=0)
    last_study_date = Column(DateTime(timezone=True), nullable=True)
    first_study_date = Column(Date, nullable=True)
    last_rating = Column(String(20), nullable=True)
    srs_stage = Column(Integer, nullable=False, default=0, server_default="0")
    srs_status = Column(String(20), nullable=False, default="new", server_default="new")
    difficulty = Column(Float, nullable=False, default=0.3, server_default="0.3")
    days_between_reviews = Column(Float, nullable=False, default=3.0, server_default="3.0")

    word = relationship("Word", lazy="joined")


class StudyRecord(Base):
    __tablename__ = "study_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String(64), nullable=False, index=True)
    word_id = Column(Integer, ForeignKey("words.id"), nullable=False)
    word = Column(String(50), nullable=False)
    phonetic = Column(String(100), nullable=True)
    meaning = Column(Text, nullable=False)
    rating = Column(String(20), nullable=False)
    quiz_result = Column(Boolean, nullable=True)
    source = Column(String(20), nullable=False, default="card", server_default="card")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
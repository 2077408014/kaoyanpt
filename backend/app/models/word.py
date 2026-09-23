from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey
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
    exam_requirement = Column(String(20), nullable=False, default="考纲")
    category = Column(String(20), nullable=False, default="CET-4")
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
    srs_stage = Column(Integer, nullable=False, default=0)

    word = relationship("Word", lazy="joined")
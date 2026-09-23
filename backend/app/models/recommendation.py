from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from ..core.database import Base

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject = Column(String(50), nullable=False)
    knowledge_point = Column(String(100), nullable=False)
    difficulty = Column(String(20), nullable=False)
    question_text = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    analysis = Column(Text, nullable=True)
    source = Column(String(100), nullable=False)
    completed = Column(Boolean, nullable=False, default=False)
    result = Column(String(20), nullable=True)
    completion_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UserWeakPoint(Base):
    __tablename__ = "user_weak_points"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject = Column(String(50), nullable=False)
    knowledge_point = Column(String(100), nullable=False)
    weak_level = Column(Integer, nullable=False, default=1)
    mistake_count = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
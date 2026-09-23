from sqlalchemy import Column, Integer, Date, DateTime, ForeignKey
from sqlalchemy.sql import func
from ..core.database import Base

class UserStudyStat(Base):
    __tablename__ = "user_study_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    study_date = Column(Date, nullable=False)
    total_time = Column(Integer, nullable=False, default=0)
    words_studied = Column(Integer, nullable=False, default=0)
    mistakes_added = Column(Integer, nullable=False, default=0)
    questions_completed = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
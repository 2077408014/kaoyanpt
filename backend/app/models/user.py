from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from ..core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    avatar = Column(String(255), nullable=True)
    daily_word_count = Column(Integer, nullable=False, default=20, server_default="20")
    selected_word_category = Column(String(50), nullable=True)
    batch_size = Column(Integer, nullable=False, default=20, server_default="20")
    study_mode = Column(String(20), nullable=False, default="mixed", server_default="mixed")
    study_session_json = Column(Text, nullable=True)
    ai_api_key = Column(String(500), nullable=True)
    ai_api_base_url = Column(String(255), nullable=True)
    ai_api_model = Column(String(100), nullable=True)
    ai_api_provider = Column(String(50), nullable=True)
    active_ai_config_id = Column(Integer, ForeignKey("ai_configs.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from ..core.database import Base


class AIConfig(Base):
    """AI 配置表：每个用户可以保存多个 AI 配置，可在不同厂商间切换。"""

    __tablename__ = "ai_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(50), nullable=False, default="")
    provider = Column(String(50), nullable=False, default="custom")
    api_key = Column(String(500), nullable=False)
    base_url = Column(String(255), nullable=False)
    model = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
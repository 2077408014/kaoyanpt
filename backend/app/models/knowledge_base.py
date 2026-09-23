from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from ..core.database import Base
from datetime import datetime


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    filename = Column(String(255))
    file_type = Column(String(20))
    file_size = Column(Integer)
    storage_path = Column(String(500))
    subject = Column(String(50), default="未分类")
    chunk_count = Column(Integer, default=0)
    indexed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
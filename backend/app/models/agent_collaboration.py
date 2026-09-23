from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from ..core.database import Base


class AgentCollaborationLog(Base):
    __tablename__ = "agent_collaboration_logs"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(64), nullable=False, index=True)
    user_id = Column(Integer, nullable=False)
    orchestrator_name = Column(String(100), nullable=False)
    query = Column(Text, nullable=False)
    context = Column(JSON, nullable=True)
    total_time_ms = Column(Float, nullable=False)
    consulted_agent_count = Column(Integer, nullable=False, default=0)
    accepted_agent_count = Column(Integer, nullable=False, default=0)
    recommendation_count = Column(Integer, nullable=False, default=0)
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AgentInteractionLog(Base):
    __tablename__ = "agent_interaction_logs"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(64), nullable=False, index=True)
    agent_name = Column(String(100), nullable=False)
    agent_domain = Column(String(100), nullable=False)
    accepted = Column(Boolean, nullable=False, default=False)
    reasoning = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    response_time_ms = Column(Float, nullable=False)
    recommendation_count = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
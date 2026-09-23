from sqlalchemy.orm import Session
from ..models.agent_collaboration import AgentCollaborationLog, AgentInteractionLog


class AgentLogService:
    def log_collaboration(
        self,
        db: Session,
        request_id: str,
        user_id: int,
        orchestrator_name: str,
        query: str,
        context: dict = None,
        total_time_ms: float = 0.0,
        consulted_agent_count: int = 0,
        accepted_agent_count: int = 0,
        recommendation_count: int = 0,
        success: bool = True,
        error_message: str = None
    ):
        log = AgentCollaborationLog(
            request_id=request_id,
            user_id=user_id,
            orchestrator_name=orchestrator_name,
            query=query,
            context=context,
            total_time_ms=total_time_ms,
            consulted_agent_count=consulted_agent_count,
            accepted_agent_count=accepted_agent_count,
            recommendation_count=recommendation_count,
            success=success,
            error_message=error_message
        )
        db.add(log)
        db.commit()
        return log

    def log_interaction(
        self,
        db: Session,
        request_id: str,
        agent_name: str,
        agent_domain: str,
        accepted: bool = False,
        reasoning: str = None,
        confidence: float = None,
        response_time_ms: float = 0.0,
        recommendation_count: int = 0,
        error: str = None
    ):
        log = AgentInteractionLog(
            request_id=request_id,
            agent_name=agent_name,
            agent_domain=agent_domain,
            accepted=accepted,
            reasoning=reasoning,
            confidence=confidence,
            response_time_ms=response_time_ms,
            recommendation_count=recommendation_count,
            error=error
        )
        db.add(log)
        db.commit()
        return log

    def get_collaboration_logs(
        self,
        db: Session,
        user_id: int = None,
        limit: int = 20,
        offset: int = 0
    ):
        query = db.query(AgentCollaborationLog)
        if user_id:
            query = query.filter(AgentCollaborationLog.user_id == user_id)
        logs = query.order_by(AgentCollaborationLog.created_at.desc()).offset(offset).limit(limit).all()
        return [self._to_dict(log) for log in logs]

    def get_interaction_logs(
        self,
        db: Session,
        request_id: str = None,
        agent_name: str = None,
        limit: int = 50,
        offset: int = 0
    ):
        query = db.query(AgentInteractionLog)
        if request_id:
            query = query.filter(AgentInteractionLog.request_id == request_id)
        if agent_name:
            query = query.filter(AgentInteractionLog.agent_name == agent_name)
        logs = query.order_by(AgentInteractionLog.created_at.desc()).offset(offset).limit(limit).all()
        return [self._to_dict(log) for log in logs]

    def get_collaboration_stats(self, db: Session, user_id: int = None):
        query = db.query(AgentCollaborationLog)
        if user_id:
            query = query.filter(AgentCollaborationLog.user_id == user_id)

        total = query.count()
        success_count = query.filter(AgentCollaborationLog.success == True).count()

        avg_time = db.query(AgentCollaborationLog.total_time_ms).filter(
            AgentCollaborationLog.user_id == user_id if user_id else True
        ).all()
        avg_time_ms = sum(t[0] for t in avg_time) / len(avg_time) if avg_time else 0

        return {
            "total_collaborations": total,
            "success_rate": round(success_count / total * 100, 2) if total > 0 else 0,
            "avg_response_time_ms": round(avg_time_ms, 2)
        }

    def _to_dict(self, log) -> dict:
        if isinstance(log, AgentCollaborationLog):
            return {
                "id": log.id,
                "request_id": log.request_id,
                "user_id": log.user_id,
                "orchestrator_name": log.orchestrator_name,
                "query": log.query,
                "context": log.context,
                "total_time_ms": log.total_time_ms,
                "consulted_agent_count": log.consulted_agent_count,
                "accepted_agent_count": log.accepted_agent_count,
                "recommendation_count": log.recommendation_count,
                "success": log.success,
                "error_message": log.error_message,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
        elif isinstance(log, AgentInteractionLog):
            return {
                "id": log.id,
                "request_id": log.request_id,
                "agent_name": log.agent_name,
                "agent_domain": log.agent_domain,
                "accepted": log.accepted,
                "reasoning": log.reasoning,
                "confidence": log.confidence,
                "response_time_ms": log.response_time_ms,
                "recommendation_count": log.recommendation_count,
                "error": log.error,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
        return {}


agent_log_service = AgentLogService()
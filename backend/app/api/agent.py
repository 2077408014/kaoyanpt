from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from ..core.database import get_db
from ..services.feature_agent_service import feature_agent_service
from ..core.deps import get_current_user
from ..models.user import User

router = APIRouter(prefix="/api/agent", tags=["智能体"])


class AgentChatRequest(BaseModel):
    agent_name: str
    message: str
    subject: Optional[str] = None


@router.post("/chat")
def agent_chat(
    data: AgentChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    valid_agents = {'ai-qa', 'resource-qa', 'mistake-recognition', 'recommendation'}
    if data.agent_name not in valid_agents:
        raise HTTPException(status_code=400, detail=f"无效的智能体: {data.agent_name}，可选: {valid_agents}")

    try:
        result = feature_agent_service.chat(
            db=db,
            user_id=current_user.id,
            agent_name=data.agent_name,
            message=data.message,
            subject=data.subject
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
def agent_history(
    agent_name: str = Query('ai-qa'),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return feature_agent_service.get_history(db, current_user.id, agent_name, limit)


@router.delete("/history")
def agent_clear_history(
    agent_name: str = Query('ai-qa'),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    feature_agent_service.clear_history(db, current_user.id, agent_name)
    return {"message": "历史已清除"}
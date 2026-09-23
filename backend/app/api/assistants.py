from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..services.collaboration_engine import get_collaboration_engine
from ..core.deps import get_current_user
from typing import Dict, Any, List

router = APIRouter(prefix="/api/assistants", tags=["AI助手协作"])


def get_engine():
    engine = get_collaboration_engine()
    if not engine:
        raise HTTPException(status_code=500, detail="协作引擎未初始化")
    return engine


@router.get("/")
def list_assistants() -> List[Dict[str, Any]]:
    try:
        engine = get_engine()
        return engine.list_assistants()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/classify")
def classify_request(
    query: str = Query(..., description="用户请求内容"),
    current_user = Depends(get_current_user)
) -> Dict[str, Any]:
    try:
        engine = get_engine()
        classification = engine.classify_request(query)
        return {"query": query, **classification}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{assistant_code}")
def get_assistant_info(assistant_code: str) -> Dict[str, Any]:
    try:
        engine = get_engine()
        assistant = engine.get_assistant(assistant_code)
        if not assistant:
            raise HTTPException(status_code=404, detail="助手不存在")
        return assistant.get_info()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute")
def execute_task(
    task_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    try:
        engine = get_engine()
        task_type = task_data.get("task_type", "answer_question")
        request = task_data.get("request", {})
        
        result = engine.execute_task(db, current_user.id, task_type, request)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
def assistant_chat(
    chat_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    try:
        engine = get_engine()
        message = chat_data.get("message", "")
        
        classification = engine.classify_request(message)
        task_type = classification.get("task_type", "answer_question")
        
        request = {"message": message}
        if "keyword" in chat_data:
            request["keyword"] = chat_data["keyword"]
        if "topic" in chat_data:
            request["topic"] = chat_data["topic"]
        if "weak_tag" in chat_data:
            request["weak_tag"] = chat_data["weak_tag"]
        
        result = engine.execute_task(db, current_user.id, task_type, request)
        
        return {
            "message": message,
            "classification": classification,
            "task_type": task_type,
            "result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{assistant_code}/process")
def process_with_assistant(
    assistant_code: str,
    request_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    try:
        engine = get_engine()
        assistant = engine.get_assistant(assistant_code)
        if not assistant:
            raise HTTPException(status_code=404, detail="助手不存在")
        
        result = assistant.process(db, current_user.id, request_data)
        return {
            "assistant": assistant_code,
            "result": result.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{assistant_code}/collaborate")
def collaborate_with_assistant(
    assistant_code: str,
    message_data: Dict[str, Any],
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    try:
        engine = get_engine()
        assistant = engine.get_assistant(assistant_code)
        if not assistant:
            raise HTTPException(status_code=404, detail="助手不存在")
        
        from ..services.assistants import CollaborationMessage
        
        message = CollaborationMessage(
            sender_code=message_data.get("sender_code", "system"),
            message_type=message_data.get("message_type", "request"),
            content=message_data.get("content", {})
        )
        
        result = assistant.handle_collaboration(db, current_user.id, message)
        
        if result:
            return {
                "assistant": assistant_code,
                "collaboration_result": result.to_dict()
            }
        else:
            return {
                "assistant": assistant_code,
                "collaboration_result": None,
                "message": "该助手无法处理此协作请求"
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

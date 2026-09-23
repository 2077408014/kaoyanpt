from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session


class CollaborationMessage:
    def __init__(self, sender_code: str, message_type: str, content: Dict[str, Any]):
        self.sender_code = sender_code
        self.message_type = message_type
        self.content = content
        self.timestamp = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sender_code": self.sender_code,
            "message_type": self.message_type,
            "content": self.content,
            "timestamp": self.timestamp
        }


class AssistantResult:
    def __init__(self, success: bool, data: Dict[str, Any], message: str = "", suggestions: List[str] = None):
        self.success = success
        self.data = data
        self.message = message
        self.suggestions = suggestions or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "suggestions": self.suggestions
        }


class BaseAssistant(ABC):
    code: str = "base"
    name: str = "基础助手"
    description: str = "基础AI助手"
    domain: str = "general"
    capabilities: List[str] = []
    dependencies: List[str] = []
    priority: int = 10

    def __init__(self, ai_service):
        self.ai_service = ai_service
        self.config = {}

    @abstractmethod
    def process(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        pass

    def handle_collaboration(self, db: Session, user_id: int, message: CollaborationMessage) -> Optional[AssistantResult]:
        return None

    def send_message(self, receiver_code: str, message_type: str, content: Dict[str, Any]) -> CollaborationMessage:
        return CollaborationMessage(self.code, message_type, content)

    def can_handle(self, request_type: str) -> bool:
        return request_type in self.capabilities

    def get_info(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "domain": self.domain,
            "capabilities": self.capabilities,
            "dependencies": self.dependencies,
            "priority": self.priority
        }

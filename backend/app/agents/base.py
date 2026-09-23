import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime


@dataclass
class AgentRequest:
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_agent: str = ""
    target_agent: str = ""
    query: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AgentResponse:
    request_id: str = ""
    agent_name: str = ""
    agent_domain: str = ""
    accepted: bool = False
    reasoning: str = ""
    recommendations: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    response_time_ms: float = 0.0
    error: Optional[str] = None


class BaseAgent(ABC):
    def __init__(self, name: str, domain: str, keywords: List[str], system_prompt: str):
        self.name = name
        self.domain = domain
        self.keywords = keywords
        self.system_prompt = system_prompt
        self.enabled = True

    def can_handle(self, query: str, context: Dict[str, Any] = None) -> bool:
        if not self.enabled:
            return False

        query_lower = query.lower()
        for keyword in self.keywords:
            if keyword.lower() in query_lower:
                return True

        if context:
            context_str = str(context).lower()
            for keyword in self.keywords:
                if keyword.lower() in context_str:
                    return True

        return False

    @abstractmethod
    async def respond(self, request: AgentRequest) -> AgentResponse:
        pass

    def get_info(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "domain": self.domain,
            "keywords": self.keywords,
            "enabled": self.enabled
        }


class AgentRegistry:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agents: Dict[str, BaseAgent] = {}
            cls._instance._agent_by_domain: Dict[str, BaseAgent] = {}
        return cls._instance

    def register(self, agent: BaseAgent):
        self._agents[agent.name] = agent
        self._agent_by_domain[agent.domain] = agent

    def unregister(self, agent_name: str):
        if agent_name in self._agents:
            agent = self._agents.pop(agent_name)
            if agent.domain in self._agent_by_domain:
                del self._agent_by_domain[agent.domain]

    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        return self._agents.get(agent_name)

    def get_agent_by_domain(self, domain: str) -> Optional[BaseAgent]:
        return self._agent_by_domain.get(domain)

    def list_agents(self) -> List[Dict[str, Any]]:
        return [agent.get_info() for agent in self._agents.values()]

    def get_all_agents(self) -> List[BaseAgent]:
        return list(self._agents.values())

    def find_relevant_agents(self, query: str, context: Dict[str, Any] = None) -> List[BaseAgent]:
        relevant = []
        for agent in self._agents.values():
            if agent.can_handle(query, context):
                relevant.append(agent)
        return relevant

    def enable_agent(self, agent_name: str, enabled: bool):
        if agent_name in self._agents:
            self._agents[agent_name].enabled = enabled

    def is_agent_enabled(self, agent_name: str) -> bool:
        agent = self._agents.get(agent_name)
        if agent:
            return agent.enabled
        return True

    def is_empty(self) -> bool:
        return len(self._agents) == 0


agent_registry = AgentRegistry()
import asyncio
import time
from typing import List, Dict, Any
from .base import AgentRequest, AgentResponse, agent_registry


class RecommendationOrchestrator:
    def __init__(self):
        self.registry = agent_registry
        self.max_parallel_requests = 4
        self.timeout_per_agent = 5.0
        self.min_confidence_threshold = 0.3

    async def generate_recommendations(
        self,
        user_id: int,
        weak_points: List[Dict[str, Any]],
        count: int = 5
    ) -> Dict[str, Any]:
        start_time = time.time()

        query = self._build_query(weak_points)
        context = {
            "user_id": user_id,
            "weak_points": weak_points,
            "recommendation_count": count
        }

        request = AgentRequest(
            source_agent="recommendation_orchestrator",
            query=query,
            context=context
        )

        relevant_agents = self.registry.find_relevant_agents(query, context)

        if not relevant_agents:
            relevant_agents = self.registry.get_all_agents()

        responses = await self._consult_agents(request, relevant_agents)

        recommendations = self._fuse_recommendations(responses, count)

        total_time_ms = (time.time() - start_time) * 1000

        return {
            "recommendations": recommendations,
            "agent_responses": [self._response_to_dict(r) for r in responses],
            "total_time_ms": total_time_ms,
            "consulted_agents": len(relevant_agents),
            "accepted_agents": sum(1 for r in responses if r.accepted)
        }

    def _build_query(self, weak_points: List[Dict[str, Any]]) -> str:
        if not weak_points:
            return "请为考研复习生成推荐题目"

        weak_str = "\n".join(
            f"- {wp['subject']} - {wp['knowledge_point']}（薄弱等级：{wp['weak_level']}）"
            for wp in weak_points[:5]
        )

        return f"""根据以下用户薄弱知识点，生成针对性的考研复习推荐题目：

薄弱知识点：
{weak_str}

要求：
1. 针对每个薄弱知识点生成相关题目
2. 题目类型多样化（选择题、分析题等）
3. 难度适中
4. 包含问题、答案和详细分析
"""

    async def _consult_agents(
        self,
        request: AgentRequest,
        agents: List[Any]
    ) -> List[AgentResponse]:
        async def consult_agent(agent):
            request.target_agent = agent.name
            try:
                return await asyncio.wait_for(
                    agent.respond(request),
                    timeout=self.timeout_per_agent
                )
            except asyncio.TimeoutError:
                return AgentResponse(
                    request_id=request.request_id,
                    agent_name=agent.name,
                    agent_domain=agent.domain,
                    accepted=False,
                    reasoning="智能体响应超时",
                    error="timeout"
                )
            except Exception as e:
                return AgentResponse(
                    request_id=request.request_id,
                    agent_name=agent.name,
                    agent_domain=agent.domain,
                    accepted=False,
                    reasoning=str(e),
                    error=str(e)
                )

        tasks = [consult_agent(agent) for agent in agents]
        responses = await asyncio.gather(*tasks)

        return responses

    def _fuse_recommendations(
        self,
        responses: List[AgentResponse],
        count: int
    ) -> List[Dict[str, Any]]:
        all_recommendations = []

        for response in responses:
            if not response.accepted or response.confidence < self.min_confidence_threshold:
                continue

            for rec in response.recommendations:
                all_recommendations.append({
                    **rec,
                    "agent_name": response.agent_name,
                    "agent_domain": response.agent_domain,
                    "confidence": response.confidence,
                    "response_time_ms": response.response_time_ms
                })

        if not all_recommendations:
            return []

        all_recommendations.sort(
            key=lambda x: (x.get("confidence", 0), x.get("response_time_ms", float('inf'))),
            reverse=True
        )

        seen_questions = set()
        final_recommendations = []

        for rec in all_recommendations:
            if len(final_recommendations) >= count:
                break

            question_hash = rec["question_text"][:100]
            if question_hash in seen_questions:
                continue

            seen_questions.add(question_hash)
            final_recommendations.append(rec)

        return final_recommendations[:count]

    def _response_to_dict(self, response: AgentResponse) -> Dict[str, Any]:
        return {
            "agent_name": response.agent_name,
            "agent_domain": response.agent_domain,
            "accepted": response.accepted,
            "reasoning": response.reasoning,
            "confidence": response.confidence,
            "response_time_ms": response.response_time_ms,
            "recommendation_count": len(response.recommendations),
            "error": response.error
        }

    def get_agent_status(self) -> List[Dict[str, Any]]:
        return self.registry.list_agents()

    def toggle_agent(self, agent_name: str, enabled: bool):
        self.registry.enable_agent(agent_name, enabled)


recommendation_orchestrator = RecommendationOrchestrator()
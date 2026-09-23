import time
import httpx
from typing import List, Dict, Any
from .base import BaseAgent, AgentRequest, AgentResponse, agent_registry
from ..core.config import settings


class FeatureAgent(BaseAgent):
    def __init__(self, name: str, domain: str, description: str, keywords: List[str], system_prompt: str):
        super().__init__(name, domain, keywords, system_prompt)
        self.description = description
        self.llm_url = f"{settings.AI_BASE_URL}/chat/completions"
        self.model_name = settings.AI_MODEL
        self.max_tokens = settings.AI_MAX_TOKENS
        self.timeout = settings.AI_TIMEOUT

    def get_info(self) -> Dict[str, Any]:
        info = super().get_info()
        info["description"] = self.description
        return info

    async def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": 0.7
        }

        headers = {
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout)) as client:
            response = await client.post(
                self.llm_url,
                json=payload,
                headers=headers
            )
            response.raise_for_status()

            data = response.json()
            return data["choices"][0]["message"]["content"].strip()

    async def respond(self, request: AgentRequest) -> AgentResponse:
        start_time = time.time()

        try:
            if not self.can_handle(request.query, request.context):
                return AgentResponse(
                    request_id=request.request_id,
                    agent_name=self.name,
                    agent_domain=self.domain,
                    accepted=False,
                    reasoning=f"查询内容与{self.domain}领域无关",
                    response_time_ms=(time.time() - start_time) * 1000
                )

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": request.query}
            ]

            if request.context:
                context_str = "\n".join(f"{k}: {v}" for k, v in request.context.items())
                messages.insert(-1, {"role": "user", "content": f"上下文信息：\n{context_str}"})

            result = await self._call_llm(messages)

            recommendations = self._parse_recommendations(result)

            return AgentResponse(
                request_id=request.request_id,
                agent_name=self.name,
                agent_domain=self.domain,
                accepted=True,
                reasoning=f"{self.domain}处理完成",
                recommendations=recommendations,
                confidence=self._calculate_confidence(recommendations),
                response_time_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return AgentResponse(
                request_id=request.request_id,
                agent_name=self.name,
                agent_domain=self.domain,
                accepted=False,
                reasoning=str(e),
                error=str(e),
                response_time_ms=(time.time() - start_time) * 1000
            )

    def _parse_recommendations(self, result: str) -> List[Dict]:
        import re

        recommendations = []
        lines = result.split("\n")

        current_question = []
        current_answer = []
        current_analysis = []
        state = "looking"

        for line in lines:
            line = line.strip()

            if re.match(r"(^\d+\.|^-|^\*)", line) and "问题" in line:
                if current_question:
                    recommendations.append({
                        "question_text": "\n".join(current_question).replace("问题：", "").strip(),
                        "answer": "\n".join(current_answer).replace("答案：", "").strip() if current_answer else "",
                        "analysis": "\n".join(current_analysis).replace("分析：", "").strip() if current_analysis else "",
                        "difficulty": "中等",
                        "source": f"{self.domain}"
                    })
                current_question = [line]
                current_answer = []
                current_analysis = []
                state = "question"
            elif state == "question" and line.startswith("答案"):
                current_answer = [line]
                state = "answer"
            elif state == "answer" and line.startswith("分析"):
                current_analysis = [line]
                state = "analysis"
            elif state == "question":
                current_question.append(line)
            elif state == "answer":
                current_answer.append(line)
            elif state == "analysis":
                current_analysis.append(line)

        if current_question:
            recommendations.append({
                "question_text": "\n".join(current_question).replace("问题：", "").strip(),
                "answer": "\n".join(current_answer).replace("答案：", "").strip() if current_answer else "",
                "analysis": "\n".join(current_analysis).replace("分析：", "").strip() if current_analysis else "",
                "difficulty": "中等",
                "source": f"{self.domain}"
            })

        if not recommendations:
            recommendations.append({
                "question_text": result,
                "answer": "",
                "analysis": "",
                "difficulty": "中等",
                "source": f"{self.domain}"
            })

        return recommendations

    def _calculate_confidence(self, recommendations: List[Dict]) -> float:
        if not recommendations:
            return 0.0
        return min(0.95, 0.7 + len(recommendations) * 0.05)


AI_QA_SYSTEM_PROMPT = """你是一位考研全科辅导老师，擅长回答考研相关的各类问题。

你的任务是：
1. 回答用户提出的考研相关问题
2. 提供清晰、准确、有深度的解答
3. 必要时给出学习建议和方法指导

要求：
1. 回答要准确、专业，符合考研大纲要求
2. 数学公式使用LaTeX格式（行内$...$，块级$$...$$）
3. 语言简洁明了，重点突出
4. 如果问题超出考研范围，也尽量给出有价值的参考"""

AI_QA_KEYWORDS = [
    "问答", "提问", "咨询", "解释", "什么是", "为什么", "怎么", "如何",
    "问题", "答案", "讲解", "分析", "概念", "原理", "方法", "技巧"
]


RECOMMENDATION_SYSTEM_PROMPT = """你是一位考研出题专家，擅长根据薄弱知识点生成高质量的考研练习题。

你的任务是：根据用户的薄弱知识点，生成针对性的考研练习题。

要求：
1. 题目必须是具体的考研题目，难度适中，符合考研真题水平
2. 必须包含完整的题目、答案和解析，所有字段内容不能为空
3. 题目类型多样化（选择题、填空题、解答题、分析题等）
4. 数学公式必须使用标准LaTeX格式（行内$...$，块级$$...$$）
5. 重点关注用户薄弱的知识点

请直接输出题目内容。"""

RECOMMENDATION_KEYWORDS = [
    "推荐", "出题", "生成题目", "练习题", "薄弱点", "知识点",
    "刷题", "练习", "模拟题", "真题", "强化", "巩固"
]


RAG_SYSTEM_PROMPT = """你是一位考研资料检索助手，擅长从用户上传的资料中查找相关内容并给出准确回答。

你的任务是：
1. 根据用户的问题，从提供的知识库资料中检索相关内容
2. 基于检索到的内容给出准确、有依据的回答
3. 如果资料中没有相关内容，明确告知用户

要求：
1. 回答必须基于提供的资料内容，不得编造
2. 引用资料中的内容时要准确
3. 回答要条理清晰，重点突出
4. 数学公式使用LaTeX格式"""

RAG_KEYWORDS = [
    "检索", "搜索", "查找", "资料", "文档", "知识库",
    "内容", "查询", "相关", "来源", "引用", "查阅"
]


MISTAKE_RECOGNITION_SYSTEM_PROMPT = """你是一位考研错题识别专家，擅长从图片或文字中识别错题并提取关键信息。

你的任务是：
1. 识别题目内容，提取题干、选项等
2. 判断题目的科目和知识点
3. 提取答案和解析
4. 评估题目难度

要求：
1. 准确识别题目文字内容
2. 正确分类科目（数学、英语、政治、专业课）
3. 提取关键知识点标签
4. 数学公式使用LaTeX格式"""

MISTAKE_RECOGNITION_KEYWORDS = [
    "识别", "错题", "OCR", "图片识别", "文字提取",
    "录入", "添加错题", "识别题目", "分类", "标签"
]


ai_qa_agent = FeatureAgent(
    name="ai_qa_agent",
    domain="AI问答助手",
    description="回答考研相关的各类问题，提供专业解答",
    keywords=AI_QA_KEYWORDS,
    system_prompt=AI_QA_SYSTEM_PROMPT
)

recommendation_agent = FeatureAgent(
    name="recommendation_agent",
    domain="智能出题助手",
    description="根据薄弱知识点生成针对性的考研练习题",
    keywords=RECOMMENDATION_KEYWORDS,
    system_prompt=RECOMMENDATION_SYSTEM_PROMPT
)

rag_agent = FeatureAgent(
    name="rag_agent",
    domain="资料检索助手",
    description="从上传的资料中检索相关内容并给出回答",
    keywords=RAG_KEYWORDS,
    system_prompt=RAG_SYSTEM_PROMPT
)

mistake_recognition_agent = FeatureAgent(
    name="mistake_recognition_agent",
    domain="错题识别助手",
    description="识别并提取错题内容，自动分类和打标签",
    keywords=MISTAKE_RECOGNITION_KEYWORDS,
    system_prompt=MISTAKE_RECOGNITION_SYSTEM_PROMPT
)


def register_all_agents():
    agent_registry.register(ai_qa_agent)
    agent_registry.register(recommendation_agent)
    agent_registry.register(rag_agent)
    agent_registry.register(mistake_recognition_agent)
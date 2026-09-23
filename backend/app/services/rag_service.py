from ..core.config import settings
from ..services.knowledge_base_service import knowledge_base_service
from ..utils.latex_utils import normalize_latex
from .llm_service import llm_service


SYSTEM_PROMPT_STRICT = """你是一个专业的考研复习助手。你只能严格根据提供的知识库内容回答用户问题。

知识库内容：
{context}

用户问题：{question}

严格回答规则：
1. 你必须并且只能基于上面知识库中的内容回答，绝对不能使用知识库以外的任何知识
2. 如果知识库内容不足以回答问题，必须明确说"知识库中的相关内容不足以回答此问题"
3. 禁止编造任何知识库中没有的信息
4. 回答要简洁明了，使用markdown格式
5. 在回答末尾标注来源文档名称
6. **数学公式必须使用标准LaTeX格式**：
   - 所有数学符号、公式、变量、函数都必须用LaTeX格式表示
   - 行内公式用$...$包裹，独立公式用$$...$$包裹
   - 极限：使用 $\\lim_{x \\to a} f(x)$ 格式
   - 分数：使用 $\\frac{分子}{分母}$ 格式
   - 指数：使用 $e^{指数}$ 格式
   - 三角函数：使用 \\sin, \\cos, \\tan 等
   - 对数：使用 \\ln, \\log 格式
   - 导数：使用 $f'(x)$ 格式
   - 积分：使用 $\\int$ 格式
   - 求和：使用 $\\sum$ 格式
   - 希腊字母：使用 \\alpha, \\beta, \\gamma, \\pi 等
7. 输出示例（极限题）：求极限 $\\lim_{x \\to 0} \\frac{\\sin x}{x}$ 的值，答案是1。
8. 输出示例（导数题）：函数 $f(x) = x^2$ 的导数是 $f'(x) = 2x$。
"""

SYSTEM_PROMPT = """你是一个专业的考研复习助手。请根据以下提供的知识库内容回答用户的问题。

知识库内容：
{context}

用户问题：{question}

回答要求：
1. 必须基于知识库内容回答，不得编造信息
2. 如果知识库中没有相关内容，请明确说明"该问题超出知识库范围"
3. 如果知识库内容不足，请结合你的知识补充，但要注明"补充信息"
4. 回答要简洁明了，使用markdown格式
5. 在回答末尾标注来源文档名称
6. **数学公式必须使用标准LaTeX格式**：
   - 所有数学符号、公式、变量、函数都必须用LaTeX格式表示
   - 行内公式用$...$包裹，独立公式用$$...$$包裹
   - 极限：使用 $\\lim_{x \\to a} f(x)$ 格式
   - 分数：使用 $\\frac{分子}{分母}$ 格式
   - 指数：使用 $e^{指数}$ 格式
   - 三角函数：使用 \\sin, \\cos, \\tan 等
   - 对数：使用 \\ln, \\log 格式
   - 导数：使用 $f'(x)$ 格式
   - 积分：使用 $\\int$ 格式
   - 求和：使用 $\\sum$ 格式
   - 希腊字母：使用 \\alpha, \\beta, \\gamma, \\pi 等
7. 输出示例（极限题）：求极限 $\\lim_{x \\to 0} \\frac{\\sin x}{x}$ 的值，答案是1。
8. 输出示例（导数题）：函数 $f(x) = x^2$ 的导数是 $f'(x) = 2x$。
"""


class RAGService:
    def __init__(self):
        self.max_tokens = settings.AI_MAX_TOKENS
        self.timeout = settings.AI_TIMEOUT

    def chat(self, user_id: int, question: str, top_k: int = 3, threshold: float = 0.3, ai_config: dict = None, subject: str = None, only_knowledge_base: bool = False) -> dict:
        from ..agents.base import agent_registry

        # 检查资料检索智能体是否启用
        if not agent_registry.is_agent_enabled('rag_agent'):
            return {
                "answer": "资料检索功能已被停用。请前往首页，在「智能体状态」中开启「资料检索助手」。",
                "source": None,
                "relevant_chunks": [],
                "from_knowledge_base": False
            }

        effective_threshold = 0.05 if only_knowledge_base else threshold
        relevant_chunks = knowledge_base_service.search(user_id, question, top_k, effective_threshold, subject=subject, enable_keyword_fallback=True)

        from_knowledge_base = len(relevant_chunks) > 0

        if not relevant_chunks:
            if only_knowledge_base:
                return {
                    "answer": "未从您的资料中找到相关内容，请尝试其他关键词或上传更多资料。",
                    "source": None,
                    "relevant_chunks": [],
                    "from_knowledge_base": False
                }
            answer = self._call_llm(question, "", ai_config)
            return {
                "answer": answer,
                "source": None,
                "relevant_chunks": [],
                "from_knowledge_base": False
            }

        if only_knowledge_base:
            max_similarity = max(chunk.get("similarity", 0) for chunk in relevant_chunks)
            if max_similarity < 0.15:
                return {
                    "answer": "从您的资料中检索到的内容相关性较低，建议尝试更精确的关键词或上传更多相关资料。",
                    "source": None,
                    "relevant_chunks": relevant_chunks,
                    "from_knowledge_base": False
                }

        context = ""
        sources = set()

        for chunk in relevant_chunks:
            context += f"【来源：{chunk['metadata'].get('filename', '未知文档')}】\n"
            context += f"{chunk['content']}\n\n"
            sources.add(chunk['metadata'].get('filename', '未知文档'))

        answer = normalize_latex(self._call_llm(question, context, ai_config, strict_mode=only_knowledge_base))

        return {
            "answer": answer,
            "source": ", ".join(sources),
            "relevant_chunks": relevant_chunks,
            "from_knowledge_base": from_knowledge_base
        }

    def search_only(self, user_id: int, question: str, top_k: int = 3, threshold: float = 0.3, subject: str = None) -> dict:
        relevant_chunks = knowledge_base_service.search(user_id, question, top_k, threshold, subject=subject)
        return {"results": relevant_chunks}

    def _call_llm(self, question: str, context: str, ai_config: dict = None, strict_mode: bool = False) -> str:
        if context:
            prompt_template = SYSTEM_PROMPT_STRICT if strict_mode else SYSTEM_PROMPT
            prompt = prompt_template.replace('{context}', context).replace('{question}', question)
            system_prompt = "你是一个专业的考研复习助手，仅基于知识库内容回答用户问题。" if strict_mode else "你是一个专业的考研复习助手，基于知识库内容回答用户问题。"
        else:
            prompt = f"请回答以下考研相关问题：\n\n{question}\n\n如果这个问题超出你的知识范围，请明确说明。"
            system_prompt = "你是一个专业的考研复习助手，精通考研各科目知识。"

        if not ai_config or not ai_config.get("api_key"):
            raise ValueError("未配置AI服务，请先在AI配置页面设置API Key")

        return llm_service.chat_single_turn(
            user_message=prompt,
            ai_config=ai_config,
            system_prompt=system_prompt,
            temperature=0.3 if strict_mode else 0.7,
        )


rag_service = RAGService()
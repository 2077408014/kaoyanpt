import json
from sqlalchemy.orm import Session
from typing import List, Dict, Optional

from ..models.ai_chat import AIChatHistory
from ..services.rag_service import rag_service
from ..services.llm_service import llm_service
from ..utils.latex_utils import normalize_latex
from ..agents.specialized import register_all_agents

register_all_agents()


AGENT_PROMPTS = {
    'ai-qa': """你是一个专业的考研复习助手。你可以回答用户关于考研复习的任何问题。

规则：
1. 根据你的知识回答考研相关问题
2. 如果问题与考研无关，礼貌地说明你专注于考研复习领域
3. 使用markdown格式回答
4. **数学公式必须使用标准LaTeX格式**，行内公式用$...$包裹，独立公式用$$...$$包裹
""",

    'resource-qa': """你是一个专业的考研知识库助手。请根据以下知识库内容回答用户的问题。

知识库内容：
{context}

回答要求：
1. 必须基于知识库内容回答，不得编造信息
2. 如果知识库中没有相关内容，请明确说"该问题超出知识库范围"
3. 结合你的知识对检索到的内容进行组织、概括和解释
4. 回答要简洁明了，用清晰的语言表述
5. 在回答末尾标注来源文档名称
""",

    'mistake-recognition': """你是一个考研错题分析助手，分析OCR识别出的题目内容。

请分析以下题目，输出结构化的结果。

要求：
1. 用自然语言组织输出，不要输出JSON格式
2. 先给出题目完整描述
3. 然后给出正确答案
4. 然后给出详细的解析过程
5. 最后标注：科目、知识点、难度和错误类型
""",

    'recommendation': """你是一位考研出题专家，根据用户薄弱知识点生成同类练习题。

要求：
1. 针对提供的知识点生成3-5道练习题
2. 题目类型包括选择题、填空题、解答题等
3. 每道题都给出正确答案和详细解析
4. 难度循序渐进
5. **数学公式必须使用标准LaTeX格式**
"""
}


class FeatureAgentService:
    def chat(
        self,
        db: Session,
        user_id: int,
        agent_name: str,
        message: str,
        user_config: dict = None,
        subject: str = None,
        context: str = None,
    ) -> dict:
        if agent_name == 'resource-qa':
            return self._resource_qa_chat(db, user_id, message, user_config, subject)

        return self._agent_chat(db, user_id, agent_name, message, user_config)

    def _get_user_config(self, db: Session, user_id: int) -> dict:
        from ..models.user import User
        from ..models.ai_config import AIConfig

        user = db.query(User).filter(User.id == user_id).first()
        if user and user.active_ai_config_id:
            config = db.query(AIConfig).filter(
                AIConfig.id == user.active_ai_config_id,
                AIConfig.user_id == user_id
            ).first()
            if config:
                return {
                    "name": config.name or config.model or "AI",
                    "api_key": config.api_key,
                    "base_url": config.base_url or "https://api.deepseek.com/v1",
                    "model": config.model or "deepseek-chat",
                    "active": True
                }

        # 未激活任何 ai_configs 配置，但已有旧版单个 AI 配置时回退
        if user and user.ai_api_key:
            return {
                "name": user.ai_api_model or "AI",
                "api_key": user.ai_api_key,
                "base_url": user.ai_api_base_url or "https://api.deepseek.com/v1",
                "model": user.ai_api_model or "deepseek-chat",
                "active": True
            }

        return {
            "name": "未启用",
            "api_key": "",
            "base_url": "",
            "model": "",
            "active": False
        }

    def _get_history(self, db: Session, user_id: int, agent_name: str, limit: int = 10) -> list:
        msgs = db.query(AIChatHistory).filter(
            AIChatHistory.user_id == user_id,
            AIChatHistory.agent_name == agent_name
        ).order_by(AIChatHistory.created_at.desc()).limit(limit).all()
        return reversed(msgs)

    def _save(self, db: Session, user_id: int, agent_name: str, msg_type: str, content: str, source: str = None, chunks: list = None):
        msg = AIChatHistory(
            user_id=user_id,
            agent_name=agent_name,
            message_type=msg_type,
            content=content,
            source=source,
            relevant_chunks=json.dumps(chunks, ensure_ascii=False) if chunks else None
        )
        db.add(msg)
        db.commit()

    def _agent_chat(self, db: Session, user_id: int, agent_name: str, message: str, user_config: dict = None) -> dict:
        if user_config is None:
            user_config = self._get_user_config(db, user_id)

        self._save(db, user_id, agent_name, 'question', message)

        ai_name = user_config.get("name", "AI")

        # 未激活 AI 配置时，直接返回提示
        if not user_config.get("active") or not user_config.get("api_key"):
            answer = "您尚未启用任何 AI 配置。请前往「AI 配置」页面，添加一个配置并点击「使用」按钮启用。"
            self._save(db, user_id, agent_name, 'answer', answer, '未配置')
            return {"answer": answer, "source": "未配置", "suggestions": []}

        # 检查对应智能体是否启用
        from ..agents.base import agent_registry
        agent_map = {
            'ai-qa': 'ai_qa_agent',
            'mistake-recognition': 'mistake_recognition_agent',
        }
        target_agent = agent_map.get(agent_name)
        if target_agent and not agent_registry.is_agent_enabled(target_agent):
            agent_names = {
                'ai-qa': 'AI问答助手',
                'mistake-recognition': '错题识别助手',
            }
            agent_display = agent_names.get(agent_name, '对应')
            answer = f"{agent_display}功能已被停用。请前往首页，在「智能体状态」中开启「{agent_display}」。"
            self._save(db, user_id, agent_name, 'answer', answer, '已停用')
            return {"answer": answer, "source": "已停用", "suggestions": []}

        system_prompt = AGENT_PROMPTS.get(agent_name, AGENT_PROMPTS['ai-qa'])
        history = list(self._get_history(db, user_id, agent_name))
        history_messages = []
        for msg in history:
            if msg.id:
                role = "user" if msg.message_type == "question" else "assistant"
                history_messages.append({"role": role, "content": msg.content})

        try:
            answer = llm_service.chat_with_history(
                user_message=message,
                history=history_messages,
                ai_config=user_config,
                system_prompt=system_prompt,
                temperature=0.7,
            )
            answer = normalize_latex(answer)
            self._save(db, user_id, agent_name, 'answer', answer, ai_name)
            return {"answer": answer, "source": ai_name, "suggestions": []}
        except Exception as e:
            answer = f"AI 服务调用失败：{e}"
            self._save(db, user_id, agent_name, 'answer', answer, '调用失败')
            return {"answer": answer, "source": "调用失败", "suggestions": []}

    def _resource_qa_chat(self, db: Session, user_id: int, message: str, user_config: dict = None, subject: str = None) -> dict:
        if user_config is None:
            user_config = self._get_user_config(db, user_id)

        self._save(db, user_id, 'resource-qa', 'question', message)

        try:
            rag_result = rag_service.chat(
                user_id=user_id,
                question=message,
                ai_config=user_config,
                subject=subject,
                only_knowledge_base=True
            )

            from_kb = rag_result.get("from_knowledge_base", False)
            answer = normalize_latex(rag_result.get("answer", "未检索到相关内容。"))
            source = rag_result.get("source") or ("知识库" if from_kb else "AI")
            chunks = rag_result.get("relevant_chunks", [])
            for chunk in chunks:
                if isinstance(chunk, dict) and chunk.get("content"):
                    chunk["content"] = normalize_latex(chunk["content"])

            self._save(db, user_id, 'resource-qa', 'answer', answer, source, chunks)
            return {
                "answer": answer,
                "source": source,
                "from_knowledge_base": from_kb,
                "relevant_chunks": chunks,
                "suggestions": []
            }
        except Exception as e:
            answer = f"知识库检索失败：{e}"
            self._save(db, user_id, 'resource-qa', 'answer', answer, 'error')
            return {"answer": answer, "source": None, "from_knowledge_base": False, "relevant_chunks": [], "suggestions": []}

    def get_history(self, db: Session, user_id: int, agent_name: str, limit: int = 50) -> list:
        msgs = db.query(AIChatHistory).filter(
            AIChatHistory.user_id == user_id,
            AIChatHistory.agent_name == agent_name
        ).order_by(AIChatHistory.created_at.asc()).limit(limit).all()
        return [{
            "id": m.id,
            "user_id": m.user_id,
            "agent_name": m.agent_name,
            "message_type": m.message_type,
            "content": m.content,
            "source": m.source,
            "relevant_chunks": json.loads(m.relevant_chunks) if m.relevant_chunks else [],
            "created_at": m.created_at.isoformat() if m.created_at else None
        } for m in msgs]

    def clear_history(self, db: Session, user_id: int, agent_name: str):
        db.query(AIChatHistory).filter(
            AIChatHistory.user_id == user_id,
            AIChatHistory.agent_name == agent_name
        ).delete()
        db.commit()


feature_agent_service = FeatureAgentService()
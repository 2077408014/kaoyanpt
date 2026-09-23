from sqlalchemy.orm import Session
from datetime import datetime
from ..models.ai_chat import AIChatHistory
import requests
import random

from ..core.config import settings

AI_RESPONSES = {
    "default": [
        "好的，我来帮您解答！",
        "这个问题很有意思，让我为您分析一下。",
        "考研复习是一个系统性的工程，需要合理规划。",
        "坚持就是胜利，加油！"
    ],
    "考研英语": [
        "考研英语分为英语一和英语二，英语一难度较高。",
        "阅读理解是得分重点，建议每天练习2-3篇。",
        "写作需要积累模板和素材，每周至少练习1篇。",
        "词汇是基础，建议使用艾宾浩斯记忆法进行复习。",
        "完形填空考察综合能力，建议放在最后做。",
        "翻译题要注意中英文表达差异，确保语句通顺。"
    ],
    "考研政治": [
        "政治分为马原、毛中特、史纲、思修、时政五个部分。",
        "马原重在理解，毛中特重在记忆。",
        "建议暑期开始系统复习，10月份开始刷题。",
        "肖秀荣系列是考研政治的经典资料。",
        "时政部分要关注当年的重大事件。",
        "分析题需要掌握答题模板和关键词。"
    ],
    "考研数学": [
        "数学分为数一、数二、数三，难度依次递减。",
        "高数占比最高，是复习的重点。",
        "建议从基础开始，打好知识点基础。",
        "刷题是关键，建议完成至少两遍真题。",
        "错题要反复研究，总结解题方法。",
        "线代和概率虽然分值少，但不能忽视。",
        "极限是高数的基础，重要极限：$$\\lim_{x \\to 0} \\frac{\\sin x}{x} = 1$$",
        "导数定义：$$f'(x) = \\lim_{\\Delta x \\to 0} \\frac{f(x+\\Delta x) - f(x)}{\\Delta x}$$",
        "牛顿-莱布尼茨公式：$$\\int_a^b f(x)dx = F(b) - F(a)$$，其中 $F'(x) = f(x)$",
        "泰勒展开：$$f(x) = \\sum_{n=0}^{\\infty} \\frac{f^{(n)}(a)}{n!}(x-a)^n$$",
        "多元函数偏导数：$$\\frac{\\partial f}{\\partial x} = \\lim_{\\Delta x \\to 0} \\frac{f(x+\\Delta x, y) - f(x, y)}{\\Delta x}$$",
        "高斯公式（散度定理）：$$\\iiint_V \\text{div}\\vec{F} dV = \\iint_{\\partial V} \\vec{F} \\cdot d\\vec{S}$$"
    ],
    "专业课": [
        "专业课要以目标院校的参考书为主。",
        "历年真题是最重要的复习资料。",
        "建议联系学长学姐获取复习经验。",
        "笔记整理很重要，便于后期复习。",
        "关注目标院校的招生政策和考试大纲变化。"
    ],
    "复习规划": [
        "建议制定详细的复习计划，按月、周、日安排。",
        "暑期是黄金复习期，要充分利用。",
        "9-10月份是强化阶段，重点刷题。",
        "11-12月份是冲刺阶段，模拟考试很重要。",
        "注意劳逸结合，保持良好的心态。",
        "定期总结复习进度，及时调整计划。"
    ],
    "心态调整": [
        "考研是一场持久战，保持积极心态很重要。",
        "遇到困难时可以适当放松，不要给自己太大压力。",
        "找研友一起学习，互相鼓励。",
        "相信自己的努力一定会有回报。",
        "适当的运动有助于缓解压力。"
    ]
}


SYSTEM_PROMPT = """你是一个专业的考研复习助手，精通考研英语、政治、数学、专业课等各科目知识。

你的任务是：
1. 回答用户关于考研复习的各类问题
2. 提供专业的学习建议和备考策略
3. 解释考研相关的概念和知识点
4. 根据用户需求提供个性化的复习指导

格式要求：
- 使用markdown格式增强可读性（列表、加粗、标题等）
- **数学公式必须使用LaTeX格式**，行内公式用 $...$ 包裹，独立公式用 $$...$$ 包裹
- 常用数学符号示例：
  - 极限：$\lim_{x \to a} f(x)$ 或 $$\lim_{x \to a} f(x)$$
  - 导数：$f'(x)$ 或 $\frac{df}{dx}$
  - 积分：$\int_a^b f(x)dx$
  - 分数：$\frac{numerator}{denominator}$
  - 求和：$\sum_{i=1}^n a_i$
  - 希腊字母：$\alpha, \beta, \gamma, \pi, \theta$
  - 三角函数：$\sin x, \cos x, \tan x$
  - 对数：$\ln x, \log x$
  - 指数：$e^x, a^b$

如果用户的问题不属于考研相关内容，你可以礼貌地说明你专注于考研复习领域。

你的回答应该帮助用户更好地备考，提供有价值的信息。
"""


class AIService:
    def __init__(self):
        self.default_api_key = settings.AI_API_KEY
        self.default_base_url = settings.AI_BASE_URL
        self.default_model = settings.AI_MODEL
        self.max_tokens = int(settings.AI_MAX_TOKENS)
        self.timeout = int(settings.AI_TIMEOUT)
    
    def _get_user_ai_config(self, db: Session, user_id: int) -> dict:
        from ..models.user import User
        from ..models.ai_config import AIConfig
        user = db.query(User).filter(User.id == user_id).first()

        # 优先使用 ai_configs 表中激活的配置（与参考后端语义一致）
        if user and user.active_ai_config_id:
            config = db.query(AIConfig).filter(
                AIConfig.id == user.active_ai_config_id,
                AIConfig.user_id == user_id
            ).first()
            if config:
                return {
                    "mode": "api",
                    "api_key": config.api_key,
                    "base_url": config.base_url or self.default_base_url,
                    "model": config.model or self.default_model,
                    "name": config.name or config.model or "AI",
                    "active": True
                }

        if user and user.ai_api_provider == 'local':
            return {
                "mode": "local",
                "api_key": "",
                "base_url": settings.LOCAL_LLM_BASE_URL,
                "model": "local-llm",
                "name": "本地模型",
                "active": True
            }
        
        if user and user.ai_api_key:
            return {
                "mode": "api",
                "api_key": user.ai_api_key,
                "base_url": user.ai_api_base_url or self.default_base_url,
                "model": user.ai_api_model or self.default_model,
                "name": user.ai_api_model or "AI",
                "active": True
            }
        
        return {
            "mode": "api",
            "api_key": self.default_api_key,
            "base_url": self.default_base_url,
            "model": self.default_model,
            "name": self.default_model or "AI",
            "active": bool(self.default_api_key)
        }
    
    def check_local_llm_status(self) -> str:
        try:
            response = requests.get(f"{settings.LOCAL_LLM_BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get("status", "unknown")
            return "stopped"
        except Exception:
            return "stopped"

    def chat(self, db: Session, user_id: int, message: str) -> dict:
        category = self._classify_message(message)
        
        message_lower = message.lower()
        command_actions = {
            "错题": ("正在打开错题管理模块...", "command"),
            "单词": ("正在启动单词背诵模式...", "command"),
            "推荐": ("正在为您推荐相关题目...", "command"),
            "薄弱": ("正在分析您的薄弱知识点...", "command"),
            "计划": ("正在为您生成个性化复习计划...", "command"),
            "报告": ("正在生成学习报告...", "command"),
        }
        
        answer = ""
        source = category
        
        for keyword, (response, src) in command_actions.items():
            if keyword in message_lower:
                answer = response
                source = src
                break
        
        if not answer:
            user_config = self._get_user_ai_config(db, user_id)
            
            if user_config["mode"] == "local":
                try:
                    answer = self._call_local_model(message)
                    source = "本地AI"
                except Exception as e:
                    print(f"Local LLM call failed: {e}")
                    responses = AI_RESPONSES.get(category, AI_RESPONSES["default"])
                    answer = responses[random.randint(0, len(responses) - 1)]
            elif user_config["api_key"]:
                try:
                    answer = self._call_ai_model(db, user_id, message, user_config)
                    source = "AI"
                except Exception as e:
                    print(f"AI API call failed: {e}")
                    responses = AI_RESPONSES.get(category, AI_RESPONSES["default"])
                    answer = responses[random.randint(0, len(responses) - 1)]
            else:
                responses = AI_RESPONSES.get(category, AI_RESPONSES["default"])
                answer = responses[random.randint(0, len(responses) - 1)]
            
            if category == "考研数学" and "$$" not in answer:
                math_responses = [r for r in AI_RESPONSES["考研数学"] if "$$" in r]
                if math_responses:
                    answer = math_responses[random.randint(0, len(math_responses) - 1)]
        
        self._save_message(db, user_id, "question", message)
        self._save_message(db, user_id, "answer", answer, source)
        
        return {
            "answer": answer,
            "category": category,
            "suggestions": []
        }
    
    def command(self, db: Session, user_id: int, command: str) -> dict:
        self._save_message(db, user_id, "question", command)
        
        command_lower = command.lower()
        result = {"action": "unknown", "message": "无法识别的指令"}
        
        if any(keyword in command_lower for keyword in ["错题", "错误", "mistake"]):
            result = {
                "action": "open_mistakes",
                "message": "正在打开错题管理模块..."
            }
        elif any(keyword in command_lower for keyword in ["单词", "背诵", "recitation"]):
            result = {
                "action": "start_recitation",
                "message": "正在启动单词背诵模式..."
            }
        elif any(keyword in command_lower for keyword in ["推荐", "题目"]):
            result = {
                "action": "generate_recommendation",
                "message": "正在为您推荐相关题目..."
            }
        elif any(keyword in command_lower for keyword in ["薄弱", "分析", "知识点"]):
            result = {
                "action": "analyze_weak_points",
                "message": "正在分析您的薄弱知识点..."
            }
        elif any(keyword in command_lower for keyword in ["计划", "安排", "规划"]):
            result = {
                "action": "generate_plan",
                "message": "正在为您生成个性化复习计划..."
            }
        elif any(keyword in command_lower for keyword in ["统计", "报告", "进度"]):
            result = {
                "action": "generate_report",
                "message": "正在生成学习报告..."
            }
        
        self._save_message(db, user_id, "answer", result["message"], "command")
        
        return result
    
    def get_history(self, db: Session, user_id: int, limit: int = 20) -> list:
        messages = db.query(AIChatHistory).filter(
            AIChatHistory.user_id == user_id
        ).order_by(AIChatHistory.created_at.desc()).limit(limit).all()
        
        return [self._to_dict(msg) for msg in reversed(messages)]
    
    def clear_history(self, db: Session, user_id: int) -> bool:
        db.query(AIChatHistory).filter(AIChatHistory.user_id == user_id).delete()
        db.commit()
        return True
    
    def _call_local_model(self, message: str) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": message}
        ]
        
        payload = {
            "model": "local-llm",
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": 0.7
        }
        
        url = f"{settings.LOCAL_LLM_BASE_URL}/v1/chat/completions"
        
        response = requests.post(url, json=payload, timeout=self.timeout)
        response.raise_for_status()
        
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    
    def _call_ai_model(self, db: Session, user_id: int, message: str, config: dict = None) -> str:
        if config is None:
            config = self._get_user_ai_config(db, user_id)
        
        history = self._get_conversation_history(db, user_id)
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        
        for msg in history:
            role = "user" if msg["message_type"] == "question" else "assistant"
            messages.append({"role": role, "content": msg["content"]})
        
        messages.append({"role": "user", "content": message})
        
        payload = {
            "model": config["model"],
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": 0.7
        }
        
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json"
        }
        
        url = f"{config['base_url']}/chat/completions"
        
        response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    
    def _get_conversation_history(self, db: Session, user_id: int, limit: int = 10) -> list:
        messages = db.query(AIChatHistory).filter(
            AIChatHistory.user_id == user_id
        ).order_by(AIChatHistory.created_at.desc()).limit(limit).all()
        
        return [self._to_dict(msg) for msg in reversed(messages)]
    
    def _classify_message(self, message: str) -> str:
        message_lower = message.lower()
        
        if any(keyword in message_lower for keyword in ["英语", "阅读", "写作", "翻译", "完形", "词汇"]):
            return "考研英语"
        if any(keyword in message_lower for keyword in ["政治", "马原", "毛中特", "史纲", "思修", "时政"]):
            return "考研政治"
        if any(keyword in message_lower for keyword in ["数学", "高数", "线代", "概率", "微积分", "极限", "导数", "积分", "泰勒", "偏导", "微分", "方程"]):
            return "考研数学"
        if any(keyword in message_lower for keyword in ["专业", "专业课"]):
            return "专业课"
        if any(keyword in message_lower for keyword in ["计划", "安排", "规划", "时间"]):
            return "复习规划"
        if any(keyword in message_lower for keyword in ["心态", "压力", "焦虑", "放松"]):
            return "心态调整"
        
        return "default"
    
    def _save_message(self, db: Session, user_id: int, message_type: str, content: str, source: str = None):
        message = AIChatHistory(
            user_id=user_id,
            message_type=message_type,
            content=content,
            source=source
        )
        db.add(message)
        db.commit()
    
    def _to_dict(self, msg: AIChatHistory) -> dict:
        return {
            "id": msg.id,
            "user_id": msg.user_id,
            "message_type": msg.message_type,
            "content": msg.content,
            "source": msg.source,
            "created_at": msg.created_at.isoformat() if msg.created_at else None
        }


ai_service = AIService()
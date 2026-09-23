from typing import Dict, Any, List
from sqlalchemy.orm import Session
from .base_assistant import BaseAssistant, AssistantResult, CollaborationMessage
import random


class KnowledgeQAAssistant(BaseAssistant):
    code: str = "knowledge_qa"
    name: str = "知识问答助手"
    description: str = "解答考研各科目的知识点问题，提供详细的解析和建议"
    domain: str = "qa"
    capabilities: List[str] = ["answer_question", "explain_concept", "solve_problem", "provide_advice"]
    dependencies: List[str] = ["mistake_analyzer", "learning_recommender"]
    priority: int = 5

    SUBJECT_RESPONSES = {
        "考研英语": [
            "考研英语分为英语一和英语二，英语一难度较高。",
            "阅读理解是得分重点，建议每天练习2-3篇。",
            "写作需要积累模板和素材，每周至少练习1篇。",
            "词汇是基础，建议使用艾宾浩斯记忆法进行复习。",
            "完形填空考察综合能力，建议放在最后做。",
            "翻译题要注意中英文表达差异，确保语句通顺。",
            "新题型需要掌握不同题型的解题技巧。",
            "真题是最好的复习资料，建议至少做两遍。"
        ],
        "考研政治": [
            "政治分为马原、毛中特、史纲、思修、时政五个部分。",
            "马原重在理解，毛中特重在记忆。",
            "建议暑期开始系统复习，10月份开始刷题。",
            "肖秀荣系列是考研政治的经典资料。",
            "时政部分要关注当年的重大事件。",
            "分析题需要掌握答题模板和关键词。",
            "选择题要多刷题，总结常见错误。",
            "冲刺阶段要重点背诵分析题考点。"
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
            "牛顿-莱布尼茨公式：$$\\int_a^b f(x)dx = F(b) - F(a)$$",
            "泰勒展开：$$f(x) = \\sum_{n=0}^{\\infty} \\frac{f^{(n)}(a)}{n!}(x-a)^n$$"
        ],
        "专业课": [
            "专业课要以目标院校的参考书为主。",
            "历年真题是最重要的复习资料。",
            "建议联系学长学姐获取复习经验。",
            "笔记整理很重要，便于后期复习。",
            "关注目标院校的招生政策和考试大纲变化。",
            "专业课复习要注重系统性和逻辑性。",
            "可以参加目标院校的专业课辅导班。",
            "模拟考试有助于熟悉考试流程和时间安排。"
        ],
        "复习规划": [
            "建议制定详细的复习计划，按月、周、日安排。",
            "暑期是黄金复习期，要充分利用。",
            "9-10月份是强化阶段，重点刷题。",
            "11-12月份是冲刺阶段，模拟考试很重要。",
            "注意劳逸结合，保持良好的心态。",
            "定期总结复习进度，及时调整计划。",
            "每天保证6-8小时的有效学习时间。",
            "找到适合自己的学习方法和节奏。"
        ],
        "心态调整": [
            "考研是一场持久战，保持积极心态很重要。",
            "遇到困难时可以适当放松，不要给自己太大压力。",
            "找研友一起学习，互相鼓励。",
            "相信自己的努力一定会有回报。",
            "适当的运动有助于缓解压力。",
            "保持规律的作息，保证充足的睡眠。",
            "不要和别人攀比进度，专注于自己。",
            "学会自我调节，保持良好的心理状态。"
        ]
    }

    def get_system_prompt(self) -> str:
        return """你是一个专业的考研复习助手，精通考研英语、政治、数学、专业课等各科目知识。

你的任务是：
1. 回答用户关于考研复习的各类问题
2. 提供专业的学习建议和备考策略
3. 解释考研相关的概念和知识点
4. 根据用户需求提供个性化的复习指导

格式要求：
- 使用markdown格式增强可读性（列表、加粗、标题等）
- 数学公式必须使用LaTeX格式，行内公式用 $...$ 包裹，独立公式用 $$...$$ 包裹
- 常用数学符号示例：
  - 极限：$\lim_{x \to a} f(x)$
  - 导数：$f'(x)$ 或 $\frac{df}{dx}$
  - 积分：$\int_a^b f(x)dx$
  - 分数：$\frac{numerator}{denominator}$
  - 求和：$\sum_{i=1}^n a_i$

如果用户的问题不属于考研相关内容，你可以礼貌地说明你专注于考研复习领域。

你的回答应该帮助用户更好地备考，提供有价值的信息。
"""

    def process(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        request_type = request.get("type", "answer_question")
        message = request.get("message", "")
        
        if request_type == "answer_question":
            return self._answer_question(db, user_id, message)
        elif request_type == "explain_concept":
            return self._explain_concept(db, user_id, request)
        elif request_type == "solve_problem":
            return self._solve_problem(db, user_id, request)
        elif request_type == "provide_advice":
            return self._provide_advice(db, user_id, request)
        
        return AssistantResult(False, {}, "未知的请求类型")

    def _answer_question(self, db: Session, user_id: int, message: str) -> AssistantResult:
        category = self._classify_message(message)
        responses = self.SUBJECT_RESPONSES.get(category, self.SUBJECT_RESPONSES["考研英语"])
        
        answer = responses[random.randint(0, len(responses) - 1)]
        
        return AssistantResult(
            True,
            {
                "answer": answer,
                "category": category,
                "related_topics": self._get_related_topics(category)
            },
            "问题解答完成"
        )

    def _explain_concept(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        concept = request.get("concept", "")
        subject = request.get("subject", "")
        
        explanation = {
            "concept": concept,
            "subject": subject,
            "definition": f"这是{subject}中的一个重要概念，需要深入理解。",
            "key_points": [
                f"{concept}的核心定义",
                f"{concept}的主要特点",
                f"{concept}与相关概念的区别",
                f"{concept}在考试中的应用"
            ],
            "examples": [f"举例说明{concept}的应用场景"]
        }
        
        return AssistantResult(
            True,
            {"explanation": explanation},
            "概念解释完成"
        )

    def _solve_problem(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        problem = request.get("problem", "")
        subject = request.get("subject", "")
        
        solution = {
            "problem": problem[:100] + "..." if len(problem) > 100 else problem,
            "subject": subject,
            "analysis": "分析题目涉及的知识点和解题思路",
            "steps": [
                "第一步：理解题目要求",
                "第二步：回忆相关知识点",
                "第三步：推导解题过程",
                "第四步：验证答案正确性"
            ],
            "tips": ["注意审题，理解题意", "检查计算过程", "注意单位和符号"]
        }
        
        return AssistantResult(
            True,
            {"solution": solution},
            "解题指导完成"
        )

    def _provide_advice(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        area = request.get("area", "")
        
        advices = {
            "time_management": [
                "制定详细的每日学习计划",
                "合理分配各科目的学习时间",
                "利用碎片时间进行复习",
                "保证充足的休息时间"
            ],
            "stress_management": [
                "适当运动，放松身心",
                "与家人朋友交流",
                "保持积极乐观的心态",
                "学会自我调节"
            ],
            "study_methods": [
                "做好笔记，便于复习",
                "多做真题，熟悉考试",
                "定期总结，查漏补缺",
                "找到适合自己的学习方法"
            ]
        }
        
        selected_advices = advices.get(area, advices["study_methods"])
        
        return AssistantResult(
            True,
            {"advice": selected_advices, "area": area},
            "建议已提供"
        )

    def _classify_message(self, message: str) -> str:
        message_lower = message.lower()
        
        if any(keyword in message_lower for keyword in ["英语", "阅读", "写作", "翻译", "完形", "词汇"]):
            return "考研英语"
        if any(keyword in message_lower for keyword in ["政治", "马原", "毛中特", "史纲", "思修", "时政"]):
            return "考研政治"
        if any(keyword in message_lower for keyword in ["数学", "高数", "线代", "概率", "微积分", "极限", "导数", "积分"]):
            return "考研数学"
        if any(keyword in message_lower for keyword in ["专业", "专业课"]):
            return "专业课"
        if any(keyword in message_lower for keyword in ["计划", "安排", "规划", "时间"]):
            return "复习规划"
        if any(keyword in message_lower for keyword in ["心态", "压力", "焦虑", "放松"]):
            return "心态调整"
        
        return "考研英语"

    def _get_related_topics(self, category: str) -> List[str]:
        topic_map = {
            "考研英语": ["阅读理解技巧", "写作模板", "词汇记忆方法", "翻译技巧"],
            "考研政治": ["马原哲学原理", "毛中特重要会议", "史纲时间线", "时政热点"],
            "考研数学": ["高等数学", "线性代数", "概率统计", "真题解析"],
            "专业课": ["专业核心课程", "历年真题", "学术论文", "复习笔记"],
            "复习规划": ["时间管理", "学习方法", "心态调整", "模拟考试"],
            "心态调整": ["压力管理", "时间管理", "学习方法", "生活平衡"]
        }
        return topic_map.get(category, [])

    def handle_collaboration(self, db: Session, user_id: int, message: CollaborationMessage) -> AssistantResult:
        if message.message_type == "request_answer":
            result = self._answer_question(db, user_id, message.content.get("message", ""))
            return AssistantResult(
                True,
                {"answer": result.data.get("answer", ""), "source": self.code},
                "问题解答已完成"
            )
        elif message.message_type == "request_concept_explanation":
            result = self._explain_concept(db, user_id, message.content)
            return AssistantResult(
                True,
                {"explanation": result.data.get("explanation", {}), "source": self.code},
                "概念解释已完成"
            )
        return None

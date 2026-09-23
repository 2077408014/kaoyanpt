from typing import Dict, Any, List
from sqlalchemy.orm import Session

from .base_assistant import BaseAssistant, AssistantResult, CollaborationMessage


class MistakeAnalyzerAssistant(BaseAssistant):
    code: str = "mistake_analyzer"
    name: str = "错题分析助手"
    description: str = "专门分析错题，识别薄弱知识点，提供针对性练习建议"
    domain: str = "mistakes"
    capabilities: List[str] = ["analyze_mistake", "identify_weak_points", "generate_practice", "suggest_review"]
    dependencies: List[str] = ["study_analyzer", "learning_recommender"]
    priority: int = 8

    def get_system_prompt(self) -> str:
        return """你是一位专业的考研错题分析助手，精通考研各科目的知识点和题型。

你的任务是：
1. 分析用户的错题记录，识别错误原因和薄弱知识点
2. 针对薄弱点提供专项练习建议
3. 生成个性化的复习计划，帮助用户巩固知识点
4. 提供相似题型的解题思路和技巧

分析报告要求：
- 使用markdown格式，清晰列出分析结果
- 标注错误类型（概念理解错误、计算错误、审题错误等）
- 提供具体的改进建议
- 推荐相关的练习题和复习资源
"""

    def process(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        request_type = request.get("type", "analyze_mistake")

        if request_type == "analyze_mistake":
            return self._analyze_mistake(db, user_id, request)
        elif request_type == "identify_weak_points":
            return self._identify_weak_points(db, user_id, request)
        elif request_type == "generate_practice":
            return self._generate_practice(db, user_id, request)
        elif request_type == "suggest_review":
            return self._suggest_review(db, user_id, request)

        return AssistantResult(False, {}, "未知的请求类型")

    def _analyze_mistake(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        mistake_id = request.get("mistake_id")
        subject = request.get("subject", "")

        if mistake_id:
            from ...models.mistake import Mistake

            mistake = db.query(Mistake).filter(Mistake.id == mistake_id, Mistake.user_id == user_id).first()
            if mistake:
                analysis = self._generate_analysis(mistake)
                return AssistantResult(True, {"analysis": analysis, "mistake_id": mistake.id}, "错题分析完成")

        analysis = self._analyze_mistakes_by_subject(db, user_id, subject)
        return AssistantResult(True, {"analysis": analysis}, "错题分析完成")

    def _identify_weak_points(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        from ...models.mistake import Mistake

        mistakes = db.query(Mistake).filter(Mistake.user_id == user_id).all()

        weak_points = {}
        for mistake in mistakes:
            tag = mistake.knowledge_point or "未分类"
            weak_points[tag] = weak_points.get(tag, 0) + 1

        sorted_points = sorted(weak_points.items(), key=lambda x: x[1], reverse=True)

        return AssistantResult(
            True,
            {"weak_points": [{"tag": tag, "count": count} for tag, count in sorted_points], "total": len(mistakes)},
            "薄弱知识点分析完成",
        )

    def _generate_practice(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        weak_tag = request.get("weak_tag", "薄弱知识点")

        return AssistantResult(
            True,
            {
                "weak_tag": weak_tag,
                "practice_suggestions": [
                    {"type": "专项练习", "target": f"{weak_tag}相关题目", "quantity": 10},
                    {"type": "概念复习", "target": f"{weak_tag}核心概念", "resources": ["教材", "笔记"]},
                    {"type": "错题重做", "target": f"{weak_tag}相关错题", "method": "间隔重复"},
                    {"type": "模拟测试", "target": f"{weak_tag}综合测试", "frequency": "每周1次"},
                ],
            },
            "练习计划生成完成",
        )

    def _suggest_review(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        from datetime import datetime, timedelta

        from ...models.mistake import Mistake

        recent_mistakes = db.query(Mistake).filter(
            Mistake.user_id == user_id,
            Mistake.created_at >= datetime.now() - timedelta(days=7),
        ).all()

        review_plan = {
            "urgent": [],
            "normal": [],
            "delayed": [],
        }

        for mistake in recent_mistakes:
            review_item = {
                "id": mistake.id,
                "question": mistake.question_text[:50] + "..." if mistake.question_text and len(mistake.question_text) > 50 else (mistake.question_text or ""),
                "knowledge_point": mistake.knowledge_point,
                "subject": mistake.subject,
            }

            wrong_count = mistake.review_count - mistake.correct_count
            if wrong_count >= 3:
                review_plan["urgent"].append(review_item)
            elif wrong_count == 2:
                review_plan["normal"].append(review_item)
            elif not mistake.review_count:
                review_plan["urgent"].append(review_item)
            else:
                review_plan["delayed"].append(review_item)

        return AssistantResult(
            True,
            {"review_plan": review_plan, "total": len(recent_mistakes)},
            "复习建议生成完成",
        )

    def _generate_analysis(self, mistake) -> Dict[str, Any]:
        question = mistake.question_text or ""
        return {
            "question_summary": question[:100] + "..." if len(question) > 100 else question,
            "review_count": mistake.review_count,
            "correct_count": mistake.correct_count,
            "error_type": self._classify_error_type(mistake),
            "knowledge_point": mistake.knowledge_point,
            "analysis": self._get_error_analysis(mistake),
            "improvement_suggestions": self._get_improvement_suggestions(mistake),
        }

    def _analyze_mistakes_by_subject(self, db: Session, user_id: int, subject: str) -> Dict[str, Any]:
        from ...models.mistake import Mistake

        query = db.query(Mistake).filter(Mistake.user_id == user_id)
        if subject:
            query = query.filter(Mistake.subject == subject)

        mistakes = query.all()

        analysis = {
            "total_mistakes": len(mistakes),
            "subject": subject or "全部科目",
            "error_distribution": {},
            "weakest_topics": [],
        }

        for mistake in mistakes:
            error_type = self._classify_error_type(mistake)
            analysis["error_distribution"][error_type] = analysis["error_distribution"].get(error_type, 0) + 1

        return analysis

    def _classify_error_type(self, mistake) -> str:
        if mistake.error_type:
            return mistake.error_type
        if "公式" in (mistake.knowledge_point or ""):
            return "计算错误"
        return "概念理解错误"

    def _get_error_analysis(self, mistake) -> str:
        error_type = self._classify_error_type(mistake)
        point = mistake.knowledge_point or "相关知识点"
        if error_type == "计算错误":
            return f"您在{point}相关的计算上出现了错误，建议加强公式记忆和计算练习。"
        elif error_type == "概念理解错误":
            return f"您对{point}的概念理解存在偏差，建议重新复习相关知识点。"
        return f"本题考查{point}知识点，建议对照解析回顾解题思路。"

    def _get_improvement_suggestions(self, mistake) -> List[str]:
        point = mistake.knowledge_point or "该知识点"
        return [
            f"重新学习{point}相关章节",
            "查找类似题目进行专项练习",
            "制作知识点卡片加深记忆",
            "定期回顾错题，强化印象",
        ]

    def handle_collaboration(self, db: Session, user_id: int, message: CollaborationMessage) -> AssistantResult:
        if message.message_type == "request_weak_points":
            result = self._identify_weak_points(db, user_id, {})
            return AssistantResult(
                True,
                {"weak_points": result.data.get("weak_points", []), "source": self.code},
                "薄弱点数据已发送",
            )
        elif message.message_type == "request_mistake_analysis":
            result = self._analyze_mistake(db, user_id, message.content)
            return AssistantResult(
                True,
                {"analysis": result.data.get("analysis", {}), "source": self.code},
                "错题分析已完成",
            )
        return None
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from .base_assistant import BaseAssistant, AssistantResult, CollaborationMessage


class LearningRecommenderAssistant(BaseAssistant):
    code: str = "learning_recommender"
    name: str = "学习推荐助手"
    description: str = "基于学习数据和薄弱点，智能推荐学习内容和练习题目"
    domain: str = "recommendation"
    capabilities: List[str] = ["recommend_topics", "suggest_exercises", "plan_study", "match_resources"]
    dependencies: List[str] = ["mistake_analyzer", "study_analyzer"]
    priority: int = 7

    def get_system_prompt(self) -> str:
        return """你是一位专业的考研学习推荐助手，能够根据用户的学习情况和薄弱点智能推荐学习内容。

你的任务是：
1. 分析用户的学习数据和错题记录
2. 识别需要重点复习的知识点
3. 推荐适合当前水平的练习题和学习资源
4. 制定个性化的学习计划

推荐原则：
- 优先推荐薄弱知识点相关内容
- 根据用户的学习进度调整推荐难度
- 推荐内容要具体、可执行
- 兼顾知识点覆盖和专项突破
"""

    def process(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        request_type = request.get("type", "recommend_topics")
        
        if request_type == "recommend_topics":
            return self._recommend_topics(db, user_id, request)
        elif request_type == "suggest_exercises":
            return self._suggest_exercises(db, user_id, request)
        elif request_type == "plan_study":
            return self._plan_study(db, user_id, request)
        elif request_type == "match_resources":
            return self._match_resources(db, user_id, request)
        
        return AssistantResult(False, {}, "未知的请求类型")

    def _recommend_topics(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        from ...models.mistake import Mistake
        from ...models.study_stat import UserStudyStat as StudyStat
        
        mistakes = db.query(Mistake).filter(Mistake.user_id == user_id).all()
        stats = db.query(StudyStat).filter(StudyStat.user_id == user_id).all()
        
        tag_count = {}
        for mistake in mistakes:
            tag = mistake.knowledge_point or "未分类"
            tag_count[tag] = tag_count.get(tag, 0) + 1
        
        sorted_tags = sorted(tag_count.items(), key=lambda x: x[1], reverse=True)
        
        recommendations = []
        for tag, count in sorted_tags[:5]:
            recommendations.append({
                "topic": tag,
                "priority": "高" if count >= 3 else "中",
                "suggested_hours": count * 2,
                "reason": f"该知识点错误{count}次，需要重点复习"
            })
        
        return AssistantResult(
            True,
            {"recommendations": recommendations, "total_topics": len(sorted_tags)},
            "知识点推荐完成"
        )

    def _suggest_exercises(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        topic = request.get("topic")
        difficulty = request.get("difficulty", "medium")
        
        exercises = [
            {
                "type": "基础练习",
                "topic": topic,
                "difficulty": "easy",
                "quantity": 5,
                "purpose": "巩固基础概念"
            },
            {
                "type": "进阶练习",
                "topic": topic,
                "difficulty": "medium",
                "quantity": 8,
                "purpose": "提升解题能力"
            },
            {
                "type": "真题演练",
                "topic": topic,
                "difficulty": "hard",
                "quantity": 3,
                "purpose": "熟悉考试风格"
            }
        ]
        
        return AssistantResult(
            True,
            {"exercises": exercises, "topic": topic, "difficulty": difficulty},
            "练习题推荐完成"
        )

    def _plan_study(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        duration = request.get("duration", 7)
        focus_area = request.get("focus_area", "")
        
        plan = {
            "duration": duration,
            "focus_area": focus_area,
            "daily_plan": []
        }
        
        subjects = ["英语", "政治", "数学"] if not focus_area else [focus_area]
        
        for day in range(1, duration + 1):
            day_plan = {
                "day": day,
                "morning": [],
                "afternoon": [],
                "evening": []
            }
            
            for subject in subjects:
                day_plan["morning"].append(f"{subject}基础知识点复习")
                day_plan["afternoon"].append(f"{subject}专项练习题")
                day_plan["evening"].append(f"{subject}错题回顾")
            
            plan["daily_plan"].append(day_plan)
        
        return AssistantResult(
            True,
            {"plan": plan},
            f"{duration}天学习计划已生成"
        )

    def _match_resources(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        topic = request.get("topic")
        
        resources = [
            {
                "type": "教材",
                "name": f"{topic}核心考点解析",
                "priority": "high"
            },
            {
                "type": "视频",
                "name": f"{topic}名师讲解视频",
                "priority": "medium"
            },
            {
                "type": "题库",
                "name": f"{topic}专项练习题集",
                "priority": "high"
            },
            {
                "type": "笔记",
                "name": f"{topic}思维导图笔记",
                "priority": "medium"
            }
        ]
        
        return AssistantResult(
            True,
            {"resources": resources, "topic": topic},
            "学习资源匹配完成"
        )

    def handle_collaboration(self, db: Session, user_id: int, message: CollaborationMessage) -> AssistantResult:
        if message.message_type == "request_recommendations":
            result = self._recommend_topics(db, user_id, {})
            return AssistantResult(
                True,
                {"recommendations": result.data.get("recommendations", []), "source": self.code},
                "推荐数据已发送"
            )
        elif message.message_type == "request_exercises":
            result = self._suggest_exercises(db, user_id, message.content)
            return AssistantResult(
                True,
                {"exercises": result.data.get("exercises", []), "source": self.code},
                "练习题推荐已完成"
            )
        return None

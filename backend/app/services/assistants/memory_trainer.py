from typing import Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from .base_assistant import BaseAssistant, AssistantResult, CollaborationMessage


class MemoryTrainerAssistant(BaseAssistant):
    code: str = "memory_trainer"
    name: str = "记忆训练助手"
    description: str = "基于艾宾浩斯遗忘曲线，安排单词和知识点的背诵计划"
    domain: str = "recitation"
    capabilities: List[str] = ["schedule_recitation", "generate_word_list", "track_progress", "adjust_plan"]
    dependencies: List[str] = ["study_analyzer"]
    priority: int = 8

    def get_system_prompt(self) -> str:
        return """你是一位专业的考研记忆训练助手，精通艾宾浩斯遗忘曲线记忆法。

你的任务是：
1. 根据艾宾浩斯遗忘曲线安排背诵计划
2. 生成个性化的单词和知识点背诵列表
3. 跟踪用户的背诵进度
4. 根据遗忘情况调整复习计划

记忆原则：
- 遵循艾宾浩斯遗忘曲线规律
- 及时复习，强化记忆
- 合理安排每日背诵量
- 根据用户进度动态调整
"""

    def process(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        request_type = request.get("type", "schedule_recitation")
        
        if request_type == "schedule_recitation":
            return self._schedule_recitation(db, user_id, request)
        elif request_type == "generate_word_list":
            return self._generate_word_list(db, user_id, request)
        elif request_type == "track_progress":
            return self._track_progress(db, user_id, request)
        elif request_type == "adjust_plan":
            return self._adjust_plan(db, user_id, request)
        
        return AssistantResult(False, {}, "未知的请求类型")

    def _schedule_recitation(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        daily_count = request.get("daily_count", 50)
        mode = request.get("mode", "words")
        
        schedule = {
            "mode": mode,
            "daily_count": daily_count,
            "plan": []
        }
        
        intervals = [1, 2, 4, 7, 15, 30]
        
        for day in range(1, 8):
            day_plan = {
                "day": day,
                "new_items": daily_count,
                "review_items": [],
                "total": daily_count
            }
            
            for i, interval in enumerate(intervals):
                if day - interval >= 1:
                    day_plan["review_items"].append(f"第{day - interval}天学习的内容")
                    day_plan["total"] += daily_count
            
            schedule["plan"].append(day_plan)
        
        return AssistantResult(
            True,
            {"schedule": schedule},
            "背诵计划已生成"
        )

    def _generate_word_list(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        from ...models.word import Word
        
        count = request.get("count", 20)
        difficulty = request.get("difficulty", "all")
        
        query = db.query(Word).filter(Word.user_id == user_id)
        
        if difficulty == "easy":
            query = query.filter(Word.familiarity >= 80)
        elif difficulty == "medium":
            query = query.filter(Word.familiarity.between(40, 80))
        elif difficulty == "hard":
            query = query.filter(Word.familiarity < 40)
        
        words = query.limit(count).all()
        
        return AssistantResult(
            True,
            {
                "words": [word.to_dict() for word in words],
                "count": len(words),
                "difficulty": difficulty
            },
            f"已生成{len(words)}个单词"
        )

    def _track_progress(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        from ...models.word import Word
        
        words = db.query(Word).filter(Word.user_id == user_id).all()
        
        if not words:
            return AssistantResult(
                True,
                {"progress": {"total": 0, "learned": 0, "familiar": 0, "unfamiliar": 0}},
                "暂无单词数据"
            )
        
        learned = sum(1 for w in words if w.familiarity >= 80)
        familiar = sum(1 for w in words if 40 <= w.familiarity < 80)
        unfamiliar = sum(1 for w in words if w.familiarity < 40)
        
        progress = {
            "total": len(words),
            "learned": learned,
            "familiar": familiar,
            "unfamiliar": unfamiliar,
            "percentage": round(learned / len(words) * 100, 1) if words else 0,
            "suggestion": self._get_progress_suggestion(learned, len(words))
        }
        
        return AssistantResult(
            True,
            {"progress": progress},
            "进度跟踪完成"
        )

    def _adjust_plan(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        from ...models.word import Word
        
        words = db.query(Word).filter(Word.user_id == user_id).all()
        
        if not words:
            return AssistantResult(
                True,
                {"adjustment": {"message": "暂无单词数据，建议先添加单词"}},
                "无需调整"
            )
        
        unfamiliar_count = sum(1 for w in words if w.familiarity < 40)
        
        adjustment = {
            "current_daily_count": 50,
            "suggested_daily_count": min(50 + unfamiliar_count // 5, 100),
            "focus_areas": [],
            "actions": []
        }
        
        if unfamiliar_count > 30:
            adjustment["actions"].append("减少新单词学习量，增加复习时间")
            adjustment["actions"].append("重点复习陌生单词")
            adjustment["actions"].append("使用碎片时间进行快速复习")
        elif unfamiliar_count > 10:
            adjustment["actions"].append("保持当前学习节奏")
            adjustment["actions"].append("适当增加复习频率")
        else:
            adjustment["actions"].append("可以适当增加新单词学习量")
        
        return AssistantResult(
            True,
            {"adjustment": adjustment},
            "计划调整建议已生成"
        )

    def _get_progress_suggestion(self, learned: int, total: int) -> str:
        if total == 0:
            return "请开始添加单词"
        percentage = learned / total * 100
        
        if percentage >= 80:
            return "学习进度良好！可以适当增加每日学习量"
        elif percentage >= 50:
            return "继续保持，坚持就是胜利！"
        elif percentage >= 20:
            return "加油！建议增加学习时间和频率"
        else:
            return "起步阶段很重要，建议每天坚持学习"

    def handle_collaboration(self, db: Session, user_id: int, message: CollaborationMessage) -> AssistantResult:
        if message.message_type == "request_recitation_plan":
            result = self._schedule_recitation(db, user_id, message.content)
            return AssistantResult(
                True,
                {"schedule": result.data.get("schedule", {}), "source": self.code},
                "背诵计划已发送"
            )
        elif message.message_type == "request_progress":
            result = self._track_progress(db, user_id, {})
            return AssistantResult(
                True,
                {"progress": result.data.get("progress", {}), "source": self.code},
                "进度数据已发送"
            )
        return None

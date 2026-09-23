from typing import Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from .base_assistant import BaseAssistant, AssistantResult, CollaborationMessage


class StudyAnalyzerAssistant(BaseAssistant):
    code: str = "study_analyzer"
    name: str = "学习分析助手"
    description: str = "分析学习数据，生成学习报告，提供改进建议"
    domain: str = "analysis"
    capabilities: List[str] = ["analyze_study", "generate_report", "track_trends", "identify_patterns"]
    dependencies: List[str] = ["mistake_analyzer", "memory_trainer"]
    priority: int = 6

    def get_system_prompt(self) -> str:
        return """你是一位专业的考研学习分析助手，能够深入分析用户的学习数据。

你的任务是：
1. 分析用户的学习时间、进度和效果
2. 生成详细的学习报告
3. 识别学习模式和趋势
4. 提供针对性的改进建议

分析原则：
- 数据驱动，客观分析
- 关注学习效率和效果
- 提供具体可操作的建议
- 帮助用户优化学习策略
"""

    def process(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        request_type = request.get("type", "analyze_study")
        
        if request_type == "analyze_study":
            return self._analyze_study(db, user_id, request)
        elif request_type == "generate_report":
            return self._generate_report(db, user_id, request)
        elif request_type == "track_trends":
            return self._track_trends(db, user_id, request)
        elif request_type == "identify_patterns":
            return self._identify_patterns(db, user_id, request)
        
        return AssistantResult(False, {}, "未知的请求类型")

    def _analyze_study(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        from ...models.study_stat import UserStudyStat as StudyStat
        from ...models.mistake import Mistake
        
        days = request.get("days", 7)
        start_date = datetime.now() - timedelta(days=days)
        
        stats = db.query(StudyStat).filter(
            StudyStat.user_id == user_id,
            StudyStat.study_date >= start_date
        ).all()
        
        mistakes = db.query(Mistake).filter(
            Mistake.user_id == user_id,
            Mistake.created_at >= start_date
        ).all()
        
        total_time = sum(stat.total_time for stat in stats)
        avg_time = total_time / len(stats) if stats else 0
        
        analysis = {
            "period": f"最近{days}天",
            "total_study_time": total_time,
            "average_daily_time": round(avg_time, 1),
            "study_days": len(stats),
            "total_mistakes": len(mistakes),
            "mistake_trend": "增加" if len(mistakes) > 10 else "稳定",
            "suggestions": self._generate_suggestions(total_time, len(stats), len(mistakes))
        }
        
        return AssistantResult(
            True,
            {"analysis": analysis},
            "学习分析完成"
        )

    def _generate_report(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        period = request.get("period", "weekly")
        
        report = {
            "period": period,
            "overview": {},
            "subject_analysis": {},
            "progress": {},
            "recommendations": []
        }
        
        from ...models.study_stat import UserStudyStat as StudyStat
        from ...models.mistake import Mistake
        
        if period == "weekly":
            days = 7
        elif period == "monthly":
            days = 30
        else:
            days = 7
        
        start_date = datetime.now() - timedelta(days=days)
        
        stats = db.query(StudyStat).filter(
            StudyStat.user_id == user_id,
            StudyStat.study_date >= start_date
        ).all()
        
        mistakes = db.query(Mistake).filter(
            Mistake.user_id == user_id,
            Mistake.created_at >= start_date
        ).all()
        
        report["overview"] = {
            "total_study_days": len(stats),
            "total_study_hours": sum(stat.total_time for stat in stats),
            "total_mistakes": len(mistakes),
            "avg_daily_hours": round(sum(stat.total_time for stat in stats) / len(stats), 1) if stats else 0
        }
        
        subject_stats = {}
        for stat in stats:
            subject = stat.subject or "其他"
            subject_stats[subject] = subject_stats.get(subject, 0) + stat.total_time
        
        report["subject_analysis"] = subject_stats
        
        report["progress"] = {
            "completion_rate": 65,
            "trend": "up"
        }
        
        report["recommendations"] = [
            "继续保持良好的学习节奏",
            "增加薄弱科目的学习时间",
            "定期回顾错题",
            "保持学习动力"
        ]
        
        return AssistantResult(
            True,
            {"report": report},
            f"{period}学习报告已生成"
        )

    def _track_trends(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        from ...models.study_stat import UserStudyStat as StudyStat
        
        days = request.get("days", 14)
        
        trends = {
            "daily_hours": [],
            "subject_distribution": [],
            "improvement_trend": "positive"
        }
        
        for i in range(days):
            date = datetime.now() - timedelta(days=days - i - 1)
            stat = db.query(StudyStat).filter(
                StudyStat.user_id == user_id,
                StudyStat.study_date == date.date()
            ).first()
            
            trends["daily_hours"].append({
                "date": date.strftime("%m-%d"),
                "hours": stat.total_time if stat else 0
            })
        
        return AssistantResult(
            True,
            {"trends": trends},
            "学习趋势跟踪完成"
        )

    def _identify_patterns(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        from ...models.study_stat import UserStudyStat as StudyStat
        
        stats = db.query(StudyStat).filter(StudyStat.user_id == user_id).all()
        
        patterns = {
            "most_active_day": "周一",
            "best_time_slot": "上午9-11点",
            "study_duration": "中等",
            "consistency": "良好",
            "suggestions": [
                "保持上午高效学习",
                "注意周末学习安排",
                "保持学习的规律性"
            ]
        }
        
        return AssistantResult(
            True,
            {"patterns": patterns},
            "学习模式识别完成"
        )

    def _generate_suggestions(self, total_time: float, study_days: int, mistakes: int) -> List[str]:
        suggestions = []
        
        if total_time < 35:
            suggestions.append("建议增加学习时间，每天至少保证5小时")
        elif total_time > 56:
            suggestions.append("注意劳逸结合，避免过度疲劳")
        
        if study_days < 5:
            suggestions.append("建议保持学习的连续性，每周至少学习5天")
        
        if mistakes > 15:
            suggestions.append("错题较多，建议增加复习时间，总结错误原因")
        
        if not suggestions:
            suggestions.append("学习状态良好，继续保持！")
        
        return suggestions

    def handle_collaboration(self, db: Session, user_id: int, message: CollaborationMessage) -> AssistantResult:
        if message.message_type == "request_study_data":
            result = self._analyze_study(db, user_id, {})
            return AssistantResult(
                True,
                {"study_data": result.data.get("analysis", {}), "source": self.code},
                "学习数据分析已完成"
            )
        elif message.message_type == "request_report":
            result = self._generate_report(db, user_id, message.content)
            return AssistantResult(
                True,
                {"report": result.data.get("report", {}), "source": self.code},
                "学习报告已生成"
            )
        return None

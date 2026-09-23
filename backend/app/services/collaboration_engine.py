from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from .assistants import (
    BaseAssistant,
    MistakeAnalyzerAssistant,
    LearningRecommenderAssistant,
    ResourceOrganizerAssistant,
    MemoryTrainerAssistant,
    KnowledgeQAAssistant,
    StudyAnalyzerAssistant,
    AssistantResult,
    CollaborationMessage
)


class Task:
    def __init__(self, task_id: int, user_id: int, task_type: str, priority: int = 5):
        self.task_id = task_id
        self.user_id = user_id
        self.task_type = task_type
        self.priority = priority
        self.status = "pending"
        self.original_request = ""
        self.assistants_involved: List[str] = []
        self.task_flow: List[Dict[str, Any]] = []
        self.intermediate_results: Dict[str, Any] = {}
        self.final_result: Dict[str, Any] = {}
        self.created_at = None
        self.updated_at = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "user_id": self.user_id,
            "task_type": self.task_type,
            "priority": self.priority,
            "status": self.status,
            "assistants_involved": self.assistants_involved,
            "task_flow": self.task_flow,
            "intermediate_results": self.intermediate_results,
            "final_result": self.final_result
        }


class CollaborationEngine:
    def __init__(self, ai_service):
        self.ai_service = ai_service
        self.assistants: Dict[str, BaseAssistant] = {}
        self._register_assistants()
        self.task_queue: List[Task] = []
        self.running_tasks: Dict[int, Task] = {}

    def _register_assistants(self):
        assistants = [
            MistakeAnalyzerAssistant(self.ai_service),
            LearningRecommenderAssistant(self.ai_service),
            ResourceOrganizerAssistant(self.ai_service),
            MemoryTrainerAssistant(self.ai_service),
            KnowledgeQAAssistant(self.ai_service),
            StudyAnalyzerAssistant(self.ai_service)
        ]
        
        for assistant in assistants:
            self.assistants[assistant.code] = assistant

    def get_assistant(self, code: str) -> Optional[BaseAssistant]:
        return self.assistants.get(code)

    def list_assistants(self) -> List[Dict[str, Any]]:
        return [assistant.get_info() for assistant in self.assistants.values()]

    def classify_request(self, request: str) -> Dict[str, Any]:
        request_lower = request.lower()
        
        classification_rules = [
            ("analyze_mistake", ["错题", "错误", "mistake", "薄弱"]),
            ("recommend_topics", ["推荐", "题目", "suggest"]),
            ("search_resources", ["资料", "资源", "resource"]),
            ("schedule_recitation", ["背诵", "单词", "记忆", "recite"]),
            ("answer_question", ["什么是", "为什么", "怎么做", "如何", "问题", "help"]),
            ("generate_report", ["报告", "统计", "分析", "progress"])
        ]
        
        for task_type, keywords in classification_rules:
            if any(keyword in request_lower for keyword in keywords):
                return {"task_type": task_type, "confidence": 0.8}
        
        return {"task_type": "answer_question", "confidence": 0.5}

    def decompose_task(self, task_type: str, request: Dict[str, Any]) -> List[Dict[str, Any]]:
        decomposition_map = {
            "analyze_mistake": [
                {"assistant": "mistake_analyzer", "action": "identify_weak_points", "input": {}},
                {"assistant": "learning_recommender", "action": "suggest_exercises", "input": {"topic": request.get("weak_tag", "")}},
                {"assistant": "resource_organizer", "action": "match_resources", "input": {"topic": request.get("weak_tag", "")}}
            ],
            "recommend_topics": [
                {"assistant": "study_analyzer", "action": "analyze_study", "input": {}},
                {"assistant": "mistake_analyzer", "action": "identify_weak_points", "input": {}},
                {"assistant": "learning_recommender", "action": "recommend_topics", "input": {}}
            ],
            "search_resources": [
                {"assistant": "resource_organizer", "action": "search_resources", "input": {"keyword": request.get("keyword", "")}},
                {"assistant": "resource_organizer", "action": "summarize_content", "input": {}}
            ],
            "schedule_recitation": [
                {"assistant": "memory_trainer", "action": "schedule_recitation", "input": {"mode": "words"}},
                {"assistant": "memory_trainer", "action": "generate_word_list", "input": {}},
                {"assistant": "study_analyzer", "action": "analyze_study", "input": {}}
            ],
            "answer_question": [
                {"assistant": "knowledge_qa", "action": "answer_question", "input": {"message": request.get("message", "")}}
            ],
            "generate_report": [
                {"assistant": "study_analyzer", "action": "generate_report", "input": {"period": "weekly"}},
                {"assistant": "mistake_analyzer", "action": "identify_weak_points", "input": {}},
                {"assistant": "learning_recommender", "action": "recommend_topics", "input": {}}
            ]
        }
        
        return decomposition_map.get(task_type, [
            {"assistant": "knowledge_qa", "action": "answer_question", "input": {"message": request.get("message", "")}}
        ])

    def execute_task(self, db: Session, user_id: int, task_type: str, request: Dict[str, Any]) -> Dict[str, Any]:
        task = Task(0, user_id, task_type)
        task.original_request = str(request)
        task.status = "running"
        
        subtasks = self.decompose_task(task_type, request)
        task.assistants_involved = [sub["assistant"] for sub in subtasks]
        
        intermediate_results = {}
        
        for idx, subtask in enumerate(subtasks):
            assistant_code = subtask["assistant"]
            action = subtask["action"]
            input_data = subtask.get("input", {})
            
            assistant = self.get_assistant(assistant_code)
            if not assistant:
                continue
            
            task.task_flow.append({
                "step": idx + 1,
                "assistant": assistant_code,
                "action": action,
                "status": "executing"
            })
            
            input_data["type"] = action
            
            result = assistant.process(db, user_id, input_data)
            
            task.task_flow[idx]["status"] = "completed"
            task.task_flow[idx]["result"] = result.to_dict()
            
            intermediate_results[assistant_code] = result.data
            
            if assistant.dependencies:
                for dep_code in assistant.dependencies:
                    if dep_code in intermediate_results:
                        dep_result = intermediate_results[dep_code]
                        collaboration_msg = CollaborationMessage(
                            sender_code=assistant_code,
                            message_type=f"request_{action}",
                            content=dep_result
                        )
                        dep_assistant = self.get_assistant(dep_code)
                        if dep_assistant:
                            collab_result = dep_assistant.handle_collaboration(db, user_id, collaboration_msg)
                            if collab_result:
                                intermediate_results[f"{dep_code}_collab"] = collab_result.data
        
        task.status = "completed"
        task.intermediate_results = intermediate_results
        task.final_result = self._integrate_results(task_type, intermediate_results)
        
        return task.to_dict()

    def _integrate_results(self, task_type: str, intermediate_results: Dict[str, Any]) -> Dict[str, Any]:
        integration_strategies = {
            "analyze_mistake": self._integrate_mistake_analysis,
            "recommend_topics": self._integrate_recommendations,
            "search_resources": self._integrate_resources,
            "schedule_recitation": self._integrate_recitation,
            "answer_question": self._integrate_qa,
            "generate_report": self._integrate_report
        }
        
        strategy = integration_strategies.get(task_type, self._integrate_default)
        return strategy(intermediate_results)

    def _integrate_mistake_analysis(self, results: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "analysis": results.get("mistake_analyzer", {}).get("analysis", {}),
            "weak_points": results.get("mistake_analyzer", {}).get("weak_points", []),
            "practice_suggestions": results.get("learning_recommender", {}).get("exercises", []),
            "resources": results.get("resource_organizer", {}).get("resources", []),
            "summary": "已完成错题分析，并生成了针对性的练习建议和学习资源推荐"
        }

    def _integrate_recommendations(self, results: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "study_analysis": results.get("study_analyzer", {}).get("analysis", {}),
            "weak_points": results.get("mistake_analyzer", {}).get("weak_points", []),
            "recommendations": results.get("learning_recommender", {}).get("recommendations", []),
            "summary": "基于学习数据分析和错题情况，为您推荐了重点学习的知识点"
        }

    def _integrate_resources(self, results: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "resources": results.get("resource_organizer", {}).get("resources", []),
            "summary": results.get("resource_organizer", {}).get("summary", {}),
            "search_count": results.get("resource_organizer", {}).get("count", 0),
            "summary_text": "已为您找到相关学习资源并生成内容摘要"
        }

    def _integrate_recitation(self, results: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "schedule": results.get("memory_trainer", {}).get("schedule", {}),
            "words": results.get("memory_trainer", {}).get("words", []),
            "progress": results.get("memory_trainer", {}).get("progress", {}),
            "summary": "已生成背诵计划和单词列表，结合学习进度为您安排了合理的背诵任务"
        }

    def _integrate_qa(self, results: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "answer": results.get("knowledge_qa", {}).get("answer", ""),
            "category": results.get("knowledge_qa", {}).get("category", ""),
            "related_topics": results.get("knowledge_qa", {}).get("related_topics", []),
            "summary": "已为您解答问题"
        }

    def _integrate_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "report": results.get("study_analyzer", {}).get("report", {}),
            "weak_points": results.get("mistake_analyzer", {}).get("weak_points", []),
            "recommendations": results.get("learning_recommender", {}).get("recommendations", []),
            "summary": "已生成完整的学习报告，包含学习分析、薄弱点识别和改进建议"
        }

    def _integrate_default(self, results: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "results": results,
            "summary": "任务已完成"
        }

    def handle_conflict(self, conflicts: List[Dict[str, Any]]) -> Dict[str, Any]:
        resolved = []
        for conflict in conflicts:
            resolved.append({
                "conflict": conflict,
                "resolution": "采用优先级较高的助手结果",
                "resolved": True
            })
        return {"conflicts": conflicts, "resolved": resolved}

    def update_priority(self, task_id: int, new_priority: int) -> bool:
        if task_id in self.running_tasks:
            self.running_tasks[task_id].priority = new_priority
            return True
        return False


collaboration_engine = None


def init_collaboration_engine(ai_service):
    global collaboration_engine
    collaboration_engine = CollaborationEngine(ai_service)
    return collaboration_engine


def get_collaboration_engine() -> CollaborationEngine:
    global collaboration_engine
    return collaboration_engine

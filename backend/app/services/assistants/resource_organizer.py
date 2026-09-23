from typing import Dict, Any, List
from sqlalchemy.orm import Session
from .base_assistant import BaseAssistant, AssistantResult, CollaborationMessage


class ResourceOrganizerAssistant(BaseAssistant):
    code: str = "resource_organizer"
    name: str = "资料整理助手"
    description: str = "管理和整理学习资料，提供资料检索和分类服务"
    domain: str = "resources"
    capabilities: List[str] = ["organize_resources", "search_resources", "categorize_resources", "summarize_content"]
    dependencies: List[str] = ["learning_recommender"]
    priority: int = 9

    def get_system_prompt(self) -> str:
        return """你是一位专业的考研资料整理助手，能够帮助用户管理和整理学习资料。

你的任务是：
1. 对学习资料进行分类和整理
2. 根据关键词搜索相关资料
3. 生成资料摘要和重点内容
4. 推荐相关学习资源

整理原则：
- 按科目和类型进行分类
- 提供清晰的资料标签
- 生成简洁的内容摘要
- 便于用户快速检索和使用
"""

    def process(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        request_type = request.get("type", "search_resources")
        
        if request_type == "organize_resources":
            return self._organize_resources(db, user_id, request)
        elif request_type == "search_resources":
            return self._search_resources(db, user_id, request)
        elif request_type == "categorize_resources":
            return self._categorize_resources(db, user_id, request)
        elif request_type == "summarize_content":
            return self._summarize_content(db, user_id, request)
        
        return AssistantResult(False, {}, "未知的请求类型")

    def _organize_resources(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        from ...models.resource import Resource
        
        resources = db.query(Resource).filter(Resource.user_id == user_id).all()
        
        organized = {
            "total": len(resources),
            "by_subject": {},
            "by_type": {}
        }
        
        for resource in resources:
            subject = resource.subject or "其他"
            rtype = resource.type or "其他"
            
            organized["by_subject"][subject] = organized["by_subject"].get(subject, 0) + 1
            organized["by_type"][rtype] = organized["by_type"].get(rtype, 0) + 1
        
        return AssistantResult(
            True,
            {"organized": organized},
            "资料整理完成"
        )

    def _search_resources(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        from ...models.resource import Resource
        
        keyword = request.get("keyword", "")
        subject = request.get("subject", "")
        
        query = db.query(Resource).filter(Resource.user_id == user_id)
        
        if keyword:
            query = query.filter(Resource.name.contains(keyword) | Resource.description.contains(keyword))
        if subject:
            query = query.filter(Resource.subject == subject)
        
        results = query.all()
        
        return AssistantResult(
            True,
            {
                "resources": [resource.to_dict() for resource in results],
                "count": len(results),
                "keyword": keyword
            },
            f"搜索完成，找到{len(results)}个资源"
        )

    def _categorize_resources(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        from ...models.resource import Resource
        
        resources = db.query(Resource).filter(Resource.user_id == user_id).all()
        
        categories = {
            "视频课程": [],
            "电子书籍": [],
            "练习题集": [],
            "笔记资料": [],
            "真题试卷": [],
            "其他": []
        }
        
        for resource in resources:
            rtype = resource.type
            if rtype in ["视频", "课程"]:
                categories["视频课程"].append(resource.name)
            elif rtype in ["书籍", "pdf"]:
                categories["电子书籍"].append(resource.name)
            elif rtype in ["题库", "习题"]:
                categories["练习题集"].append(resource.name)
            elif rtype in ["笔记"]:
                categories["笔记资料"].append(resource.name)
            elif rtype in ["真题"]:
                categories["真题试卷"].append(resource.name)
            else:
                categories["其他"].append(resource.name)
        
        return AssistantResult(
            True,
            {"categories": categories},
            "资料分类完成"
        )

    def _summarize_content(self, db: Session, user_id: int, request: Dict[str, Any]) -> AssistantResult:
        resource_id = request.get("resource_id")
        
        if resource_id:
            from ...models.resource import Resource
            resource = db.query(Resource).filter(Resource.id == resource_id, Resource.user_id == user_id).first()
            
            if resource:
                summary = {
                    "resource_name": resource.name,
                    "subject": resource.subject,
                    "summary": f"这是一份关于{resource.subject}的学习资料，主要内容包括相关知识点讲解和练习题。建议配合课程视频一起学习，效果更佳。",
                    "key_points": [
                        f"{resource.subject}核心概念",
                        f"{resource.subject}重点考点",
                        f"{resource.subject}解题技巧",
                        f"{resource.subject}常见错误"
                    ],
                    "estimated_reading_time": "约30分钟"
                }
                
                return AssistantResult(
                    True,
                    {"summary": summary},
                    "内容摘要已生成"
                )
        
        return AssistantResult(
            True,
            {"summary": {"message": "请指定资源ID以生成摘要"}},
            "需要资源ID"
        )

    def handle_collaboration(self, db: Session, user_id: int, message: CollaborationMessage) -> AssistantResult:
        if message.message_type == "request_resources":
            topic = message.content.get("topic", "")
            result = self._search_resources(db, user_id, {"keyword": topic})
            return AssistantResult(
                True,
                {"resources": result.data.get("resources", []), "source": self.code},
                "资源检索完成"
            )
        elif message.message_type == "request_summary":
            result = self._summarize_content(db, user_id, message.content)
            return AssistantResult(
                True,
                {"summary": result.data.get("summary", {}), "source": self.code},
                "内容摘要已生成"
            )
        return None

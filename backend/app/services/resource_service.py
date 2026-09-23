import os
import shutil
from sqlalchemy.orm import Session
from datetime import datetime
from ..models.resource import Resource
from ..core.config import UPLOAD_PATH
from ..utils.text_extractor import extract_text
from .search_service import search_service


class ResourceService:
    def upload_resource(self, db: Session, user_id: int, file: any, filename: str) -> dict:
        file_type = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
        file_size = len(file.read())
        file.seek(0)
        
        os.makedirs(UPLOAD_PATH, exist_ok=True)
        
        storage_path = os.path.join(UPLOAD_PATH, f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")
        with open(storage_path, 'wb') as f:
            shutil.copyfileobj(file, f)
        
        resource = Resource(
            user_id=user_id,
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            storage_path=storage_path,
            indexed=False
        )
        db.add(resource)
        db.commit()
        db.refresh(resource)
        
        content = extract_text(storage_path)
        if content:
            search_service.add_document(user_id, resource.id, filename, content)
            resource.indexed = True
            db.commit()
        
        return self._to_dict(resource)
    
    def get_resources(self, db: Session, user_id: int) -> list:
        resources = db.query(Resource).filter(Resource.user_id == user_id).order_by(Resource.upload_date.desc()).all()
        return [self._to_dict(r) for r in resources]
    
    def get_resource(self, db: Session, user_id: int, resource_id: int) -> dict:
        resource = db.query(Resource).filter(
            Resource.id == resource_id,
            Resource.user_id == user_id
        ).first()
        return self._to_dict(resource) if resource else None
    
    def delete_resource(self, db: Session, user_id: int, resource_id: int) -> bool:
        resource = db.query(Resource).filter(
            Resource.id == resource_id,
            Resource.user_id == user_id
        ).first()
        
        if not resource:
            return False
        
        if os.path.exists(resource.storage_path):
            os.remove(resource.storage_path)
        
        search_service.delete_document(resource_id)
        
        db.delete(resource)
        db.commit()
        return True
    
    def search_resources(self, db: Session, user_id: int, query: str) -> list:
        matched_ids = search_service.search(user_id, query)
        
        results = []
        if matched_ids:
            resources = db.query(Resource).filter(
                Resource.id.in_(matched_ids),
                Resource.user_id == user_id
            ).all()
            results = [self._to_dict(r) for r in resources]
        
        if not results:
            resources = db.query(Resource).filter(Resource.user_id == user_id).all()
            for resource in resources:
                if query.lower() in resource.filename.lower():
                    results.append(self._to_dict(resource))
        
        return results
    
    def resource_qa(self, db: Session, user_id: int, resource_id: int, question: str) -> dict:
        resource = db.query(Resource).filter(
            Resource.id == resource_id,
            Resource.user_id == user_id
        ).first()
        
        if not resource:
            return {"answer": "资源不存在", "source": None}
        
        content = extract_text(resource.storage_path)
        
        if content:
            relevant_text = self._find_relevant_text(content, question)
            if relevant_text:
                return {
                    "answer": relevant_text,
                    "source": resource.filename
                }
        
        return {
            "answer": f"针对您上传的资料「{resource.filename}」，关于「{question}」的问题，建议您查阅该资料的相关章节。",
            "source": resource.filename
        }
    
    def _find_relevant_text(self, content: str, question: str) -> str:
        import re
        
        question_keywords = [w for w in question.split() if len(w) >= 2]
        
        sentences = re.split(r'(?<=[。！？])', content)
        
        scores = []
        for sentence in sentences:
            score = 0
            sentence_lower = sentence.lower()
            for keyword in question_keywords:
                if keyword.lower() in sentence_lower:
                    score += 1
            if score > 0:
                scores.append((score, sentence.strip()))
        
        scores.sort(key=lambda x: x[0], reverse=True)
        
        if scores:
            return scores[0][1][:300]
        
        return None
    
    def _to_dict(self, resource: Resource) -> dict:
        return {
            "id": resource.id,
            "user_id": resource.user_id,
            "filename": resource.filename,
            "file_type": resource.file_type,
            "file_size": resource.file_size,
            "storage_path": resource.storage_path,
            "indexed": resource.indexed,
            "upload_date": resource.upload_date.isoformat() if resource.upload_date else None
        }


resource_service = ResourceService()
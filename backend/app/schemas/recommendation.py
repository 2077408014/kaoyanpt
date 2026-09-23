from typing import Optional, List
from pydantic import BaseModel, Field

class RecommendationGenerateRequest(BaseModel):
    subject: Optional[str] = None
    knowledge_point: Optional[str] = None
    difficulty: Optional[str] = None
    count: int = Field(10, ge=5, le=50)
    source: Optional[str] = None

class RecommendationResponse(BaseModel):
    id: int
    user_id: int
    subject: str
    knowledge_point: str
    difficulty: str
    question_text: str
    answer: str
    analysis: Optional[str]
    source: str
    completed: bool
    result: Optional[str]
    created_at: str

    class Config:
        from_attributes = True

class WeakPointResponse(BaseModel):
    subject: str
    knowledge_point: str
    weak_level: int
    mistake_count: int

class RecommendationCreate(BaseModel):
    subject: str
    knowledge_point: str
    difficulty: str
    question_text: str
    answer: str
    analysis: Optional[str] = None
    source: str

class RecommendationComplete(BaseModel):
    result: str

class RecommendationReport(BaseModel):
    total_recommendations: int
    completed_recommendations: int
    correct_recommendations: int
    accuracy_rate: float
    weak_points: List[WeakPointResponse]
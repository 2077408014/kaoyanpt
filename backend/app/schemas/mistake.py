from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, Field

class MistakeCreate(BaseModel):
    subject: str = Field(..., description="科目（数学/英语/政治/专业课）")
    knowledge_point: Optional[str] = Field(None, description="知识点")
    error_type: Optional[str] = Field(None, description="错误类型（概念错误/计算错误/审题错误）")
    difficulty: Optional[str] = Field(None, description="难度（简单/中等/困难）")
    question_text: Optional[str] = Field(None, description="题目文本")
    answer: Optional[str] = Field(None, description="正确答案")
    analysis: Optional[str] = Field(None, description="解析")
    error_reason: Optional[str] = Field(None, description="错误原因")
    image_path: Optional[str] = Field(None, description="题目图片路径")

class MistakeUpdate(BaseModel):
    subject: Optional[str] = None
    knowledge_point: Optional[str] = None
    error_type: Optional[str] = None
    difficulty: Optional[str] = None
    question_text: Optional[str] = None
    answer: Optional[str] = None
    analysis: Optional[str] = None
    error_reason: Optional[str] = None
    image_path: Optional[str] = None

class MistakeResponse(BaseModel):
    id: int
    user_id: int
    subject: str
    knowledge_point: Optional[str]
    error_type: Optional[str]
    difficulty: Optional[str]
    mastery_level: str
    question_text: Optional[str]
    answer: Optional[str]
    analysis: Optional[str]
    error_reason: Optional[str]
    image_path: Optional[str]
    next_review_date: Optional[date]
    review_count: int
    correct_count: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True

class MistakeReviewCreate(BaseModel):
    result: str = Field(..., description="结果（正确/错误/部分正确）")
    notes: Optional[str] = None

class MistakeReviewResponse(BaseModel):
    id: int
    mistake_id: int
    user_id: int
    result: str
    review_date: datetime
    notes: Optional[str]

    class Config:
        from_attributes = True

class MistakeRecognizeRequest(BaseModel):
    image_path: str = Field(..., description="已上传的图片路径")

class MistakeRecognizeResponse(BaseModel):
    question_text: Optional[str] = Field(None, description="OCR识别的题目文本")
    subject: Optional[str] = Field(None, description="建议科目")
    knowledge_point: Optional[str] = Field(None, description="建议知识点")
    confidence: float = Field(0.0, description="置信度")
    raw_text: str = Field("", description="原始OCR文本")

class SimilarMistakeResponse(BaseModel):
    id: int
    subject: str
    knowledge_point: Optional[str]
    question_text: Optional[str]
    difficulty: Optional[str]
    mastery_level: str
    similarity_score: float

    class Config:
        from_attributes = True

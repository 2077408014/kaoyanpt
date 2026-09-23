from pydantic import BaseModel, Field

class ResourceResponse(BaseModel):
    id: int
    user_id: int
    filename: str
    file_type: str
    file_size: int
    upload_date: str

    class Config:
        from_attributes = True

class ResourceSearchRequest(BaseModel):
    query: str = Field(..., description="搜索关键词")

class ResourceQARequest(BaseModel):
    question: str = Field(..., description="用户问题")
from pydantic import BaseModel, Field

class AIChatRequest(BaseModel):
    message: str = Field(..., description="用户消息")

class AICommandRequest(BaseModel):
    command: str = Field(..., description="自然语言指令")

class AIResponse(BaseModel):
    content: str = Field(..., description="AI回复内容")
    source: str = Field(..., description="答案来源")
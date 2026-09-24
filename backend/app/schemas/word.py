from typing import Optional
from pydantic import BaseModel, Field

class WordResponse(BaseModel):
    id: int
    word: str
    phonetic: Optional[str]
    meaning: str
    example_sentence: Optional[str]
    difficulty: int
    frequency: int
    exam_requirement: str

    class Config:
        from_attributes = True

class UserWordResponse(BaseModel):
    id: int
    user_id: int
    word_id: int
    word: str
    mastery_level: str
    next_review_date: Optional[str]
    review_count: int
    correct_count: int
    last_study_date: Optional[str]
    first_study_date: Optional[str]
    last_rating: Optional[str]
    srs_stage: int

    class Config:
        from_attributes = True

class WordStudyRequest(BaseModel):
    word_id: int
    result: str = Field(..., description="评级：忘记/困难/一般/认识（兼容旧三档）")
    session_id: Optional[str] = Field(None, description="会话ID，用于背诵记录分组")
    source: str = Field("card", description="来源：card/push/quiz")
    quiz_result: Optional[bool] = Field(None, description="测验对错（source=quiz 时）")

class StudyPlanRequest(BaseModel):
    daily_word_count: int = Field(..., ge=5, le=100, description="每日学习单词数量")
    word_category: Optional[str] = Field(None, description="词汇分类")
    batch_size: int = Field(20, ge=5, le=50, description="每轮背诵批次大小")
    study_mode: str = Field("mixed", description="背诵模式：new_first(新词优先) / mixed(混合模式)")

class PushConfig(BaseModel):
    count: int = 10
    interval_seconds: int = 60
    category: Optional[str] = None
    auto_play: bool = True

class RoundWordItem(BaseModel):
    word_id: int
    type: str  # new / review
    repeat_count: int = 0

class StudySessionData(BaseModel):
    current_round: int = 0
    total_rounds: int = 0
    round_queue: list[dict] = []
    round_stats: dict = {"known": 0, "vague": 0, "unknown": 0}
    global_index: int = 0
    total_words_today: int = 0
    study_mode: str = "mixed"
    batch_size: int = 20
    all_word_ids: list[int] = []
    completed_rounds: int = 0
    category: Optional[str] = None
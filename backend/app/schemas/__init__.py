from .auth import UserCreate, UserLogin, UserResponse, TokenResponse
from .mistake import MistakeCreate, MistakeUpdate, MistakeResponse, MistakeReviewCreate, MistakeReviewResponse
from .word import WordResponse, UserWordResponse, WordStudyRequest, StudyPlanRequest
from .resource import ResourceResponse, ResourceSearchRequest
from .recommendation import RecommendationGenerateRequest, RecommendationResponse, WeakPointResponse
from .ai import AIChatRequest, AICommandRequest, AIResponse
from .politics import (
    PoliticsRecitationCreate, PoliticsRecitationUpdate, PoliticsRecitationResponse,
    PoliticsRecognizeRequest, PoliticsRecognizeResponse,
    RecitationReminderCreate, RecitationReminderUpdate, RecitationReminderResponse
)
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BACKEND_DIR.parent
UPLOAD_PATH = BACKEND_DIR / "uploads"
INDEX_PATH = BACKEND_DIR / "indexes"
DATABASE_PATH = ROOT_DIR / "kaoyan_xt.db"
RAG_DATA_PATH = Path(__file__).resolve().parent.parent / "data"

UPLOAD_PATH.mkdir(parents=True, exist_ok=True)
INDEX_PATH.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    DATABASE_URL: str = f"sqlite:///{DATABASE_PATH}"
    SECRET_KEY: str = "kaoyan_xt_secret_key_2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://api.deepseek.com/v1"
    AI_MODEL: str = "deepseek-chat"
    AI_MAX_TOKENS: int = 2048
    AI_TIMEOUT: int = 60
    LOCAL_LLM_BASE_URL: str = "http://localhost:8081"

    # 本地 LLM 部署参数（由 start_llm.py 独立进程读取）
    LLM_MODEL_NAME: str = "Qwen/Qwen2.5-7B-Instruct"
    LLM_DEVICE: str = "auto"
    LLM_MAX_CONTEXT: int = 4096
    LLM_TEMPERATURE: float = 0.7
    LLM_PORT: int = 8081

    # 邮件服务（忘记密码/邮箱验证）
    SMTP_HOST: str = "smtp.qq.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
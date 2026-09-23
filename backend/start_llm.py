import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.local_llm_service import LocalLLMService
from app.core.config import settings

if __name__ == "__main__":
    llm_service = LocalLLMService(
        model_name=settings.LLM_MODEL_NAME,
        device=settings.LLM_DEVICE
    )
    llm_service.load_model()
    llm_service.run_server(port=settings.LLM_PORT)
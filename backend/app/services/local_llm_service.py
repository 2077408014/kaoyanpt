import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import threading
import uvicorn

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    _HAS_TORCH = True
except Exception as e:
    print(f"[LocalLLM] torch/transformers 不可用（{e}），本地推理模式将不可用（请使用 CPU/GPU 环境安装）")
    _HAS_TORCH = False
    torch = None
    AutoTokenizer = None
    AutoModelForCausalLM = None


class LocalLLMService:
    def __init__(self, model_name: str = "Qwen/Qwen2.5-7B-Instruct", device: str = "auto"):
        self.model_name = model_name
        self.device = device
        self.tokenizer = None
        self.model = None
        self.app = FastAPI(title="Local LLM Service", version="1.0.0")
        self._setup_routes()
        self.server = None

    def _setup_routes(self):
        class ChatRequest(BaseModel):
            model: str = "local-llm"
            messages: list
            max_tokens: int = 1024
            temperature: float = 0.7

        @self.app.post("/v1/chat/completions")
        async def chat_completions(request: ChatRequest):
            if not self.model:
                raise HTTPException(status_code=503, detail="Model not loaded")

            try:
                user_message = request.messages[-1]["content"]
                response = self.generate(user_message, max_tokens=request.max_tokens, temperature=request.temperature)
                return {
                    "id": "chatcmpl-local-1",
                    "object": "chat.completion",
                    "created": int(os.popen("date +%s").read().strip() or 0),
                    "model": self.model_name,
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": response
                        },
                        "finish_reason": "stop"
                    }],
                    "usage": {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0
                    }
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/v1/models")
        async def list_models():
            return {
                "object": "list",
                "data": [{
                    "id": "local-llm",
                    "object": "model",
                    "created": int(os.popen("date +%s").read().strip() or 0),
                    "owned_by": "local",
                    "root": self.model_name,
                    "parent": None
                }]
            }

        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy" if self.model else "loading"}

    def load_model(self):
        if not _HAS_TORCH:
            raise RuntimeError("torch/transformers 未安装，无法加载本地模型")

        print(f"Loading model: {self.model_name}...")

        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)

            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            torch_dtype = torch.float32

            if torch.cuda.is_available():
                torch_dtype = torch.float16

            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                trust_remote_code=True,
                device_map="auto",
                torch_dtype=torch_dtype,
                low_cpu_mem_usage=True,
                attn_implementation="eager"
            )

            print("Model loaded successfully!")
        except Exception as e:
            print(f"Failed to load model: {e}")
            raise

    def generate(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7) -> str:
        if not self.model:
            raise RuntimeError("Model not loaded")

        messages = [
            {"role": "system", "content": "你是一个专业的考研复习助手，精通考研英语、政治、数学、专业课等各科目知识。使用markdown格式回答，数学公式使用LaTeX格式，行内公式用$...$包裹，独立公式用$$...$$包裹。"},
            {"role": "user", "content": prompt}
        ]

        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

        inputs = self.tokenizer(text, return_tensors="pt").to(self.model.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                top_p=0.9,
                repetition_penalty=1.05,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
                use_cache=False
            )

        generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        if "[/INST]" in generated_text:
            response = generated_text.split("[/INST]")[-1].strip()
        else:
            response = generated_text[len(text):].strip()

        return response

    def run_server(self, port: int = 8081):
        self.server = threading.Thread(
            target=uvicorn.run,
            args=(self.app,),
            kwargs={"host": "0.0.0.0", "port": port, "log_level": "info"},
            daemon=True
        )
        self.server.start()
        print(f"Local LLM server running on http://localhost:{port}")

        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("Stopping local LLM server...")


if __name__ == "__main__":
    from ..core.config import settings
    service = LocalLLMService(model_name=settings.LLM_MODEL_NAME, device=settings.LLM_DEVICE)
    service.load_model()
    service.run_server(port=settings.LLM_PORT)
# 两人团队开发工作流隔离策略实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为两人团队建立完全隔离的开发工作流，一人负责测试现有功能，另一人负责部署本地开源大语言模型，确保双方工作互不干扰，同时支持最终集成。

**Architecture:** 采用Git工作树(Git Worktree)实现代码隔离，通过独立的配置文件实现环境隔离，通过清晰的分支策略确保工作流独立。

**Tech Stack:** Git Worktree, Python, Vue.js, SQLite, FastAPI, Vite

## Global Constraints

- 测试工程师分支: `feature/testing-workflow`
- 模型部署工程师分支: `feature/local-llm-deployment`
- 工作树目录: `.worktrees/`
- 测试环境端口: 前端5173, 后端8000
- 模型部署环境端口: 前端5180, 后端8080
- 测试数据库: `kaoyan_xt_test.db`
- 模型部署数据库: `kaoyan_xt_llm.db`
- 所有工作树必须加入.gitignore

---

## 文件结构

```
KaoYanXT/
├── .gitignore                    # 添加工作树和环境文件忽略规则
├── .worktrees/                   # Git工作树目录（隔离的工作空间）
│   ├── feature-testing-workflow/ # 测试工程师工作空间
│   └── feature-local-llm-deployment/ # 模型部署工程师工作空间
├── backend/
│   ├── .env                      # 主环境配置
│   ├── .env.test                 # 测试环境配置
│   ├── .env.llm                  # 模型部署环境配置
│   └── app/
│       └── config.py             # 动态配置加载
├── frontend/
│   ├── .env                      # 主环境配置
│   ├── .env.test                 # 测试环境配置
│   └── .env.llm                  # 模型部署环境配置
└── docker-compose.yml            # 可选：Docker隔离部署
```

---

### Task 1: 更新 .gitignore 文件

**Files:**
- Modify: `.gitignore`

**Interfaces:**
- Produces: 工作树和环境文件的Git忽略规则

- [ ] **Step 1: 更新 .gitignore 添加工作树和环境文件忽略规则**

```
# Git Worktrees
.worktrees/
worktrees/

# Environment files
backend/.env
backend/.env.test
backend/.env.llm
frontend/.env
frontend/.env.test
frontend/.env.llm

# Database files
backend/*.db

# Node.js modules
frontend/node_modules/

# Build outputs
frontend/dist/

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# Logs
*.log
```

- [ ] **Step 2: 提交变更**

```bash
git add .gitignore
git commit -m "chore: add worktree and environment file ignore rules"
```

---

### Task 2: 创建测试工程师工作树

**Files:**
- Create: `.worktrees/feature-testing-workflow/` (Git工作树)

**Interfaces:**
- Produces: 隔离的测试工程师工作空间

- [ ] **Step 1: 创建测试工程师工作树**

```bash
git worktree add .worktrees/feature-testing-workflow -b feature/testing-workflow
```

- [ ] **Step 2: 验证工作树创建成功**

```bash
git worktree list
```
Expected: 显示 `.worktrees/feature-testing-workflow` 在列表中

- [ ] **Step 3: 进入测试工作树并初始化环境**

```bash
cd .worktrees/feature-testing-workflow

# 安装后端依赖
cd backend
pip install -r requirements.txt

# 安装前端依赖
cd ../frontend
npm install

cd ../..
```

- [ ] **Step 4: 提交工作树创建**

```bash
git add .gitignore
git commit -m "chore: add testing workflow worktree"
```

---

### Task 3: 创建模型部署工程师工作树

**Files:**
- Create: `.worktrees/feature-local-llm-deployment/` (Git工作树)

**Interfaces:**
- Produces: 隔离的模型部署工程师工作空间

- [ ] **Step 1: 创建模型部署工程师工作树**

```bash
git worktree add .worktrees/feature-local-llm-deployment -b feature/local-llm-deployment
```

- [ ] **Step 2: 验证工作树创建成功**

```bash
git worktree list
```
Expected: 显示两个工作树在列表中

- [ ] **Step 3: 进入模型部署工作树并初始化环境**

```bash
cd .worktrees/feature-local-llm-deployment

# 安装后端依赖
cd backend
pip install -r requirements.txt

# 安装前端依赖
cd ../frontend
npm install

# 安装LLM相关依赖
pip install transformers torch accelerate sentence-transformers

cd ../..
```

- [ ] **Step 4: 提交工作树创建**

```bash
git add .gitignore
git commit -m "chore: add local LLM deployment worktree"
```

---

### Task 4: 创建测试环境配置文件

**Files:**
- Create: `.worktrees/feature-testing-workflow/backend/.env.test`
- Create: `.worktrees/feature-testing-workflow/frontend/.env.test`

**Interfaces:**
- Produces: 测试环境专用配置

- [ ] **Step 1: 创建测试后端环境配置**

```bash
cd .worktrees/feature-testing-workflow/backend
```

```env
# 测试环境配置 - 测试工程师专用
DATABASE_URL=sqlite:///./kaoyan_xt_test.db
SECRET_KEY=kaoyan_xt_test_secret_key_2026
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
UPLOAD_DIR=./uploads_test
INDEX_DIR=./indexes_test
SERVER_PORT=8000

# AI配置 - 使用预设响应进行测试
AI_API_KEY=
AI_BASE_URL=https://api.deepseek.com/v1
AI_MODEL=deepseek-chat
AI_MAX_TOKENS=2048
AI_TIMEOUT=60
USE_LOCAL_LLM=false
```

- [ ] **Step 2: 创建测试前端环境配置**

```bash
cd .worktrees/feature-testing-workflow/frontend
```

```env
# 测试环境配置 - 测试工程师专用
VITE_APP_TITLE=考研复习平台-测试环境
VITE_API_BASE_URL=http://localhost:8000
VITE_PORT=5173
VITE_NODE_ENV=test
```

- [ ] **Step 3: 创建测试上传目录**

```bash
cd .worktrees/feature-testing-workflow/backend
mkdir -p uploads_test indexes_test
```

- [ ] **Step 4: 提交配置文件**

```bash
cd .worktrees/feature-testing-workflow
git add backend/.env.test frontend/.env.test
git commit -m "chore: add testing environment configuration"
```

---

### Task 5: 创建模型部署环境配置文件

**Files:**
- Create: `.worktrees/feature-local-llm-deployment/backend/.env.llm`
- Create: `.worktrees/feature-local-llm-deployment/frontend/.env.llm`

**Interfaces:**
- Produces: 模型部署环境专用配置

- [ ] **Step 1: 创建模型部署后端环境配置**

```bash
cd .worktrees/feature-local-llm-deployment/backend
```

```env
# 模型部署环境配置 - LLM工程师专用
DATABASE_URL=sqlite:///./kaoyan_xt_llm.db
SECRET_KEY=kaoyan_xt_llm_secret_key_2026
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
UPLOAD_DIR=./uploads_llm
INDEX_DIR=./indexes_llm
SERVER_PORT=8080

# AI配置 - 使用本地LLM
AI_API_KEY=local
AI_BASE_URL=http://localhost:8081/v1
AI_MODEL=local-llm-model
AI_MAX_TOKENS=4096
AI_TIMEOUT=120
USE_LOCAL_LLM=true

# 本地LLM配置
LLM_MODEL_NAME=Qwen/Qwen2-7B-Instruct
LLM_DEVICE=auto
LLM_MAX_CONTEXT=4096
LLM_TEMPERATURE=0.7
LLM_PORT=8081
```

- [ ] **Step 2: 创建模型部署前端环境配置**

```bash
cd .worktrees/feature-local-llm-deployment/frontend
```

```env
# 模型部署环境配置 - LLM工程师专用
VITE_APP_TITLE=考研复习平台-LLM部署环境
VITE_API_BASE_URL=http://localhost:8080
VITE_PORT=5180
VITE_NODE_ENV=llm
```

- [ ] **Step 3: 创建LLM上传目录**

```bash
cd .worktrees/feature-local-llm-deployment/backend
mkdir -p uploads_llm indexes_llm
```

- [ ] **Step 4: 提交配置文件**

```bash
cd .worktrees/feature-local-llm-deployment
git add backend/.env.llm frontend/.env.llm
git commit -m "chore: add LLM deployment environment configuration"
```

---

### Task 6: 更新后端配置加载逻辑以支持多环境

**Files:**
- Modify: `.worktrees/feature-testing-workflow/backend/app/config.py`
- Modify: `.worktrees/feature-local-llm-deployment/backend/app/config.py`

**Interfaces:**
- Consumes: 环境变量配置
- Produces: 动态配置加载能力

- [ ] **Step 1: 更新测试工作树的配置加载逻辑**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./kaoyan_xt.db"
    SECRET_KEY: str = "kaoyan_xt_secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    UPLOAD_DIR: str = "./uploads"
    INDEX_DIR: str = "./indexes"
    SERVER_PORT: int = 8000
    
    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://api.deepseek.com/v1"
    AI_MODEL: str = "deepseek-chat"
    AI_MAX_TOKENS: int = 2048
    AI_TIMEOUT: int = 60
    USE_LOCAL_LLM: bool = False
    
    LLM_MODEL_NAME: str = "Qwen/Qwen2-7B-Instruct"
    LLM_DEVICE: str = "auto"
    LLM_MAX_CONTEXT: int = 4096
    LLM_TEMPERATURE: float = 0.7
    LLM_PORT: int = 8081

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

def get_settings():
    env_file = ".env"
    if os.getenv("ENVIRONMENT") == "test":
        env_file = ".env.test"
    elif os.getenv("ENVIRONMENT") == "llm":
        env_file = ".env.llm"
    
    return Settings(_env_file=env_file)

settings = get_settings()
```

- [ ] **Step 2: 更新模型部署工作树的配置加载逻辑**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./kaoyan_xt.db"
    SECRET_KEY: str = "kaoyan_xt_secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    UPLOAD_DIR: str = "./uploads"
    INDEX_DIR: str = "./indexes"
    SERVER_PORT: int = 8000
    
    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://api.deepseek.com/v1"
    AI_MODEL: str = "deepseek-chat"
    AI_MAX_TOKENS: int = 2048
    AI_TIMEOUT: int = 60
    USE_LOCAL_LLM: bool = False
    
    LLM_MODEL_NAME: str = "Qwen/Qwen2-7B-Instruct"
    LLM_DEVICE: str = "auto"
    LLM_MAX_CONTEXT: int = 4096
    LLM_TEMPERATURE: float = 0.7
    LLM_PORT: int = 8081

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

def get_settings():
    env_file = ".env"
    if os.getenv("ENVIRONMENT") == "test":
        env_file = ".env.test"
    elif os.getenv("ENVIRONMENT") == "llm":
        env_file = ".env.llm"
    
    return Settings(_env_file=env_file)

settings = get_settings()
```

- [ ] **Step 3: 提交变更**

```bash
cd .worktrees/feature-testing-workflow
git add backend/app/config.py
git commit -m "feat: add multi-environment configuration support"

cd ../../.worktrees/feature-local-llm-deployment
git add backend/app/config.py
git commit -m "feat: add multi-environment configuration support"
```

---

### Task 7: 更新前端 Vite 配置以支持多环境

**Files:**
- Modify: `.worktrees/feature-testing-workflow/frontend/vite.config.ts`
- Modify: `.worktrees/feature-local-llm-deployment/frontend/vite.config.ts`

**Interfaces:**
- Consumes: 环境变量配置
- Produces: 动态端口和代理配置

- [ ] **Step 1: 更新测试工作树的Vite配置**

```typescript
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd())
  
  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src')
      }
    },
    server: {
      host: true,
      port: parseInt(env.VITE_PORT) || 5173,
      proxy: {
        '/api': {
          target: env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
          changeOrigin: true
        },
        '/uploads': {
          target: env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
          changeOrigin: true
        }
      }
    }
  }
})
```

- [ ] **Step 2: 更新模型部署工作树的Vite配置**

```typescript
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd())
  
  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src')
      }
    },
    server: {
      host: true,
      port: parseInt(env.VITE_PORT) || 5180,
      proxy: {
        '/api': {
          target: env.VITE_API_BASE_URL || 'http://127.0.0.1:8080',
          changeOrigin: true
        },
        '/uploads': {
          target: env.VITE_API_BASE_URL || 'http://127.0.0.1:8080',
          changeOrigin: true
        }
      }
    }
  }
})
```

- [ ] **Step 3: 提交变更**

```bash
cd .worktrees/feature-testing-workflow
git add frontend/vite.config.ts
git commit -m "feat: add multi-environment Vite configuration"

cd ../../.worktrees/feature-local-llm-deployment
git add frontend/vite.config.ts
git commit -m "feat: add multi-environment Vite configuration"
```

---

### Task 8: 创建本地LLM部署服务

**Files:**
- Create: `.worktrees/feature-local-llm-deployment/backend/app/services/local_llm_service.py`
- Modify: `.worktrees/feature-local-llm-deployment/backend/app/services/ai_service.py`
- Create: `.worktrees/feature-local-llm-deployment/backend/start_llm.py`

**Interfaces:**
- Consumes: AI服务配置
- Produces: 本地LLM推理服务

- [ ] **Step 1: 创建本地LLM服务模块**

```python
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from threading import Thread
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch
import os

class LocalLLMService:
    def __init__(self, model_name: str = "Qwen/Qwen2-7B-Instruct", device: str = "auto"):
        self.model_name = model_name
        self.device = device
        self.tokenizer = None
        self.model = None
        self.pipeline = None
        self.app = FastAPI(title="Local LLM Service")
        self._setup_routes()
    
    def load_model(self):
        print(f"Loading model: {self.model_name}...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            trust_remote_code=True,
            device_map="auto",
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            load_in_4bit=True if torch.cuda.is_available() else False
        )
        self.pipeline = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            max_new_tokens=1024,
            temperature=0.7,
            top_p=0.9,
            repetition_penalty=1.05
        )
        print("Model loaded successfully!")
    
    def generate(self, prompt: str) -> str:
        if not self.pipeline:
            raise RuntimeError("Model not loaded")
        
        messages = [
            {"role": "system", "content": "你是一个专业的考研复习助手，精通考研英语、政治、数学、专业课等各科目知识。使用markdown格式回答，数学公式使用LaTeX格式。"},
            {"role": "user", "content": prompt}
        ]
        
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        result = self.pipeline(text)
        return result[0]["generated_text"].split("[/INST]")[-1].strip()
    
    def _setup_routes(self):
        class ChatRequest(BaseModel):
            model: str
            messages: list
            max_tokens: int = 1024
            temperature: float = 0.7
        
        @self.app.post("/v1/chat/completions")
        async def chat_completions(request: ChatRequest):
            try:
                user_message = request.messages[-1]["content"]
                response = self.generate(user_message)
                
                return {
                    "choices": [{
                        "message": {"role": "assistant", "content": response}
                    }],
                    "usage": {}
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
    
    def run_server(self, port: int = 8081):
        uvicorn.run(self.app, host="0.0.0.0", port=port)
    
    def start_in_background(self, port: int = 8081):
        thread = Thread(target=self.run_server, args=(port,), daemon=True)
        thread.start()
        return thread
```

- [ ] **Step 2: 更新AI服务以支持本地LLM**

```python
def _call_ai_model(self, db: Session, user_id: int, message: str, config: dict = None) -> str:
    if config is None:
        config = self._get_user_ai_config(db, user_id)
    
    if config.get("api_key") == "local" or settings.USE_LOCAL_LLM:
        try:
            from .local_llm_service import LocalLLMService
            
            llm_service = LocalLLMService(
                model_name=settings.LLM_MODEL_NAME,
                device=settings.LLM_DEVICE
            )
            llm_service.load_model()
            return llm_service.generate(message)
        except Exception as e:
            print(f"Local LLM call failed: {e}")
            responses = AI_RESPONSES.get("default", AI_RESPONSES["default"])
            return responses[random.randint(0, len(responses) - 1)]
    
    history = self._get_conversation_history(db, user_id)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    
    for msg in history:
        role = "user" if msg["message_type"] == "question" else "assistant"
        messages.append({"role": role, "content": msg["content"]})
    
    messages.append({"role": "user", "content": message})
    
    payload = {
        "model": config["model"],
        "messages": messages,
        "max_tokens": self.max_tokens,
        "temperature": 0.7
    }
    
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json"
    }
    
    url = f"{config['base_url']}/chat/completions"
    
    response = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
    response.raise_for_status()
    
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()
```

- [ ] **Step 3: 创建LLM启动脚本**

```python
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.local_llm_service import LocalLLMService
from app.config import settings

if __name__ == "__main__":
    llm_service = LocalLLMService(
        model_name=settings.LLM_MODEL_NAME,
        device=settings.LLM_DEVICE
    )
    llm_service.load_model()
    llm_service.run_server(port=settings.LLM_PORT)
```

- [ ] **Step 4: 提交变更**

```bash
cd .worktrees/feature-local-llm-deployment
git add backend/app/services/local_llm_service.py backend/app/services/ai_service.py backend/start_llm.py
git commit -m "feat: add local LLM deployment service"
```

---

### Task 9: 创建集成合并策略文档

**Files:**
- Create: `docs/integration-strategy.md`

**Interfaces:**
- Produces: 清晰的分支合并流程和集成策略

- [ ] **Step 1: 创建集成策略文档**

```markdown
# 两人团队开发集成策略

## 分支结构

```
master
├── feature/testing-workflow     # 测试工程师分支
└── feature/local-llm-deployment # LLM部署工程师分支
```

## 工作流隔离规则

### 测试工程师 (`feature/testing-workflow`)
- **职责**: 测试现有功能、修复bug、优化测试用例
- **环境**: 端口8000(后端)/5173(前端), 数据库`kaoyan_xt_test.db`
- **禁止**: 修改AI服务核心逻辑、添加新的LLM依赖

### LLM部署工程师 (`feature/local-llm-deployment`)
- **职责**: 部署本地开源大语言模型、优化推理性能
- **环境**: 端口8080(后端)/5180(前端), 数据库`kaoyan_xt_llm.db`
- **禁止**: 修改业务逻辑、改动测试用例

## 集成流程

### Step 1: 功能完成检查
1. 测试工程师确认所有测试通过
2. LLM部署工程师确认本地模型服务正常运行

### Step 2: 创建集成分支
```bash
git checkout master
git pull origin master
git checkout -b feature/integration
```

### Step 3: 合并测试分支
```bash
git merge --no-ff feature/testing-workflow
# 解决冲突（如果有）
git commit -m "merge: integrate testing workflow changes"
```

### Step 4: 合并LLM部署分支
```bash
git merge --no-ff feature/local-llm-deployment
# 解决冲突（重点关注AI服务配置）
git commit -m "merge: integrate local LLM deployment"
```

### Step 5: 集成测试
1. 运行完整测试套件
2. 验证AI功能在本地LLM和远程API模式下都能正常工作
3. 检查数学公式渲染是否正确

### Step 6: 推送到主分支
```bash
git checkout master
git merge --no-ff feature/integration
git push origin master
```

### Step 7: 删除临时分支
```bash
git branch -d feature/testing-workflow
git branch -d feature/local-llm-deployment
git branch -d feature/integration
git push origin --delete feature/testing-workflow feature/local-llm-deployment
```

## 配置合并策略

### AI服务配置 (.env)
- `USE_LOCAL_LLM`: 默认为`false`，生产环境使用远程API
- `AI_BASE_URL`: 保留远程API地址作为默认值
- `LLM_MODEL_NAME`: 保留本地模型配置，用于开发环境

### 端口配置
- 生产环境: 前端5173, 后端8000
- 开发环境: 根据需求选择

## 回滚策略

如果集成出现问题，使用以下命令回滚：

```bash
git revert <merge-commit-hash>
# 或者
git reset --hard origin/master
```

## 沟通协调

1. 每日站会同步进度
2. 合并前互相通知
3. 冲突解决优先考虑主分支逻辑
4. AI服务接口变更需提前沟通
```

- [ ] **Step 2: 提交文档**

```bash
cd d:\软件\trae_cn\projects\KaoYanXT
git add docs/integration-strategy.md
git commit -m "docs: add team integration strategy"
```

---

### Task 10: 创建启动脚本简化工作流

**Files:**
- Create: `.worktrees/feature-testing-workflow/start-testing.sh` (Windows: `.bat`)
- Create: `.worktrees/feature-testing-workflow/start-testing.bat`
- Create: `.worktrees/feature-local-llm-deployment/start-llm.sh` (Windows: `.bat`)
- Create: `.worktrees/feature-local-llm-deployment/start-llm.bat`

**Interfaces:**
- Produces: 一键启动脚本

- [ ] **Step 1: 创建测试环境启动脚本(bat)**

```bat
@echo off
echo 启动测试环境...
echo 后端端口: 8000
echo 前端端口: 5173

set ENVIRONMENT=test

cd backend
echo 启动后端服务...
start cmd /k "uvicorn app.main:app --host 0.0.0.0 --port 8000"

cd ../frontend
echo 启动前端服务...
start cmd /k "npm run dev -- --mode test"

echo 测试环境启动完成！
echo 后端地址: http://localhost:8000
echo 前端地址: http://localhost:5173
```

- [ ] **Step 2: 创建LLM环境启动脚本(bat)**

```bat
@echo off
echo 启动LLM部署环境...
echo 后端端口: 8080
echo 前端端口: 5180
echo LLM端口: 8081

set ENVIRONMENT=llm

cd backend
echo 启动本地LLM服务...
start cmd /k "python start_llm.py"

echo 等待LLM模型加载...
timeout /t 30 /nobreak >nul

echo 启动后端服务...
start cmd /k "uvicorn app.main:app --host 0.0.0.0 --port 8080"

cd ../frontend
echo 启动前端服务...
start cmd /k "npm run dev -- --mode llm"

echo LLM环境启动完成！
echo 后端地址: http://localhost:8080
echo 前端地址: http://localhost:5180
echo LLM服务: http://localhost:8081
```

- [ ] **Step 3: 提交启动脚本**

```bash
cd .worktrees/feature-testing-workflow
git add start-testing.bat
git commit -m "chore: add testing environment start script"

cd ../../.worktrees/feature-local-llm-deployment
git add start-llm.bat
git commit -m "chore: add LLM environment start script"
```

---

## Self-Review

**1. Spec coverage:**
- ✅ Git分支策略 - Task 2, 3
- ✅ Git工作树隔离 - Task 2, 3
- ✅ 环境配置隔离 - Task 4, 5, 6, 7
- ✅ 本地LLM部署 - Task 8
- ✅ 集成策略 - Task 9
- ✅ 启动脚本 - Task 10

**2. Placeholder scan:**
- ✅ 所有步骤包含完整代码
- ✅ 没有TBD或TODO

**3. Type consistency:**
- ✅ 配置文件命名一致
- ✅ 端口配置一致
- ✅ 环境变量命名一致

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-12-team-workflow-isolation.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**

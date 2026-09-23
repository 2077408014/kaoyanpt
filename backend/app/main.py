from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .core.database import engine, Base
from .core.config import UPLOAD_PATH
from .core.seed import run_seed
from .api import auth, mistakes, words, politics, recommendation, resources, ai, report, assistants, rag, supervision, study, ai_config, agent
from .services.collaboration_engine import init_collaboration_engine
from .services.ai_service import ai_service

Base.metadata.create_all(bind=engine)
run_seed()

init_collaboration_engine(ai_service)

app = FastAPI(title="考研复习平台", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=UPLOAD_PATH), name="uploads")

app.include_router(auth.router)
app.include_router(mistakes.router)
app.include_router(words.router)
app.include_router(politics.router)
app.include_router(recommendation.router)
app.include_router(resources.router)
app.include_router(ai.router)
app.include_router(report.router)
app.include_router(assistants.router)
app.include_router(rag.router)
app.include_router(supervision.router)
app.include_router(study.router)
app.include_router(ai_config.router)
app.include_router(agent.router)


@app.get("/")
async def root():
    return {"message": "考研复习平台 API"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}

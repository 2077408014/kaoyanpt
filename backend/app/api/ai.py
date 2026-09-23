from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..services.ai_service import ai_service
from ..services.llm_service import llm_service
from ..core.deps import get_current_user
from ..schemas.ai import AIChatRequest, AICommandRequest

router = APIRouter(prefix="/api/ai", tags=["AI问答"])


@router.post("/chat")
def chat(
    data: AIChatRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        result = ai_service.chat(db, current_user.id, data.message)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/command")
def command(
    data: AICommandRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        result = ai_service.command(db, current_user.id, data.command)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
def get_history(
    limit: int = Query(20, ge=1, le=100),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        result = ai_service.get_history(db, current_user.id, limit)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history")
def clear_history(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        ai_service.clear_history(db, current_user.id)
        return {"message": "聊天记录已清除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/local-status")
def get_local_model_status():
    try:
        status = ai_service.check_local_llm_status()
        return {"status": status}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.post("/recommend")
def recommend_questions(
    data: dict,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        question_text = data.get("question_text", "")
        subject = data.get("subject", "")
        knowledge_point = data.get("knowledge_point", "")

        user_config = ai_service._get_user_ai_config(db, current_user.id)

        if not user_config.get("api_key"):
            raise HTTPException(status_code=400, detail="请先在AI配置页面设置API Key")

        system_prompt = f"你是一个专业的考研{subject}出题专家，擅长根据题目生成同类练习题。"

        user_prompt = f"""请根据以下题目信息，生成3道同类练习题。

题目信息：
科目：{subject}
知识点：{knowledge_point}
原题内容：{question_text}

要求：
1. 生成的题目要与原题同类型、同知识点
2. 难度循序渐进
3. 每道题包含题目描述、正确答案和详细解析
4. 数学公式必须使用LaTeX格式，行内公式用$...$包裹，独立公式用$$...$$包裹
5. 输出格式为纯JSON数组，不要任何其他文字、解释或markdown标记
6. 每个元素包含：question（题目）、answer（答案）、analysis（解析）
7. 所有字段内容不能为空

只输出JSON，不要任何其他内容！"""

        schema_hint = '[{"question": "题目内容", "answer": "答案内容", "analysis": "解析内容"}]'

        parsed = llm_service.generate_json(
            user_message=user_prompt,
            ai_config=user_config,
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=1500,
            max_retries=1,
            schema_hint=schema_hint,
        )

        questions = []
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    q = item.get("question", "").strip()
                    a = item.get("answer", "").strip()
                    if q and a:
                        questions.append({
                            "question": q,
                            "answer": a,
                            "analysis": item.get("analysis", "").strip()
                        })
        elif isinstance(parsed, dict):
            q = parsed.get("question", "").strip()
            a = parsed.get("answer", "").strip()
            if q and a:
                questions.append({
                    "question": q,
                    "answer": a,
                    "analysis": parsed.get("analysis", "").strip()
                })

        return {"questions": questions}
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成推荐题目失败：{str(e)}")
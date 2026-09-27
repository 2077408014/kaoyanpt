"""教师 / 机构管理者 AI 助手接口（SSE 流式）。

事件协议（每行 data: JSON）：
- {"delta": "文本增量"}      正文流式增量
- {"action": {...}}          待确认动作（如创建教师账号卡片）
- {"error": "错误信息"}      调用失败
- {"done": true}             结束
"""
import json
from typing import Optional

import requests
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.database import get_db
from ..core.deps import require_teacher, require_institution_admin
from ..models.user import User
from ..models.ai_config import AIConfig
from ..models.ai_chat import AIChatHistory
from ..schemas.assistant import AssistantChatRequest
from ..services.llm_service import llm_service
from ..services import assistant_service as ctx

router = APIRouter(prefix="/api/assistant", tags=["assistant"])

# 只携带最近若干轮，控制 token
HISTORY_LIMIT = 10

# 聊天历史在 ai_chat_history 表中的 agent_name（与学生端 ai-qa 区分）
AGENT_TEACHER = "teacher-assistant"
AGENT_INSTITUTION = "institution-assistant"


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _server_config() -> dict:
    return {
        "api_key": settings.AI_API_KEY,
        "base_url": settings.AI_BASE_URL,
        "model": settings.AI_MODEL,
    }


def _resolve_ai_config(db: Session, user: User) -> dict:
    """优先使用用户在「AI 配置」页激活的配置，否则回退服务器默认配置。"""
    if user.active_ai_config_id:
        config = db.query(AIConfig).filter(
            AIConfig.id == user.active_ai_config_id,
            AIConfig.user_id == user.id,
        ).first()
        if config:
            return {
                "api_key": config.api_key,
                "base_url": config.base_url or settings.AI_BASE_URL,
                "model": config.model or settings.AI_MODEL,
            }
    return _server_config()


def _save_history(db: Session, user_id: int, agent_name: str,
                  msg_type: str, content: str) -> None:
    db.add(AIChatHistory(
        user_id=user_id, agent_name=agent_name,
        message_type=msg_type, content=content,
    ))
    db.commit()


def _parse_create_teacher(intent) -> Optional[dict]:
    """从意图识别结果提取创建教师动作；信息不全返回 None。"""
    if not isinstance(intent, dict) or intent.get("action") != "create_teacher":
        return None
    args = intent.get("args") or {}
    username = str(args.get("username", "")).strip()
    email = str(args.get("email", "")).strip()
    password = str(args.get("password", "")).strip()
    if len(username) < 3 or "@" not in email:
        return None
    if len(password) < 6:
        password = "123456"  # 缺省初始密码，卡片中可改
    return {
        "type": "create_teacher",
        "username": username,
        "email": email,
        "password": password,
    }


def _stream_completion(messages: list[dict], config: dict, db: Session,
                       user_id: int, agent_name: str):
    """直连 DeepSeek SSE，转译为统一事件；正常完成后落库聊天历史。"""
    question = messages[-1]["content"] if messages else ""

    def generate():
        if not config.get("api_key"):
            yield _sse({"error": "尚未配置 AI 服务，请点击右上角「AI配置」添加并启用配置"})
            return
        url = f"{config['base_url'].rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['api_key']}",
        }
        payload = {
            "model": config["model"],
            "messages": messages,
            "stream": True,
            "temperature": 0.6,
            "max_tokens": settings.AI_MAX_TOKENS,
        }
        answer_parts: list[str] = []
        completed = False
        try:
            with requests.post(
                url, json=payload, headers=headers,
                timeout=(10, settings.AI_TIMEOUT), stream=True,
            ) as resp:
                if resp.status_code != 200:
                    detail = resp.text[:300]
                    yield _sse({"error": f"AI 服务异常（HTTP {resp.status_code}）：{detail}"})
                    return
                for raw in resp.iter_lines():
                    if not raw:
                        continue
                    line = raw.decode("utf-8") if isinstance(raw, bytes) else raw
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"].get("content")
                    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                        continue
                    if delta:
                        answer_parts.append(delta)
                        yield _sse({"delta": delta})
                completed = True
        except requests.exceptions.Timeout:
            yield _sse({"error": "AI 响应超时，请稍后重试"})
        except requests.exceptions.ConnectionError:
            yield _sse({"error": "无法连接 AI 服务，请检查网络或服务器配置"})
        except Exception as e:  # noqa: BLE001
            yield _sse({"error": f"AI 服务调用失败：{e}"})
        if completed:
            answer = "".join(answer_parts).strip()
            if question and answer:
                _save_history(db, user_id, agent_name, "question", question)
                _save_history(db, user_id, agent_name, "answer", answer)
        yield _sse({"done": True})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _build_llm_messages(system_prompt: str, history: list[dict]) -> list[dict]:
    recent = history[-HISTORY_LIMIT:]
    return [{"role": "system", "content": system_prompt}, *recent]


def _action_response(action: dict):
    def generate():
        yield _sse({"action": action})
        yield _sse({"done": True})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


def _simple_event_response(event: dict, extra_headers: Optional[dict] = None):
    """单个事件 + done。注意事件内容必须是已求值的普通值，
    不能闭包引用 except 变量（其在 except 块结束后被清除）。"""
    def generate():
        yield _sse(event)
        yield _sse({"done": True})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", **(extra_headers or {})},
    )


@router.post("/teacher/chat")
async def teacher_chat(
    data: AssistantChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    context = ctx.build_teacher_context(db, current_user)
    system_prompt = ctx.TEACHER_SYSTEM_PROMPT.format(context=context)
    messages = _build_llm_messages(
        system_prompt, [{"role": m.role, "content": m.content} for m in data.messages]
    )
    config = _resolve_ai_config(db, current_user)
    return _stream_completion(messages, config, db, current_user.id, AGENT_TEACHER)


@router.post("/institution/chat")
async def institution_chat(
    data: AssistantChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_institution_admin),
):
    context = ctx.build_institution_context(db, current_user)
    if context is None:
        return _simple_event_response(
            {"error": "超级管理员未绑定具体机构，机构 AI 助手仅对机构管理者开放"}
        )

    config = _resolve_ai_config(db, current_user)

    # 先做一次意图识别：明确的"创建教师账号"直接返回确认卡片，不走正文生成
    latest = data.messages[-1].content
    action = None
    try:
        intent = llm_service.generate_json(
            latest, config,
            system_prompt=ctx.INTENT_SYSTEM_PROMPT,
            temperature=0.0, max_tokens=300,
        )
        action = _parse_create_teacher(intent)
    except ValueError as e:
        # 先取出字符串，避免闭包引用已被 Python 清除的 except 变量
        message = str(e)
        return _simple_event_response({"error": message})

    if action:
        # 落库：问题 + 动作摘要，保证历史与多轮上下文完整
        _save_history(db, current_user.id, AGENT_INSTITUTION, "question", latest)
        _save_history(
            db, current_user.id, AGENT_INSTITUTION, "answer",
            f"已向你发起创建教师账号的确认卡片（用户名：{action['username']}，邮箱：{action['email']}）。",
        )
        return _action_response(action)

    system_prompt = ctx.INSTITUTION_SYSTEM_PROMPT.format(context=context)
    messages = _build_llm_messages(
        system_prompt, [{"role": m.role, "content": m.content} for m in data.messages]
    )
    return _stream_completion(messages, config, db, current_user.id, AGENT_INSTITUTION)


# ---------- 聊天历史（效仿学生端「清除记录」） ----------

def _history(db: Session, user: User, agent_name: str, limit: int) -> list[dict]:
    # 按自增 id 排序：created_at 只有秒级精度，同事务多条可能并列导致乱序
    msgs = db.query(AIChatHistory).filter(
        AIChatHistory.user_id == user.id,
        AIChatHistory.agent_name == agent_name,
    ).order_by(AIChatHistory.id.desc()).limit(limit).all()
    msgs.reverse()
    return [{
        "id": m.id,
        "message_type": m.message_type,
        "content": m.content,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    } for m in msgs]


def _clear_history(db: Session, user: User, agent_name: str) -> dict:
    db.query(AIChatHistory).filter(
        AIChatHistory.user_id == user.id,
        AIChatHistory.agent_name == agent_name,
    ).delete()
    db.commit()
    return {"message": "历史已清除"}


@router.get("/teacher/history")
def teacher_history(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    return _history(db, current_user, AGENT_TEACHER, limit)


@router.delete("/teacher/history")
def teacher_clear_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_teacher),
):
    return _clear_history(db, current_user, AGENT_TEACHER)


@router.get("/institution/history")
def institution_history(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_institution_admin),
):
    return _history(db, current_user, AGENT_INSTITUTION, limit)


@router.delete("/institution/history")
def institution_clear_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_institution_admin),
):
    return _clear_history(db, current_user, AGENT_INSTITUTION)

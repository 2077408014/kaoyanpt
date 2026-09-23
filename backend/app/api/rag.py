from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse, FileResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session
import asyncio
import json
import os
from ..core.database import get_db
from ..services.knowledge_base_service import knowledge_base_service
from ..services.feature_agent_service import feature_agent_service
from ..core.deps import get_current_user, get_current_user_from_query

router = APIRouter(prefix="/api/rag", tags=["RAG"])

index_progress = {}


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    subject: str = Form("未分类"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    allowed_types = ["pdf", "png", "jpg", "jpeg", "doc", "docx", "txt"]
    file_ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ''

    if file_ext not in allowed_types:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {file_ext}")

    contents = await file.read()
    if len(contents) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小超过限制（最大50MB）")

    try:
        result = knowledge_base_service.add_document(db, current_user.id, contents, file.filename, subject=subject, index_now=False)
        return {
            "success": True,
            "message": "文档上传成功，可在文档列表中手动触发索引",
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/documents/{document_id}/index")
async def index_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    progress_key = f"{current_user.id}_{document_id}"
    import time

    if progress_key in index_progress and index_progress[progress_key]["status"] == "running":
        elapsed = time.time() - index_progress[progress_key].get("start_time", 0)
        if elapsed < 1800:
            raise HTTPException(status_code=400, detail="已有索引任务正在进行")
        else:
            del index_progress[progress_key]

    index_progress[progress_key] = {"progress": 0, "message": "准备开始", "status": "running", "start_time": time.time()}

    async def run_index():
        try:
            def progress_callback(progress: int, message: str):
                if progress_key not in index_progress or index_progress[progress_key]["status"] == "cancelled":
                    raise Exception("索引已取消")
                index_progress[progress_key] = {"progress": progress, "message": message, "status": "running"}

            # 在异步任务中创建新的数据库会话
            def run_index_sync():
                db_session = next(get_db())
                try:
                    return knowledge_base_service.index_document(
                        db_session, current_user.id, document_id, progress_callback
                    )
                finally:
                    db_session.close()

            success = await asyncio.to_thread(run_index_sync)

            if not success:
                index_progress[progress_key]["status"] = "failed"
                index_progress[progress_key]["message"] = "索引失败"
                return

            if progress_key in index_progress and index_progress[progress_key]["status"] == "cancelled":
                return

            index_progress[progress_key] = {"progress": 100, "message": "索引创建成功", "status": "completed"}
        except Exception as e:
            error_msg = str(e)
            print(f"Index task failed: {error_msg}")
            if "取消" in error_msg or "cancelled" in error_msg.lower():
                if progress_key in index_progress:
                    index_progress[progress_key] = {"progress": 0, "message": "用户已取消索引", "status": "cancelled"}
            elif progress_key in index_progress and index_progress[progress_key]["status"] != "cancelled":
                index_progress[progress_key] = {"progress": 0, "message": error_msg, "status": "failed"}

    asyncio.create_task(run_index())

    return {"success": True, "message": "索引任务已启动"}


@router.get("/documents/{document_id}/index/progress")
async def get_index_progress(
    document_id: int,
    current_user = Depends(get_current_user_from_query)
):
    progress_key = f"{current_user.id}_{document_id}"

    async def event_generator():
        while True:
            progress = index_progress.get(progress_key, {"progress": 0, "message": "等待中", "status": "waiting"})
            yield f"data: {json.dumps(progress)}\n\n"

            if progress["status"] in ["completed", "failed", "cancelled"]:
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/documents/{document_id}/index/cancel")
async def cancel_index(
    document_id: int,
    current_user = Depends(get_current_user)
):
    progress_key = f"{current_user.id}_{document_id}"
    if progress_key in index_progress:
        index_progress[progress_key]["status"] = "cancelled"
        index_progress[progress_key]["message"] = "用户已取消索引"
        return {"success": True, "message": "索引已取消"}
    return {"success": False, "message": "没有正在进行的索引任务"}


@router.post("/documents/{document_id}/index/reset")
async def reset_index_status(
    document_id: int,
    current_user = Depends(get_current_user)
):
    progress_key = f"{current_user.id}_{document_id}"
    if progress_key in index_progress:
        del index_progress[progress_key]
        return {"success": True, "message": "索引状态已重置"}
    return {"success": True, "message": "无需重置"}


@router.get("/documents")
async def get_documents(
    subject: str = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    documents = knowledge_base_service.get_documents(db, current_user.id, subject=subject)
    return {"documents": documents}


@router.get("/documents/{document_id}")
async def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    document = knowledge_base_service.get_document(db, current_user.id, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    return document


@router.get("/documents/{document_id}/download")
async def download_document(
    document_id: int,
    preview: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user_from_query)
):
    document = knowledge_base_service.get_document(db, current_user.id, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")

    storage_path = document.get("storage_path")
    if not storage_path or not os.path.exists(storage_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    filename = document.get("filename", "document")
    file_type = document.get("file_type", "").lower()

    if preview and file_type == "pdf":
        with open(storage_path, "rb") as f:
            content = f.read()
        headers = {
            "Content-Disposition": "inline",
            "Content-Length": str(len(content)),
            "Accept-Ranges": "bytes",
            "Cache-Control": "max-age=3600",
        }
        return Response(
            content,
            media_type="application/pdf",
            headers=headers
        )

    return FileResponse(
        storage_path,
        media_type="application/octet-stream",
        filename=filename
    )


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    success = knowledge_base_service.remove_document(db, current_user.id, document_id)
    if not success:
        raise HTTPException(status_code=404, detail="文档不存在")
    # 后台异步重建索引，不阻塞删除响应
    asyncio.create_task(
        asyncio.to_thread(knowledge_base_service.rebuild_index_async, current_user.id)
    )
    return {"success": True, "message": "删除成功"}


@router.get("/knowledge/status")
async def get_knowledge_status(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    return knowledge_base_service.get_status(db, current_user.id)


class RAGChatRequest(BaseModel):
    question: str
    top_k: int = 3
    threshold: float = 0.3
    subject: str = None
    only_knowledge_base: bool = False


@router.post("/chat")
async def rag_chat(
    body: RAGChatRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not body.question or not body.question.strip():
        raise HTTPException(status_code=400, detail="请输入问题")

    from ..services.rag_service import rag_service
    user_config = feature_agent_service._get_user_config(db, current_user.id)
    try:
        return rag_service.chat(
            user_id=current_user.id,
            question=body.question.strip(),
            top_k=body.top_k,
            threshold=body.threshold,
            ai_config=user_config,
            subject=body.subject,
            only_knowledge_base=body.only_knowledge_base
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/search")
async def rag_search(
    body: RAGChatRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not body.question or not body.question.strip():
        raise HTTPException(status_code=400, detail="请输入搜索词")

    from ..services.rag_service import rag_service
    return rag_service.search_only(current_user.id, body.question.strip(), body.top_k, body.threshold, subject=body.subject)


@router.post("/rebuild-index")
async def rebuild_index(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    asyncio.create_task(
        asyncio.to_thread(knowledge_base_service.rebuild_index_async, current_user.id)
    )
    return {"success": True, "message": "索引重建任务已启动，正在后台处理"}
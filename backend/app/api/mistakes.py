import os
import uuid
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
from ..core.database import get_db
from ..core.config import UPLOAD_PATH
from ..schemas.mistake import (
    MistakeCreate, MistakeUpdate, MistakeResponse,
    MistakeReviewCreate, MistakeReviewResponse,
    MistakeRecognizeRequest, MistakeRecognizeResponse,
    SimilarMistakeResponse
)
from ..services.mistake_service import mistake_service
from ..services.ocr_service import ocr_service
from ..core.deps import get_current_user
from ..models.user import User

router = APIRouter(prefix="/api/mistakes", tags=["mistakes"])

@router.post("", response_model=MistakeResponse)
async def create_mistake(
    data: MistakeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        mistake = mistake_service.create_mistake(db, current_user.id, data)
        return mistake
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("", response_model=list[MistakeResponse])
async def get_mistakes(
    subject: Optional[str] = Query(None),
    knowledge_point: Optional[str] = Query(None),
    error_type: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    mastery_level: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    filters = {k: v for k, v in locals().items() if v is not None and k != "db" and k != "current_user"}
    mistakes = mistake_service.get_mistakes(db, current_user.id, filters)
    return mistakes

@router.post("/upload")
async def upload_mistake_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="仅支持 JPG/PNG/WEBP 图片")

    mistakes_dir = UPLOAD_PATH / "mistakes"
    mistakes_dir.mkdir(parents=True, exist_ok=True)

    ext = file.filename.split(".")[-1] if file.filename else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = mistakes_dir / filename

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return {
        "image_path": f"mistakes/{filename}",
        "image_url": f"/uploads/mistakes/{filename}"
    }

@router.post("/recognize", response_model=MistakeRecognizeResponse)
async def recognize_mistake(
    data: MistakeRecognizeRequest,
    current_user: User = Depends(get_current_user)
):
    full_path = UPLOAD_PATH / data.image_path
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="图片不存在")

    result = await asyncio.to_thread(ocr_service.recognize, str(full_path))
    return result

@router.get("/review/today", response_model=list[MistakeResponse])
async def get_today_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    mistakes = mistake_service.get_today_reviews(db, current_user.id)
    return mistakes

@router.get("/{mistake_id}", response_model=MistakeResponse)
async def get_mistake(
    mistake_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    mistake = mistake_service.get_mistake_by_id(db, current_user.id, mistake_id)
    if not mistake:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="错题不存在")
    return mistake

@router.get("/{mistake_id}/similar", response_model=list[SimilarMistakeResponse])
async def get_similar_mistakes(
    mistake_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    results = mistake_service.get_similar_mistakes(db, current_user.id, mistake_id)
    return [
        SimilarMistakeResponse(
            id=item["mistake"].id,
            subject=item["mistake"].subject,
            knowledge_point=item["mistake"].knowledge_point,
            question_text=item["mistake"].question_text,
            difficulty=item["mistake"].difficulty,
            mastery_level=item["mistake"].mastery_level,
            similarity_score=item["similarity_score"]
        )
        for item in results
    ]

@router.put("/{mistake_id}", response_model=MistakeResponse)
async def update_mistake(
    mistake_id: int,
    data: MistakeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    mistake = mistake_service.update_mistake(db, current_user.id, mistake_id, data)
    if not mistake:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="错题不存在")
    return mistake

@router.delete("/{mistake_id}")
async def delete_mistake(
    mistake_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    success = mistake_service.delete_mistake(db, current_user.id, mistake_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="错题不存在")
    return {"message": "删除成功"}

@router.post("/{mistake_id}/review", response_model=MistakeReviewResponse)
async def review_mistake(
    mistake_id: int,
    data: MistakeReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        review = mistake_service.review_mistake(db, current_user.id, mistake_id, data)
        return review
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

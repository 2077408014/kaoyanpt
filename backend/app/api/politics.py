import os
import uuid
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
from ..core.database import get_db
from ..core.config import UPLOAD_PATH
from ..schemas.politics import (
    PoliticsRecitationCreate, PoliticsRecitationUpdate, PoliticsRecitationResponse,
    PoliticsRecognizeRequest, PoliticsRecognizeResponse, PoliticsReviewRequest,
    RecitationReminderCreate, RecitationReminderUpdate, RecitationReminderResponse
)
from ..services.politics_service import politics_service
from ..core.deps import get_current_user
from ..models.user import User

router = APIRouter(prefix="/api/politics", tags=["politics"])


@router.get("")
async def get_recitations(
    category: Optional[str] = Query(None),
    mastery_level: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    recitations = politics_service.get_recitations(db, current_user.id, category, mastery_level)
    return [{
        "id": r.id,
        "user_id": r.user_id,
        "title": r.title,
        "category": r.category,
        "content": r.content,
        "image_path": r.image_path,
        "mastery_level": r.mastery_level,
        "review_count": r.review_count,
        "next_review_date": r.next_review_date.isoformat() if r.next_review_date else None,
        "last_review_date": r.last_review_date.isoformat() if r.last_review_date else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None
    } for r in recitations]


@router.get("/{recitation_id}")
async def get_recitation(
    recitation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    recitation = politics_service.get_recitation(db, current_user.id, recitation_id)
    if not recitation:
        raise HTTPException(status_code=404, detail="背诵内容不存在")
    return {
        "id": recitation.id,
        "user_id": recitation.user_id,
        "title": recitation.title,
        "category": recitation.category,
        "content": recitation.content,
        "image_path": recitation.image_path,
        "mastery_level": recitation.mastery_level,
        "review_count": recitation.review_count,
        "next_review_date": recitation.next_review_date.isoformat() if recitation.next_review_date else None,
        "last_review_date": recitation.last_review_date.isoformat() if recitation.last_review_date else None,
        "created_at": recitation.created_at.isoformat() if recitation.created_at else None,
        "updated_at": recitation.updated_at.isoformat() if recitation.updated_at else None
    }


@router.post("")
async def create_recitation(
    data: PoliticsRecitationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    recitation = politics_service.create_recitation(db, current_user.id, data)
    return {
        "id": recitation.id,
        "user_id": recitation.user_id,
        "title": recitation.title,
        "category": recitation.category,
        "content": recitation.content,
        "image_path": recitation.image_path,
        "mastery_level": recitation.mastery_level,
        "review_count": recitation.review_count,
        "next_review_date": recitation.next_review_date.isoformat() if recitation.next_review_date else None,
        "last_review_date": recitation.last_review_date.isoformat() if recitation.last_review_date else None,
        "created_at": recitation.created_at.isoformat() if recitation.created_at else None,
        "updated_at": recitation.updated_at.isoformat() if recitation.updated_at else None
    }


@router.put("/{recitation_id}")
async def update_recitation(
    recitation_id: int,
    data: PoliticsRecitationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = politics_service.update_recitation(db, current_user.id, recitation_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="背诵内容不存在")
    return {
        "id": result.id,
        "user_id": result.user_id,
        "title": result.title,
        "category": result.category,
        "content": result.content,
        "image_path": result.image_path,
        "mastery_level": result.mastery_level,
        "review_count": result.review_count,
        "next_review_date": result.next_review_date.isoformat() if result.next_review_date else None,
        "last_review_date": result.last_review_date.isoformat() if result.last_review_date else None,
        "created_at": result.created_at.isoformat() if result.created_at else None,
        "updated_at": result.updated_at.isoformat() if result.updated_at else None
    }


@router.delete("/{recitation_id}")
async def delete_recitation(
    recitation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    success = politics_service.delete_recitation(db, current_user.id, recitation_id)
    if not success:
        raise HTTPException(status_code=404, detail="背诵内容不存在")
    return {"message": "删除成功"}


@router.post("/{recitation_id}/review")
async def review_recitation(
    recitation_id: int,
    data: PoliticsReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    recitation = politics_service.review_recitation(db, current_user.id, recitation_id, data.result)
    if not recitation:
        raise HTTPException(status_code=404, detail="背诵内容不存在")
    return {
        "id": recitation.id,
        "mastery_level": recitation.mastery_level,
        "next_review_date": recitation.next_review_date.isoformat() if recitation.next_review_date else None,
        "review_count": recitation.review_count
    }


@router.post("/upload")
async def upload_politics_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="仅支持 JPG/PNG/WEBP 图片")

    politics_dir = UPLOAD_PATH / "politics"
    politics_dir.mkdir(parents=True, exist_ok=True)

    ext = file.filename.split(".")[-1] if file.filename else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = politics_dir / filename

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    return {
        "image_path": f"politics/{filename}",
        "image_url": f"/uploads/politics/{filename}"
    }


@router.post("/recognize")
async def recognize_politics_image(
    data: PoliticsRecognizeRequest,
    current_user: User = Depends(get_current_user)
):
    print(f"[识别请求] 用户ID: {current_user.id}, 图片路径: {data.image_path}")
    result = await asyncio.to_thread(politics_service.recognize_image, data.image_path)
    print(f"[识别结果] content: {result['content'][:50] if result['content'] else '空'}, confidence: {result['confidence']}")
    return result


@router.get("/reminders")
async def get_reminders(
    reminder_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    reminders = politics_service.get_reminders(db, current_user.id, reminder_type)
    return [{
        "id": r.id,
        "user_id": r.user_id,
        "reminder_type": r.reminder_type,
        "reminder_time": r.reminder_time,
        "frequency": r.frequency,
        "enabled": r.enabled,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None
    } for r in reminders]


@router.post("/reminders")
async def create_reminder(
    data: RecitationReminderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    reminder = politics_service.create_reminder(db, current_user.id, data)
    return {
        "id": reminder.id,
        "user_id": reminder.user_id,
        "reminder_type": reminder.reminder_type,
        "reminder_time": reminder.reminder_time,
        "frequency": reminder.frequency,
        "enabled": reminder.enabled,
        "created_at": reminder.created_at.isoformat() if reminder.created_at else None,
        "updated_at": reminder.updated_at.isoformat() if reminder.updated_at else None
    }


@router.put("/reminders/{reminder_id}")
async def update_reminder(
    reminder_id: int,
    data: RecitationReminderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = politics_service.update_reminder(db, current_user.id, reminder_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="提醒不存在")
    return {
        "id": result.id,
        "user_id": result.user_id,
        "reminder_type": result.reminder_type,
        "reminder_time": result.reminder_time,
        "frequency": result.frequency,
        "enabled": result.enabled,
        "created_at": result.created_at.isoformat() if result.created_at else None,
        "updated_at": result.updated_at.isoformat() if result.updated_at else None
    }


@router.delete("/reminders/{reminder_id}")
async def delete_reminder(
    reminder_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    success = politics_service.delete_reminder(db, current_user.id, reminder_id)
    if not success:
        raise HTTPException(status_code=404, detail="提醒不存在")
    return {"message": "删除成功"}

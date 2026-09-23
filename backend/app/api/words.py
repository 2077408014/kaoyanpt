from fastapi import APIRouter, Depends, Query, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from ..core.database import get_db
from ..schemas.word import WordResponse, WordStudyRequest, StudyPlanRequest, StudySessionData
from ..services.word_service import word_service
from ..core.deps import get_current_user
from ..models.user import User

router = APIRouter(prefix="/api/words", tags=["words"])


@router.get("/stats")
async def get_word_stats(
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return word_service.get_word_stats(db, current_user.id, category)


@router.get("/today")
async def get_today_words(
    count: int = Query(20, ge=5, le=100),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = word_service.get_today_words(db, current_user.id, count, category)
    return {
        "review": [
            {
                "id": word.id,
                "word": word.word,
                "phonetic": word.phonetic,
                "meaning": word.meaning,
                "example_sentence": word.example_sentence,
                "difficulty": word.difficulty,
                "frequency": word.frequency,
                "exam_requirement": word.exam_requirement,
                "category": word.category,
                "type": "review"
            }
            for word in result["review"]
        ],
        "new": [
            {
                "id": word.id,
                "word": word.word,
                "phonetic": word.phonetic,
                "meaning": word.meaning,
                "example_sentence": word.example_sentence,
                "difficulty": word.difficulty,
                "frequency": word.frequency,
                "exam_requirement": word.exam_requirement,
                "category": word.category,
                "type": "new"
            }
            for word in result["new"]
        ],
        "review_count": result["review_count"],
        "new_count": len(result["new"]),
        "total_today": result["total_today"]
    }


@router.get("/daily-review")
async def get_daily_review_words(
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    words = word_service.get_daily_review_words(db, current_user.id, category)
    return {
        "words": [
            {
                "id": word.id,
                "word": word.word,
                "phonetic": word.phonetic,
                "meaning": word.meaning,
                "example_sentence": word.example_sentence,
                "exam_requirement": word.exam_requirement,
                "category": word.category,
                "type": "review"
            }
            for word in words
        ],
        "count": len(words)
    }


@router.get("/review-words")
async def get_review_words_by_range(
    time_range: str = Query("today", description="复习时间范围: today(今日), day(近一日), week(近一周), month(近一月), recommended(系统推荐)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    words = word_service.get_review_words_by_range(db, current_user.id, time_range)
    return {
        "words": [
            {
                "id": word.id,
                "word": word.word,
                "phonetic": word.phonetic,
                "meaning": word.meaning,
                "example_sentence": word.example_sentence,
                "exam_requirement": word.exam_requirement,
                "category": word.category,
                "type": "review"
            }
            for word in words
        ],
        "count": len(words)
    }


@router.get("/categories")
async def get_word_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return {"categories": word_service.get_word_categories(db, current_user.id)}


@router.get("/review")
async def get_review_words(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    items = word_service.get_review_words(db, current_user.id)
    return [
        {
            "id": item.id,
            "word_id": item.word_id,
            "word": item.word.word if hasattr(item, 'word') else "",
            "mastery_level": item.mastery_level,
            "next_review_date": item.next_review_date.isoformat() if item.next_review_date else None,
            "review_count": item.review_count,
            "correct_count": item.correct_count,
            "last_study_date": item.last_study_date.isoformat() if item.last_study_date else None,
            "first_study_date": item.first_study_date.isoformat() if item.first_study_date else None,
            "last_rating": item.last_rating,
            "srs_stage": item.srs_stage
        }
        for item in items
    ]


@router.get("/list")
async def get_word_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=10, le=100),
    mastery_level: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = word_service.get_word_list(db, current_user.id, page, page_size, mastery_level, keyword, category)

    items = [
        {
            "id": item["id"],
            "word_id": item["word_id"],
            "word": item["word"],
            "phonetic": item["phonetic"],
            "meaning": item["meaning"],
            "example_sentence": item["example_sentence"],
            "mastery_level": item["mastery_level"],
            "next_review_date": item["next_review_date"].isoformat() if item["next_review_date"] else None,
            "review_count": item["review_count"],
            "correct_count": item["correct_count"],
            "last_study_date": item["last_study_date"].isoformat() if item["last_study_date"] else None,
            "first_study_date": item["first_study_date"].isoformat() if item["first_study_date"] else None,
            "last_rating": item["last_rating"],
            "srs_stage": item["srs_stage"]
        }
        for item in result["items"]
    ]

    return {"total": result["total"], "items": items}


@router.post("/study")
async def study_word(
    data: WordStudyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = word_service.study_word(db, current_user.id, data)
    return {
        "id": result.id,
        "mastery_level": result.mastery_level,
        "next_review_date": result.next_review_date.isoformat() if result.next_review_date else None,
        "review_count": result.review_count,
        "correct_count": result.correct_count,
        "last_rating": result.last_rating,
        "srs_stage": result.srs_stage
    }


@router.get("/plan")
async def get_study_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return word_service.get_study_plan(db, current_user.id)


@router.post("/plan")
async def save_study_plan(
    data: StudyPlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return word_service.save_study_plan(db, current_user.id, data)


@router.get("/session")
async def get_study_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = word_service.get_study_session(db, current_user.id)
    return session or {}


@router.post("/session")
async def save_study_session(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return word_service.save_study_session(db, current_user.id, data)


@router.delete("/session")
async def clear_study_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    word_service.clear_study_session(db, current_user.id)
    return {"success": True}


@router.post("/upload-wordbook")
async def upload_wordbook(
    file: UploadFile = File(...),
    category: str = Form("我的词书"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="未选择文件")

    if file.size and file.size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小超过限制（最大50MB）")

    try:
        contents = await file.read()
        result = word_service.upload_wordbook(db, current_user.id, contents, file.filename, category)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("message", "词书导入失败"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"词书上传失败: {str(e)}")
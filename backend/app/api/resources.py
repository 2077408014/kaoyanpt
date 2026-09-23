from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..services.resource_service import resource_service
from ..core.deps import get_current_user

router = APIRouter(prefix="/api/resources", tags=["资料管理"])


@router.post("/upload")
async def upload_resource(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        result = resource_service.upload_resource(db, current_user.id, file.file, file.filename)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
def get_resources(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        result = resource_service.get_resources(db, current_user.id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{id}")
def get_resource(id: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        result = resource_service.get_resource(db, current_user.id, id)
        if not result:
            raise HTTPException(status_code=404, detail="资源不存在")
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{id}")
def delete_resource(id: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        success = resource_service.delete_resource(db, current_user.id, id)
        if not success:
            raise HTTPException(status_code=404, detail="资源不存在")
        return {"message": "删除成功"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
def search_resources(
    query: str = Query(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        result = resource_service.search_resources(db, current_user.id, query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/qa")
def resource_qa(
    resource_id: int,
    question: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        result = resource_service.resource_qa(db, current_user.id, resource_id, question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
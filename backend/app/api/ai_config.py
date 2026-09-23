from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..services.ai_config_service import ai_config_service
from ..schemas.ai_config import AIConfigCreate, AIConfigUpdate, AIConfigResponse, AIConfigListItem
from ..core.deps import get_current_user


class SwitchConfigRequest(BaseModel):
    config_id: Optional[int] = None

router = APIRouter(prefix="/api/ai-configs", tags=["AI配置"])


@router.get("", response_model=list[AIConfigListItem])
def list_configs(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的所有 AI 配置列表。"""
    configs = ai_config_service.get_configs(db, current_user.id)
    return configs


@router.get("/{config_id}", response_model=AIConfigResponse)
def get_config(
    config_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取单条 AI 配置详情。"""
    config = ai_config_service.get_config(db, current_user.id, config_id)
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    return config


@router.post("", response_model=AIConfigResponse)
def create_config(
    data: AIConfigCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """创建新的 AI 配置。"""
    try:
        config = ai_config_service.create_config(db, current_user.id, data)
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建配置失败: {e}")


@router.put("/{config_id}", response_model=AIConfigResponse)
def update_config(
    config_id: int,
    data: AIConfigUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新 AI 配置。"""
    config = ai_config_service.update_config(db, current_user.id, config_id, data)
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    return config


@router.delete("/{config_id}")
def delete_config(
    config_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除 AI 配置。"""
    deleted = ai_config_service.delete_config(db, current_user.id, config_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="配置不存在")
    # 如果删除的是当前激活的配置，清空激活状态
    if current_user.active_ai_config_id == config_id:
        current_user.active_ai_config_id = None
        db.commit()
    return {"success": True, "id": config_id}


@router.post("/switch")
def switch_config(
    request: SwitchConfigRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """切换当前激活的 AI 配置。config_id 为 null 表示取消激活（回退到旧配置或默认）。"""
    if request.config_id is not None:
        config = ai_config_service.get_config(db, current_user.id, request.config_id)
        if not config:
            raise HTTPException(status_code=404, detail="配置不存在")
    current_user.active_ai_config_id = request.config_id
    db.commit()
    db.refresh(current_user)
    return {"success": True, "active_ai_config_id": request.config_id}
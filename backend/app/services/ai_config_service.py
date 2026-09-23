from typing import Optional

from sqlalchemy.orm import Session

from ..models.ai_config import AIConfig
from ..schemas.ai_config import AIConfigCreate, AIConfigUpdate


class AIConfigService:
    def get_configs(self, db: Session, user_id: int) -> list:
        configs = db.query(AIConfig).filter(
            AIConfig.user_id == user_id
        ).order_by(AIConfig.created_at.desc()).all()
        return configs

    def get_config(self, db: Session, user_id: int, config_id: int) -> Optional[AIConfig]:
        return db.query(AIConfig).filter(
            AIConfig.id == config_id,
            AIConfig.user_id == user_id
        ).first()

    def create_config(self, db: Session, user_id: int, data: AIConfigCreate) -> AIConfig:
        config = AIConfig(
            user_id=user_id,
            name=data.name,
            provider=data.provider,
            api_key=data.api_key,
            base_url=data.base_url,
            model=data.model,
        )
        db.add(config)
        db.commit()
        db.refresh(config)
        return config

    def update_config(self, db: Session, user_id: int, config_id: int, data: AIConfigUpdate) -> Optional[AIConfig]:
        config = self.get_config(db, user_id, config_id)
        if not config:
            return None

        if data.name is not None:
            config.name = data.name
        if data.provider is not None:
            config.provider = data.provider
        if data.api_key is not None:
            config.api_key = data.api_key
        if data.base_url is not None:
            config.base_url = data.base_url
        if data.model is not None:
            config.model = data.model

        db.commit()
        db.refresh(config)
        return config

    def delete_config(self, db: Session, user_id: int, config_id: int) -> bool:
        config = self.get_config(db, user_id, config_id)
        if not config:
            return False
        from ..models.user import User
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.active_ai_config_id == config_id:
            user.active_ai_config_id = None
        db.delete(config)
        db.commit()
        return True


ai_config_service = AIConfigService()
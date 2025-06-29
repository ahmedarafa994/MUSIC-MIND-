from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta
import uuid

from app.models.api_key import APIKey
from app.schemas.api_key import APIKeyCreate, APIKeyUpdate
from app.crud.base import CRUDBase
import logging

logger = logging.getLogger(__name__)

class CRUDAPIKey(CRUDBase[APIKey, APIKeyCreate, APIKeyUpdate]):
    def create_with_user(
        self,
        db: Session,
        *,
        obj_in: APIKeyCreate,
        user_id: str
    ) -> tuple[APIKey, str]:
        """Create API key with user association"""
        api_key, key = APIKey.create_api_key(
            user_id=user_id,
            name=obj_in.name,
            scopes=obj_in.scopes,
            expires_days=obj_in.expires_days
        )
        
        db.add(api_key)
        db.commit()
        db.refresh(api_key)
        return api_key, key

    def get_by_user(
        self,
        db: Session,
        *,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[APIKey]:
        """Get API keys by user"""
        return db.query(APIKey).filter(
            APIKey.user_id == user_id
        ).offset(skip).limit(limit).all()

    def verify_key(self, db: Session, *, key: str) -> Optional[APIKey]:
        """Verify API key and return the key object"""
        import hashlib
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        
        api_key = db.query(APIKey).filter(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True
        ).first()
        
        if api_key and api_key.is_valid():
            return api_key
        return None

api_key_crud = CRUDAPIKey(APIKey)
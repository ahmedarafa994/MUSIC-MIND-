from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from datetime import datetime, timedelta
import uuid
import hashlib

from app.models.api_key import APIKey
from app.schemas.api_key import APIKeyCreate, APIKeyUpdate # Assuming APIKeyUpdate schema exists
from app.crud.base import CRUDBase
import structlog

logger = structlog.get_logger(__name__)

class CRUDAPIKey(CRUDBase[APIKey, APIKeyCreate, APIKeyUpdate]):
    async def create_with_user(
        self,
        db: AsyncSession,
        *,
        obj_in: APIKeyCreate,
        user_id: uuid.UUID,
        created_from_ip: Optional[str] = None
    ) -> Tuple[APIKey, str]:
        """Create API key for a user and return the key object and the raw key string."""
        plain_key, key_hash = APIKey.generate_key()
        key_prefix = plain_key[:8] # Standard prefix length

        expires_at = None
        if obj_in.expires_days:
            expires_at = datetime.utcnow() + timedelta(days=obj_in.expires_days)

        db_obj = APIKey(
            user_id=user_id,
            name=obj_in.name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            scopes=obj_in.scopes,
            expires_at=expires_at,
            created_from_ip=created_from_ip,
            # rate_limit_per_minute, rate_limit_per_hour, etc. can be set from obj_in if added to schema
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        logger.info("API Key created", api_key_id=db_obj.id, user_id=user_id, name=obj_in.name)
        return db_obj, plain_key # Return the plain key only once upon creation

    async def get_by_user(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[APIKey]:
        """Get API keys by user."""
        stmt = select(APIKey).filter(APIKey.user_id == user_id).order_by(desc(APIKey.created_at)).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_key_prefix(self, db: AsyncSession, *, key_prefix: str) -> Optional[APIKey]:
        """Get API key by its prefix (for identification, not authentication)."""
        stmt = select(APIKey).filter(APIKey.key_prefix == key_prefix)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_by_key_hash(self, db: AsyncSession, *, key_hash: str) -> Optional[APIKey]:
        """Get API key by its hash (used during authentication)."""
        stmt = select(APIKey).filter(APIKey.key_hash == key_hash)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def authenticate_api_key(self, db: AsyncSession, *, plain_key: str) -> Optional[APIKey]:
        """Authenticate an API key string."""
        # It's better to hash the plain_key here and query by key_hash
        # However, if the key itself is stored (not recommended), then this would be different.
        # Assuming we only store key_hash:
        key_hash_to_check = hashlib.sha256(plain_key.encode()).hexdigest()
        api_key = await self.get_by_key_hash(db, key_hash=key_hash_to_check)

        if not api_key:
            logger.debug("API key not found by hash during authentication attempt")
            return None
        if not api_key.is_valid(): # Checks is_active and expiry
            logger.warning("Invalid or expired API key used for authentication", api_key_id=api_key.id)
            return None

        return api_key

    async def update_key_activity(self, db: AsyncSession, *, api_key: APIKey, is_active: bool) -> APIKey:
        """Activate or deactivate an API key."""
        api_key.is_active = is_active
        api_key.updated_at = datetime.utcnow()
        db.add(api_key)
        await db.commit()
        await db.refresh(api_key)
        logger.info("API Key activity updated", api_key_id=api_key.id, is_active=is_active)
        return api_key

    async def record_usage(
        self,
        db: AsyncSession,
        *,
        api_key: APIKey,
        ip_address: Optional[str] = None
    ) -> APIKey:
        """Record usage of an API key."""
        api_key.usage_count = (api_key.usage_count or 0) + 1
        api_key.last_used_at = datetime.utcnow()
        if ip_address:
            api_key.last_used_ip = ip_address
        db.add(api_key)
        await db.commit()
        await db.refresh(api_key)
        # logger.debug("API Key usage recorded", api_key_id=api_key.id) # Can be too verbose
        return api_key

    async def delete_by_user(self, db: AsyncSession, *, user_id: uuid.UUID, key_id: uuid.UUID) -> Optional[APIKey]:
        """Delete an API key belonging to a specific user."""
        stmt = select(APIKey).filter(and_(APIKey.id == key_id, APIKey.user_id == user_id))
        result = await db.execute(stmt)
        api_key = result.scalars().first()
        if api_key:
            await db.delete(api_key)
            await db.commit()
            logger.info("API Key deleted", api_key_id=key_id, user_id=user_id)
            return api_key
        logger.warning("API Key not found for deletion or user mismatch", api_key_id=key_id, user_id=user_id)
        return None

    async def get_expired_keys(self, db: AsyncSession) -> List[APIKey]:
        """Get all API keys that have expired."""
        stmt = select(APIKey).filter(
            and_(
                APIKey.expires_at.isnot(None),
                APIKey.expires_at < datetime.utcnow(),
                APIKey.is_active == True # Only care about active keys that are now expired
            )
        )
        result = await db.execute(stmt)
        return result.scalars().all()

    async def deactivate_expired_keys(self, db: AsyncSession) -> int:
        """Deactivate all expired API keys and return the count of deactivated keys."""
        expired_keys = await self.get_expired_keys(db)
        count = 0
        for key in expired_keys:
            key.is_active = False
            key.updated_at = datetime.utcnow()
            db.add(key)
            count += 1
        if count > 0:
            await db.commit()
            logger.info(f"Deactivated {count} expired API keys.")
        return count

api_key = CRUDAPIKey(APIKey)

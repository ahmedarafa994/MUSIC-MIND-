from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, update as sqlalchemy_update
from datetime import datetime, timedelta
import uuid

from app.models.user import User
from app.models.audio_file import AudioFile
from app.models.agent_session import AgentSession
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password # Assuming these are synchronous
from app.crud.base import CRUDBase
import structlog

logger = structlog.get_logger(__name__)

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        """Get user by email"""
        stmt = select(User).filter(User.email == email)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def get_by_username(self, db: AsyncSession, *, username: str) -> Optional[User]:
        """Get user by username"""
        stmt = select(User).filter(User.username == username)
        result = await db.execute(stmt)
        return result.scalars().first()

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        """Create new user"""
        hashed_password = get_password_hash(obj_in.password)
        db_obj = User(
            email=obj_in.email,
            username=obj_in.username,
            full_name=obj_in.full_name,
            hashed_password=hashed_password,
            # Initialize other fields from UserBase or defaults
            bio=obj_in.bio,
            phone_number=obj_in.phone_number,
            country=obj_in.country,
            timezone=obj_in.timezone,
            is_active=True, # Default to active, can be changed by verification logic
            is_verified=False, # Default to not verified
            # Set initial API limits based on default tier, or handle in a service layer
            api_usage_limit=User().get_subscription_limits().get('api_calls', 100)
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        logger.info("User created", user_id=db_obj.id, email=db_obj.email)
        return db_obj

    async def authenticate(self, db: AsyncSession, *, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = await self.get_by_email(db, email=email)
        if not user:
            logger.debug("Authentication failed: User not found", email=email)
            return None

        # Check if account is locked before verifying password
        if user.is_account_locked():
            logger.warning("Authentication failed: Account locked", email=email)
            # Optionally, you might want to inform the user how long they are locked out.
            # This could be done by raising an HTTPException with appropriate detail.
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account locked. Try again after {user.locked_until.isoformat()} UTC."
            )

        if not verify_password(password, user.hashed_password):
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= 5:
                 user.lock_account()
            db.add(user)
            await db.commit()
            logger.debug("Authentication failed: Incorrect password", email=email)
            return None

        # Reset failed attempts on successful login
        if user.failed_login_attempts > 0 or user.locked_until:
            user.unlock_account()
            db.add(user)
            await db.commit()
            await db.refresh(user) # Refresh to get updated state

        return user

    async def update_last_login(self, db: AsyncSession, *, user_id: uuid.UUID, ip_address: Optional[str] = None) -> Optional[User]:
        """Update user's last login timestamp and IP."""
        user = await self.get(db, id=user_id)
        if user:
            user.last_login = datetime.utcnow()
            # user.login_count = (user.login_count or 0) + 1 # Add if User model has login_count
            # if ip_address:
            #     user.last_login_ip = ip_address # Add if User model has last_login_ip
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.debug("User last login updated", user_id=user_id)
            return user
        return None

    async def is_active(self, user: User) -> bool:
        """Check if user is active"""
        return user.is_active

    async def is_verified(self, user: User) -> bool:
        """Check if user is verified"""
        return user.is_verified

    async def verify_user(self, db: AsyncSession, *, user: User) -> User:
        """Verify user account"""
        user.is_verified = True
        # user.verified_at = datetime.utcnow() # Add if User model has verified_at
        user.updated_at = datetime.utcnow()
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info("User account verified", user_id=user.id)
        return user

    async def deactivate_user(self, db: AsyncSession, *, user: User) -> User:
        """Deactivate user account"""
        user.is_active = False
        user.updated_at = datetime.utcnow()
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info("User account deactivated", user_id=user.id)
        return user

    async def activate_user(self, db: AsyncSession, *, user: User) -> User:
        """Activate user account"""
        user.is_active = True
        user.updated_at = datetime.utcnow()
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info("User account activated", user_id=user.id)
        return user

    async def update_password(self, db: AsyncSession, *, user: User, new_password: str) -> User:
        """Update user password"""
        user.hashed_password = get_password_hash(new_password)
        # user.password_changed_at = datetime.utcnow() # Add if User model has password_changed_at
        user.updated_at = datetime.utcnow()
        user.failed_login_attempts = 0 # Reset failed attempts on password change
        user.locked_until = None # Unlock account on password change
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info("User password updated", user_id=user.id)
        return user

    async def increment_api_usage(self, db: AsyncSession, *, user_id: uuid.UUID, cost: float = 0.0, count: int = 1) -> Optional[User]:
        """Increment user's API usage count and associate cost."""
        user = await self.get(db, id=user_id)
        if user:
            user.api_usage_count = (user.api_usage_count or 0) + count
            # user.total_api_cost = (user.total_api_cost or 0) + cost # Add if User model has total_api_cost

            if user.api_usage_reset_date and datetime.utcnow() >= user.api_usage_reset_date:
                user.reset_api_usage()

            db.add(user)
            await db.commit()
            await db.refresh(user)
            return user
        return None

    async def update_subscription(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        tier: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[User]:
        """Update user's subscription tier and API limits."""
        user = await self.get(db, id=user_id)
        if user:
            user.subscription_tier = tier
            if start_date:
                user.subscription_start_date = start_date
            if end_date:
                user.subscription_end_date = end_date

            new_limits = user.get_subscription_limits()
            user.api_usage_limit = new_limits.get('api_calls', 100)
            # user.max_file_size_mb = new_limits.get('file_size_mb', 10)
            # user.max_storage_gb = new_limits.get('storage_gb', 1)

            user.updated_at = datetime.utcnow()
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info("User subscription updated", user_id=user_id, new_tier=tier)
            return user
        return None

    async def search_users(self, db: AsyncSession, *, query: str, skip: int = 0, limit: int = 100) -> List[User]:
        """Search users by username, email, or full name (case-insensitive)."""
        search_filter = or_(
            User.username.ilike(f"%{query}%"),
            User.email.ilike(f"%{query}%"),
            User.full_name.ilike(f"%{query}%")
        )
        stmt = select(User).filter(search_filter).order_by(User.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_user_stats(self, db: AsyncSession, *, user_id: uuid.UUID) -> Dict[str, Any]:
        """Get user statistics (file counts, session counts, costs)."""
        user = await self.get(db, id=user_id)
        if not user:
            # Consider raising HTTPException(404) or returning specific error structure
            logger.warning("User not found for stats", user_id=user_id)
            return {"error": "User not found"}

        file_stmt = select(
            func.count(AudioFile.id),
            func.sum(AudioFile.file_size),
            func.sum(AudioFile.duration)
        ).filter(AudioFile.user_id == user_id)
        file_res = await db.execute(file_stmt)
        total_files, total_size_bytes, total_duration_seconds = file_res.one_or_none() or (0,0,0)

        session_stmt = select(
            func.count(AgentSession.id),
            func.sum(AgentSession.total_cost),
            func.sum(AgentSession.total_execution_time)
        ).filter(AgentSession.user_id == user_id)
        session_res = await db.execute(session_stmt)
        total_sessions, total_cost, total_processing_time = session_res.one_or_none() or (0,0,0)

        return {
            "user_id": str(user.id),
            "total_files": total_files or 0,
            "storage_used_mb": round((total_size_bytes or 0) / (1024 * 1024), 2),
            "total_audio_duration_minutes": round((total_duration_seconds or 0) / 60, 2),
            "total_sessions": total_sessions or 0,
            "total_cost": float(total_cost or 0.0),
            "total_processing_time_seconds": float(total_processing_time or 0.0),
            "api_calls_this_month": user.api_usage_count or 0,
            "api_usage_limit": user.api_usage_limit,
            "subscription_tier": user.subscription_tier,
            "account_created_at": user.created_at,
            "last_login": user.last_login,
        }

    async def count(self, db: AsyncSession) -> int:
        """Count total users."""
        stmt = select(func.count()).select_from(User)
        result = await db.execute(stmt)
        return result.scalar_one()

user = CRUDUser(User)

# Need to import status for HTTPException if used within this file
from fastapi import HTTPException, status

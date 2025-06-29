from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta
import uuid

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password
from app.crud.base import CRUDBase
import structlog

logger = structlog.get_logger()

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def get_by_email(self, db: Session, *, email: str) -> Optional[User]:
        """Get user by email"""
        return db.query(User).filter(User.email == email).first()

    def get_by_username(self, db: Session, *, username: str) -> Optional[User]:
        """Get user by username"""
        return db.query(User).filter(User.username == username).first()

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        """Create new user"""
        db_obj = User(
            email=obj_in.email,
            username=obj_in.username,
            full_name=obj_in.full_name,
            bio=obj_in.bio,
            phone_number=obj_in.phone_number,
            country=obj_in.country,
            timezone=obj_in.timezone,
        )
        db_obj.set_password(obj_in.password)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def authenticate(self, db: Session, *, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        user = self.get_by_email(db, email=email)
        if not user:
            return None
        if not user.verify_password(password):
            return None
        return user

    def is_active(self, user: User) -> bool:
        """Check if user is active"""
        return user.is_active

    def is_verified(self, user: User) -> bool:
        """Check if user is verified"""
        return user.is_verified

    def verify_user(self, db: Session, *, user: User) -> User:
        """Verify user account"""
        user.is_verified = True
        user.updated_at = datetime.utcnow()
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def deactivate_user(self, db: Session, *, user: User) -> User:
        """Deactivate user account"""
        user.is_active = False
        user.updated_at = datetime.utcnow()
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def activate_user(self, db: Session, *, user: User) -> User:
        """Activate user account"""
        user.is_active = True
        user.updated_at = datetime.utcnow()
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def update_password(self, db: Session, *, user: User, new_password: str) -> User:
        """Update user password"""
        user.set_password(new_password)
        user.updated_at = datetime.utcnow()
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def update_last_login(self, db: Session, *, user: User, ip_address: str = None) -> User:
        """Update user's last login timestamp"""
        user.last_login = datetime.utcnow()
        if ip_address:
            user.last_login_ip = ip_address
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def increment_api_usage(self, db: Session, *, user: User, count: int = 1) -> User:
        """Increment user's API usage count"""
        user.api_usage_count += count
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def reset_api_usage(self, db: Session, *, user: User) -> User:
        """Reset user's API usage count (monthly reset)"""
        user.api_usage_count = 0
        user.api_usage_reset_date = datetime.utcnow() + timedelta(days=30)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def update_subscription(
        self, 
        db: Session, 
        *, 
        user: User, 
        tier: str,
        start_date: datetime = None, 
        end_date: datetime = None
    ) -> User:
        """Update user's subscription"""
        user.subscription_tier = tier
        if start_date:
            user.subscription_start_date = start_date
        if end_date:
            user.subscription_end_date = end_date
        
        # Update API limits based on tier
        limits = user.get_subscription_limits()
        user.api_usage_limit = limits["api_calls"]
        
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def get_users_by_subscription(
        self, 
        db: Session, 
        *, 
        tier: str,
        skip: int = 0, 
        limit: int = 100
    ) -> List[User]:
        """Get users by subscription tier"""
        return db.query(User).filter(
            User.subscription_tier == tier
        ).offset(skip).limit(limit).all()

    def get_active_users(
        self, 
        db: Session, 
        *, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[User]:
        """Get active users"""
        return db.query(User).filter(
            User.is_active == True
        ).offset(skip).limit(limit).all()

    def get_users_created_between(
        self, 
        db: Session, 
        *, 
        start_date: datetime,
        end_date: datetime, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[User]:
        """Get users created between dates"""
        return db.query(User).filter(
            and_(User.created_at >= start_date, User.created_at <= end_date)
        ).offset(skip).limit(limit).all()

    def search_users(
        self, 
        db: Session, 
        *, 
        query: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[User]:
        """Search users by username, email, or full name"""
        search_filter = or_(
            User.username.ilike(f"%{query}%"),
            User.email.ilike(f"%{query}%"),
            User.full_name.ilike(f"%{query}%")
        )
        return db.query(User).filter(search_filter).offset(skip).limit(limit).all()

    def get_user_stats(self, db: Session, *, user: User) -> Dict[str, Any]:
        """Get user statistics"""
        from app.models.audio_file import AudioFile
        from app.models.agent_session import AgentSession
        
        # Get file statistics
        file_stats = db.query(
            func.count(AudioFile.id).label('total_files'),
            func.sum(AudioFile.file_size).label('total_size'),
            func.avg(AudioFile.duration).label('avg_duration')
        ).filter(AudioFile.user_id == user.id).first()
        
        # Get session statistics
        session_stats = db.query(
            func.count(AgentSession.id).label('total_sessions'),
            func.sum(AgentSession.total_cost).label('total_cost'),
            func.sum(AgentSession.total_execution_time).label('total_time')
        ).filter(AgentSession.user_id == user.id).first()
        
        return {
            'user_id': str(user.id),
            'total_files': file_stats.total_files or 0,
            'total_storage_bytes': file_stats.total_size or 0,
            'average_file_duration': file_stats.avg_duration or 0,
            'total_sessions': session_stats.total_sessions or 0,
            'total_cost': float(session_stats.total_cost or 0),
            'total_processing_time': float(session_stats.total_time or 0),
            'api_usage_count': user.api_usage_count,
            'api_usage_limit': user.api_usage_limit,
            'subscription_tier': user.subscription_tier,
            'account_age_days': (datetime.utcnow() - user.created_at).days,
            'last_login': user.last_login,
        }

    def get_subscription_expiring_users(
        self, 
        db: Session, 
        *, 
        days: int = 7
    ) -> List[User]:
        """Get users whose subscription is expiring within specified days"""
        expiry_date = datetime.utcnow() + timedelta(days=days)
        return db.query(User).filter(
            and_(
                User.subscription_end_date.isnot(None),
                User.subscription_end_date <= expiry_date,
                User.subscription_tier != 'free'
            )
        ).all()

    def get_inactive_users(self, db: Session, *, days: int = 30) -> List[User]:
        """Get users who haven't logged in for specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return db.query(User).filter(
            or_(
                User.last_login.is_(None),
                User.last_login <= cutoff_date
            )
        ).all()

    def bulk_update_api_limits(
        self, 
        db: Session, 
        *, 
        user_ids: List[str], 
        new_limit: int
    ) -> int:
        """Bulk update API limits for multiple users"""
        updated_count = db.query(User).filter(
            User.id.in_(user_ids)
        ).update({
            User.api_usage_limit: new_limit,
            User.updated_at: datetime.utcnow()
        }, synchronize_session=False)
        db.commit()
        return updated_count

    def delete_inactive_unverified_users(
        self, 
        db: Session, 
        *, 
        days: int = 7
    ) -> int:
        """Delete unverified users older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted_count = db.query(User).filter(
            and_(
                User.is_verified == False,
                User.created_at <= cutoff_date
            )
        ).delete(synchronize_session=False)
        db.commit()
        return deleted_count

    def record_failed_login(self, db: Session, *, user: User) -> User:
        """Record failed login attempt"""
        user.failed_login_attempts += 1
        
        # Lock account after 5 failed attempts
        if user.failed_login_attempts >= 5:
            user.lock_account(duration_minutes=30)
            logger.warning("User account locked due to failed login attempts", 
                         user_id=str(user.id), attempts=user.failed_login_attempts)
        
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def reset_failed_login_attempts(self, db: Session, *, user: User) -> User:
        """Reset failed login attempts after successful login"""
        user.failed_login_attempts = 0
        user.unlock_account()
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def set_password_reset_token(
        self, 
        db: Session, 
        *, 
        user: User, 
        token: str
    ) -> User:
        """Set password reset token"""
        user.password_reset_token = token
        user.password_reset_expires = datetime.utcnow() + timedelta(hours=24)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def clear_password_reset_token(self, db: Session, *, user: User) -> User:
        """Clear password reset token"""
        user.password_reset_token = None
        user.password_reset_expires = None
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def set_email_verification_token(
        self, 
        db: Session, 
        *, 
        user: User, 
        token: str
    ) -> User:
        """Set email verification token"""
        user.email_verification_token = token
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def clear_email_verification_token(self, db: Session, *, user: User) -> User:
        """Clear email verification token"""
        user.email_verification_token = None
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

user_crud = CRUDUser(User)
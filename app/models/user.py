from sqlalchemy import Integer, String, DateTime, Boolean, Text, func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.db.database import Base
import uuid
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
# Removed passlib.context import, will use utils
from datetime import datetime, timedelta
from typing import List, TYPE_CHECKING, Optional # Added Optional
from app.core.password_utils import verify_password, get_password_hash # Import new utils

if TYPE_CHECKING:
    from .audio_file import AudioFile
    from .agent_session import AgentSession
    from .api_key import APIKey

# pwd_context removed

class User(Base):
    __tablename__ = "users"

    # id, created_at, updated_at are inherited from Base

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Profile fields
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    
    # Subscription and billing
    subscription_tier: Mapped[str] = mapped_column(String(50), default="free")  # free, premium, pro
    subscription_start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    subscription_end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # API usage tracking
    api_usage_count: Mapped[int] = mapped_column(Integer, default=0)
    api_usage_limit: Mapped[int] = mapped_column(Integer, default=100)  # Based on subscription
    api_usage_reset_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Security
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    password_reset_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_reset_expires: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    email_verification_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Relationships
    audio_files: Mapped[List["AudioFile"]] = relationship("AudioFile", back_populates="user", cascade="all, delete-orphan")
    agent_sessions: Mapped[List["AgentSession"]] = relationship("AgentSession", back_populates="user", cascade="all, delete-orphan")
    api_keys: Mapped[List["APIKey"]] = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")

    def verify_password(self, password: str) -> bool:
        """Verify a password against the hash"""
        return verify_password(password, self.hashed_password) # Use imported function

    def set_password(self, password: str):
        """Set password hash"""
        self.hashed_password = get_password_hash(password) # Use imported function

    def can_make_api_call(self) -> bool:
        """Check if user can make API calls based on usage limits"""
        if not self.is_active:
            return False
        
        # Check if usage limit reset is needed
        if self.api_usage_reset_date and datetime.utcnow() > self.api_usage_reset_date:
            self.reset_api_usage()
        
        return self.api_usage_count < self.api_usage_limit

    def increment_api_usage(self):
        """Increment API usage counter"""
        self.api_usage_count += 1

    def reset_api_usage(self):
        """Reset API usage counter (monthly reset)"""
        self.api_usage_count = 0
        self.api_usage_reset_date = datetime.utcnow() + timedelta(days=30)

    def is_account_locked(self) -> bool:
        """Check if account is locked due to failed login attempts"""
        if self.locked_until and datetime.utcnow() < self.locked_until:
            return True
        return False

    def lock_account(self, duration_minutes: int = 30):
        """Lock account for specified duration"""
        self.locked_until = datetime.utcnow() + timedelta(minutes=duration_minutes)

    def unlock_account(self):
        """Unlock account and reset failed attempts"""
        self.locked_until = None
        self.failed_login_attempts = 0

    def get_subscription_limits(self) -> dict:
        """Get limits based on subscription tier"""
        limits = {
            "free": {
                "api_calls": 100,
                "file_size_mb": 10,
                "concurrent_sessions": 1,
                "storage_gb": 1
            },
            "premium": {
                "api_calls": 1000,
                "file_size_mb": 50,
                "concurrent_sessions": 3,
                "storage_gb": 10
            },
            "pro": {
                "api_calls": 10000,
                "file_size_mb": 100,
                "concurrent_sessions": 10,
                "storage_gb": 100
            }
        }
        return limits.get(self.subscription_tier, limits["free"])

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"
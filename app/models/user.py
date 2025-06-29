from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import uuid
from sqlalchemy.dialects.postgresql import UUID
from passlib.context import CryptContext
from datetime import datetime, timedelta

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Profile fields
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    phone_number = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)
    timezone = Column(String(50), default="UTC")
    
    # Subscription and billing
    subscription_tier = Column(String(50), default="free")  # free, premium, pro
    subscription_start_date = Column(DateTime(timezone=True), nullable=True)
    subscription_end_date = Column(DateTime(timezone=True), nullable=True)
    stripe_customer_id = Column(String(100), nullable=True)
    
    # API usage tracking
    api_usage_count = Column(Integer, default=0)
    api_usage_limit = Column(Integer, default=100)  # Based on subscription
    api_usage_reset_date = Column(DateTime(timezone=True), nullable=True)
    
    # Security
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    password_reset_token = Column(String(255), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    email_verification_token = Column(String(255), nullable=True)
    
    # Relationships
    audio_files = relationship("AudioFile", back_populates="user", cascade="all, delete-orphan")
    agent_sessions = relationship("AgentSession", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")

    def verify_password(self, password: str) -> bool:
        """Verify a password against the hash"""
        return pwd_context.verify(password, self.hashed_password)

    def set_password(self, password: str):
        """Set password hash"""
        self.hashed_password = pwd_context.hash(password)

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
from sqlalchemy import Integer, String, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from app.db.database import Base
import uuid
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .user import User

class APIKey(Base):
    __tablename__ = "api_keys"

    # id, created_at, updated_at are inherited from Base

    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Key information
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # User-defined name for the key
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)  # SHA-256 hash
    key_prefix: Mapped[str] = mapped_column(String(10), nullable=False)  # First 8 chars for identification
    
    # Permissions and limits
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    scopes: Mapped[str] = mapped_column(String(500), default="read,write")  # Comma-separated permissions
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=60)
    rate_limit_per_hour: Mapped[int] = mapped_column(Integer, default=1000)
    rate_limit_per_day: Mapped[int] = mapped_column(Integer, default=10000)
    
    # Usage tracking
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv6 compatible
    
    # Security
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_from_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="api_keys")

    def __repr__(self):
        return f"<APIKey(id={self.id}, name={self.name}, active={self.is_active})>"

    @classmethod
    def generate_key(cls) -> tuple[str, str]:
        """Generate a new API key and return (key, hash)"""
        # Generate a secure random key
        key = f"mk_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return key, key_hash

    @classmethod
    def create_api_key(cls, user_id: str, name: str, scopes: str = "read,write", 
                      expires_days: int = None, created_from_ip: str = None):
        """Create a new API key"""
        key, key_hash = cls.generate_key()
        
        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        api_key = cls(
            user_id=user_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key[:8],
            scopes=scopes,
            expires_at=expires_at,
            created_from_ip=created_from_ip
        )
        
        return api_key, key

    def verify_key(self, key: str) -> bool:
        """Verify if the provided key matches this API key"""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return key_hash == self.key_hash

    def is_valid(self) -> bool:
        """Check if API key is valid and not expired"""
        if not self.is_active:
            return False
        
        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False
        
        return True

    def has_scope(self, required_scope: str) -> bool:
        """Check if API key has required scope"""
        if not self.scopes:
            return False
        
        key_scopes = [scope.strip() for scope in self.scopes.split(',')]
        return required_scope in key_scopes or 'admin' in key_scopes

    def record_usage(self, ip_address: str = None):
        """Record API key usage"""
        self.usage_count += 1
        self.last_used_at = datetime.utcnow()
        if ip_address:
            self.last_used_ip = ip_address

    def deactivate(self):
        """Deactivate the API key"""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def activate(self):
        """Activate the API key"""
        self.is_active = True
        self.updated_at = datetime.utcnow()

    def extend_expiry(self, days: int):
        """Extend API key expiry"""
        if self.expires_at:
            self.expires_at += timedelta(days=days)
        else:
            self.expires_at = datetime.utcnow() + timedelta(days=days)
        self.updated_at = datetime.utcnow()

    @property
    def masked_key(self) -> str:
        """Return masked version of the key for display"""
        return f"{self.key_prefix}{'*' * 24}"

    @property
    def days_until_expiry(self) -> int:
        """Get days until expiry"""
        if not self.expires_at:
            return -1  # Never expires
        
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.days)

    @property
    def is_expiring_soon(self) -> bool:
        """Check if key is expiring within 7 days"""
        return 0 <= self.days_until_expiry <= 7
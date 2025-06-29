from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from .common import BaseSchema, SubscriptionTier

# Base user schemas
class UserBase(BaseSchema):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    full_name: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = Field(None, max_length=1000)
    phone_number: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    timezone: str = Field(default="UTC", max_length=50)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v

class UserUpdate(BaseSchema):
    full_name: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = Field(None, max_length=1000)
    phone_number: Optional[str] = Field(None, max_length=20)
    country: Optional[str] = Field(None, max_length=100)
    timezone: Optional[str] = Field(None, max_length=50)
    avatar_url: Optional[str] = Field(None, max_length=500)

class UserResponse(UserBase):
    id: uuid.UUID
    is_active: bool
    is_verified: bool
    is_superuser: bool
    subscription_tier: SubscriptionTier
    api_usage_count: int
    api_usage_limit: int
    created_at: datetime
    updated_at: Optional[datetime]
    last_login: Optional[datetime]

class UserProfile(UserResponse):
    subscription_start_date: Optional[datetime]
    subscription_end_date: Optional[datetime]
    avatar_url: Optional[str]
    stripe_customer_id: Optional[str]
    failed_login_attempts: int
    locked_until: Optional[datetime]

class UserPublicProfile(BaseSchema):
    """Public user profile (limited information)"""
    id: uuid.UUID
    username: str
    full_name: Optional[str]
    bio: Optional[str]
    avatar_url: Optional[str]
    country: Optional[str]
    created_at: datetime

# User statistics
class UserStats(BaseSchema):
    total_files: int
    total_sessions: int
    total_processing_time: float
    total_cost: float
    storage_used_mb: float
    api_calls_this_month: int
    subscription_tier: SubscriptionTier
    account_age_days: int
    login_count: int
    last_login: Optional[datetime]

class UserUsageStats(BaseSchema):
    """Detailed usage statistics"""
    api_calls: Dict[str, int]  # Daily API calls for last 30 days
    storage_usage: Dict[str, float]  # Storage usage over time
    session_duration: Dict[str, float]  # Average session duration
    popular_features: List[Dict[str, Any]]  # Most used features
    cost_breakdown: Dict[str, float]  # Cost by service

# Subscription management
class SubscriptionUpdate(BaseSchema):
    tier: SubscriptionTier
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class SubscriptionInfo(BaseSchema):
    tier: SubscriptionTier
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    is_active: bool
    days_remaining: Optional[int]
    auto_renew: bool
    limits: Dict[str, Any]

# User preferences
class UserPreferences(BaseSchema):
    theme: str = Field(default="light", pattern="^(light|dark|auto)$")
    language: str = Field(default="en", max_length=5)
    notifications_email: bool = True
    notifications_push: bool = True
    notifications_sms: bool = False
    default_audio_quality: str = Field(default="high", pattern="^(low|medium|high|lossless)$")
    auto_save_projects: bool = True
    privacy_level: str = Field(default="private", pattern="^(public|friends|private)$")

class UserPreferencesUpdate(BaseSchema):
    theme: Optional[str] = Field(None, pattern="^(light|dark|auto)$")
    language: Optional[str] = Field(None, max_length=5)
    notifications_email: Optional[bool] = None
    notifications_push: Optional[bool] = None
    notifications_sms: Optional[bool] = None
    default_audio_quality: Optional[str] = Field(None, pattern="^(low|medium|high|lossless)$")
    auto_save_projects: Optional[bool] = None
    privacy_level: Optional[str] = Field(None, pattern="^(public|friends|private)$")

# User search and filtering
class UserSearchParams(BaseSchema):
    query: Optional[str] = Field(None, max_length=200)
    subscription_tier: Optional[SubscriptionTier] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    country: Optional[str] = Field(None, max_length=100)
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    last_login_after: Optional[datetime] = None
    last_login_before: Optional[datetime] = None

# Admin user management
class UserAdminUpdate(BaseSchema):
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    is_superuser: Optional[bool] = None
    subscription_tier: Optional[SubscriptionTier] = None
    api_usage_limit: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=1000)

class UserAdminResponse(UserProfile):
    notes: Optional[str]
    total_cost: float
    total_sessions: int
    total_files: int
    storage_used_mb: float

# User activity tracking
class UserActivity(BaseSchema):
    activity_type: str
    description: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None

class UserActivityLog(BaseSchema):
    activities: List[UserActivity]
    total: int
    page: int
    size: int

# User deletion and data export
class UserDataExportRequest(BaseSchema):
    include_files: bool = True
    include_sessions: bool = True
    include_activity_log: bool = False
    format: str = Field(default="json", pattern="^(json|csv|xml)$")

class UserDataExportResponse(BaseSchema):
    export_id: str
    status: str
    created_at: datetime
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None

class UserDeletionRequest(BaseSchema):
    password: str
    confirmation: str = Field(..., pattern="^DELETE$")
    reason: Optional[str] = Field(None, max_length=500)

    @validator('confirmation')
    def validate_confirmation(cls, v):
        if v != "DELETE":
            raise ValueError('Must type "DELETE" to confirm account deletion')
        return v

# Bulk user operations (admin only)
class BulkUserOperation(BaseSchema):
    user_ids: List[uuid.UUID] = Field(..., min_items=1, max_items=100)
    operation: str = Field(..., pattern="^(activate|deactivate|verify|unverify|delete)$")
    reason: Optional[str] = Field(None, max_length=500)

class BulkUserOperationResult(BaseSchema):
    operation: str
    total_users: int
    successful: int
    failed: int
    errors: List[Dict[str, str]]
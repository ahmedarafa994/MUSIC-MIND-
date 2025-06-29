from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Generic, TypeVar
from datetime import datetime
from enum import Enum

# Base schema class
class BaseSchema(BaseModel):
    class Config:
        from_attributes = True
        use_enum_values = True

# Enums
class SubscriptionTier(str, Enum):
    FREE = "free"
    PREMIUM = "premium"
    PRO = "pro"

class FileStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    QUEUED = "queued"

class SessionStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

class SessionType(str, Enum):
    MUSIC_GENERATION = "music_generation"
    MASTERING = "mastering"
    ANALYSIS = "analysis"
    ENHANCEMENT = "enhancement"

# Pagination schemas
class PaginationParams(BaseSchema):
    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=20, ge=1, le=100, description="Items per page")
    sort_by: Optional[str] = Field(None, max_length=50, description="Field to sort by")
    sort_order: str = Field(default="desc", regex="^(asc|desc)$", description="Sort order")

T = TypeVar('T')

class PaginatedResponse(BaseSchema, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    pages: int
    has_next: bool
    has_prev: bool

# Error schemas
class ErrorDetail(BaseSchema):
    code: str
    message: str
    field: Optional[str] = None

class ErrorResponse(BaseSchema):
    error: str
    details: Optional[List[ErrorDetail]] = None
    timestamp: datetime
    request_id: Optional[str] = None

# Success response schema
class SuccessResponse(BaseSchema):
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None

# Health check schema
class HealthCheckResponse(BaseSchema):
    status: str
    timestamp: datetime
    version: str
    database: str
    redis: Optional[str] = None
    storage: str
    uptime: float

# Statistics schemas
class UserStats(BaseSchema):
    total_files: int
    total_sessions: int
    total_processing_time: float
    total_cost: float
    storage_used_mb: float
    api_calls_this_month: int
    subscription_tier: SubscriptionTier
    account_age_days: int

class SystemStats(BaseSchema):
    total_users: int
    total_files: int
    total_sessions: int
    active_sessions: int
    total_processing_time: float
    average_processing_time: float
    success_rate: float
    storage_used_gb: float
    api_calls_today: int

# File upload schemas
class FileUploadRequest(BaseSchema):
    filename: str = Field(..., max_length=255)
    file_size: int = Field(..., gt=0)
    mime_type: str = Field(..., max_length=100)
    checksum: Optional[str] = Field(None, max_length=64)

class FileUploadResponse(BaseSchema):
    file_id: str
    filename: str
    upload_url: Optional[str] = None  # For direct upload to cloud storage
    expires_at: Optional[datetime] = None

# Webhook schemas
class WebhookEvent(BaseSchema):
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[str] = None

class WebhookResponse(BaseSchema):
    success: bool
    message: Optional[str] = None

# Search and filter schemas
class SearchParams(BaseSchema):
    query: Optional[str] = Field(None, max_length=200)
    filters: Optional[Dict[str, Any]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

# Notification schemas
class NotificationCreate(BaseSchema):
    title: str = Field(..., max_length=200)
    message: str = Field(..., max_length=1000)
    type: str = Field(..., max_length=50)
    user_id: str
    data: Optional[Dict[str, Any]] = None

class NotificationResponse(BaseSchema):
    id: str
    title: str
    message: str
    type: str
    is_read: bool
    created_at: datetime
    data: Optional[Dict[str, Any]] = None
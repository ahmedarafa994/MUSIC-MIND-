from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
import uuid
from .common import BaseSchema

# Base API key schemas
class APIKeyBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=100)
    scopes: str = Field(default="read,write", max_length=500)
    description: Optional[str] = Field(None, max_length=500)

class APIKeyCreate(APIKeyBase):
    expires_days: Optional[int] = Field(None, ge=1, le=365)
    rate_limit_per_minute: Optional[int] = Field(None, ge=1, le=1000)
    rate_limit_per_hour: Optional[int] = Field(None, ge=1, le=10000)
    rate_limit_per_day: Optional[int] = Field(None, ge=1, le=100000)

class APIKeyUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    scopes: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    rate_limit_per_minute: Optional[int] = Field(None, ge=1, le=1000)
    rate_limit_per_hour: Optional[int] = Field(None, ge=1, le=10000)
    rate_limit_per_day: Optional[int] = Field(None, ge=1, le=100000)

class APIKeyResponse(APIKeyBase):
    id: uuid.UUID
    key_prefix: str
    is_active: bool
    usage_count: int
    last_used_at: Optional[datetime]
    last_used_ip: Optional[str]
    expires_at: Optional[datetime]
    rate_limit_per_minute: int
    rate_limit_per_hour: int
    rate_limit_per_day: int
    created_at: datetime
    updated_at: Optional[datetime]

class APIKeyDetail(APIKeyResponse):
    masked_key: str
    days_until_expiry: int
    is_expiring_soon: bool
    usage_stats: Optional[dict] = None

class APIKeyCreateResponse(BaseSchema):
    api_key: APIKeyResponse
    key: str  # Only returned once during creation
    warning: str = "Store this key securely. It will not be shown again."

# API key usage tracking
class APIKeyUsage(BaseSchema):
    api_key_id: uuid.UUID
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    ip_address: str
    user_agent: Optional[str]
    timestamp: datetime
    request_size_bytes: Optional[int]
    response_size_bytes: Optional[int]

class APIKeyUsageStats(BaseSchema):
    api_key_id: uuid.UUID
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time: float
    total_data_transferred: int
    requests_by_endpoint: dict
    requests_by_day: dict
    error_rate: float
    last_30_days_usage: List[dict]

# API key permissions and scopes
class APIKeyScope(BaseSchema):
    scope: str
    description: str
    permissions: List[str]

class APIKeyScopeList(BaseSchema):
    scopes: List[APIKeyScope]

# API key rate limiting
class RateLimitInfo(BaseSchema):
    limit_per_minute: int
    limit_per_hour: int
    limit_per_day: int
    current_minute_usage: int
    current_hour_usage: int
    current_day_usage: int
    reset_time_minute: datetime
    reset_time_hour: datetime
    reset_time_day: datetime
    is_rate_limited: bool

class RateLimitExceeded(BaseSchema):
    error: str = "Rate limit exceeded"
    limit_type: str  # minute, hour, day
    limit: int
    current_usage: int
    reset_time: datetime
    retry_after: int  # seconds

# API key security
class APIKeySecurityEvent(BaseSchema):
    api_key_id: uuid.UUID
    event_type: str  # suspicious_usage, rate_limit_exceeded, invalid_scope, etc.
    description: str
    ip_address: str
    user_agent: Optional[str]
    timestamp: datetime
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    metadata: Optional[dict] = None

class APIKeySecurityLog(BaseSchema):
    api_key_id: uuid.UUID
    events: List[APIKeySecurityEvent]
    total_events: int
    high_severity_count: int
    last_suspicious_activity: Optional[datetime]

# API key rotation
class APIKeyRotationRequest(BaseSchema):
    api_key_id: uuid.UUID
    expires_old_key_in_hours: int = Field(default=24, ge=1, le=168)  # 1 hour to 1 week

class APIKeyRotationResponse(BaseSchema):
    old_key_id: uuid.UUID
    new_key_id: uuid.UUID
    new_key: str
    old_key_expires_at: datetime
    warning: str = "Update your applications with the new key before the old key expires."

# Bulk API key operations
class BulkAPIKeyOperation(BaseSchema):
    api_key_ids: List[uuid.UUID] = Field(..., min_items=1, max_items=50)
    operation: str = Field(..., pattern="^(activate|deactivate|delete|extend_expiry)$")
    parameters: Optional[dict] = None

class BulkAPIKeyOperationResult(BaseSchema):
    operation: str
    total_keys: int
    successful: int
    failed: int
    results: List[dict]

# API key templates
class APIKeyTemplate(BaseSchema):
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    default_scopes: str
    default_expires_days: Optional[int] = Field(None, ge=1, le=365)
    default_rate_limits: dict
    is_public: bool = False

class APIKeyTemplateResponse(APIKeyTemplate):
    id: uuid.UUID
    created_by: uuid.UUID
    usage_count: int
    created_at: datetime
    updated_at: Optional[datetime]

# API key analytics
class APIKeyAnalytics(BaseSchema):
    api_key_id: uuid.UUID
    time_period: str  # day, week, month
    total_requests: int
    unique_ips: int
    top_endpoints: List[dict]
    error_breakdown: dict
    response_time_percentiles: dict
    geographic_distribution: dict
    hourly_usage_pattern: List[dict]

# API key webhook notifications
class APIKeyWebhook(BaseSchema):
    api_key_id: uuid.UUID
    webhook_url: str = Field(..., max_length=500)
    events: List[str] = Field(..., min_items=1)  # rate_limit, security_event, expiry_warning
    is_active: bool = True
    secret: Optional[str] = Field(None, max_length=100)

class APIKeyWebhookResponse(APIKeyWebhook):
    id: uuid.UUID
    created_at: datetime
    last_triggered: Optional[datetime]
    total_deliveries: int
    failed_deliveries: int

# API key export/import
class APIKeyExport(BaseSchema):
    include_usage_stats: bool = False
    include_security_events: bool = False
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    format: str = Field(default="json", pattern="^(json|csv)$")

class APIKeyExportResponse(BaseSchema):
    export_id: uuid.UUID
    download_url: str
    expires_at: datetime
    file_size_bytes: int
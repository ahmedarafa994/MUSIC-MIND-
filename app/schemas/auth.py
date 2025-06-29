from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from .common import BaseSchema

# Token schemas
class Token(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenData(BaseSchema):
    user_id: Optional[str] = None
    scopes: List[str] = []

class RefreshTokenRequest(BaseSchema):
    refresh_token: str

# Authentication request schemas
class LoginRequest(BaseSchema):
    email: EmailStr
    password: str
    remember_me: bool = False

class RegisterRequest(BaseSchema):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
    terms_accepted: bool = True

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

    @validator('terms_accepted')
    def validate_terms(cls, v):
        if not v:
            raise ValueError('Terms and conditions must be accepted')
        return v

# Password management schemas
class PasswordResetRequest(BaseSchema):
    email: EmailStr

class PasswordResetConfirm(BaseSchema):
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @validator('new_password')
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

class ChangePasswordRequest(BaseSchema):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @validator('new_password')
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

# Email verification schemas
class EmailVerificationRequest(BaseSchema):
    email: EmailStr

class EmailVerificationConfirm(BaseSchema):
    token: str

# Two-factor authentication schemas
class TwoFactorSetupRequest(BaseSchema):
    password: str

class TwoFactorSetupResponse(BaseSchema):
    secret: str
    qr_code_url: str
    backup_codes: List[str]

class TwoFactorConfirmRequest(BaseSchema):
    code: str

class TwoFactorLoginRequest(BaseSchema):
    email: EmailStr
    password: str
    totp_code: str

# Social authentication schemas
class SocialAuthRequest(BaseSchema):
    provider: str = Field(..., pattern="^(google|github|discord)$")
    access_token: str

class SocialAuthResponse(BaseSchema):
    user_id: str
    is_new_user: bool
    access_token: str
    refresh_token: str

# Session management schemas
class SessionInfo(BaseSchema):
    session_id: str
    user_agent: str
    ip_address: str
    location: Optional[str] = None
    created_at: datetime
    last_activity: datetime
    is_current: bool

class SessionListResponse(BaseSchema):
    sessions: List[SessionInfo]
    total: int

class RevokeSessionRequest(BaseSchema):
    session_id: str

# Account security schemas
class SecurityEvent(BaseSchema):
    event_type: str
    description: str
    ip_address: str
    user_agent: str
    timestamp: datetime
    location: Optional[str] = None

class SecurityLogResponse(BaseSchema):
    events: List[SecurityEvent]
    total: int

# API key authentication schemas
class APIKeyAuth(BaseSchema):
    api_key: str
    scopes: Optional[List[str]] = None

# Login response schemas
class LoginResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict  # Will contain user profile data
    requires_2fa: bool = False
    requires_email_verification: bool = False

class LogoutResponse(BaseSchema):
    message: str = "Successfully logged out"
    revoked_sessions: int = 0

# Moved from app.core.security
class TokenPayload(BaseSchema):
    sub: Optional[str] = None
    type: Optional[str] = None # e.g. "access", "refresh"
    scopes: List[str] = []

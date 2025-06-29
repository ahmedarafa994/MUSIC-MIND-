import os
from typing import List, Optional, Union
from pydantic import BaseSettings, AnyHttpUrl, validator
from functools import lru_cache

class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "AI Music Mastering API"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "your-secret-key-change-in-production"
    API_V1_STR: str = "/api/v1"
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # Database settings
    DATABASE_URL: str = "sqlite:///./music_mastering.db"
    
    # Redis settings (for caching and sessions)
    REDIS_URL: Optional[str] = "redis://localhost:6379/0"
    
    # Security settings
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    
    # Password settings
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGITS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = False
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    RATE_LIMIT_PER_DAY: int = 10000
    
    # File upload settings
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_AUDIO_TYPES: List[str] = [
        "audio/mpeg", "audio/wav", "audio/flac", 
        "audio/aac", "audio/ogg", "audio/mp4"
    ]
    UPLOAD_PATH: str = "uploads"
    TEMP_PATH: str = "temp"
    
    # AI/ML settings
    AI_MODEL_PATH: str = "models"
    MAX_PROCESSING_TIME: int = 3600  # 1 hour
    MAX_CONCURRENT_JOBS: int = 5
    
    # External API settings
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    HUGGINGFACE_API_KEY: Optional[str] = None
    STABILITY_API_KEY: Optional[str] = None
    GOOGLE_AI_API_KEY: Optional[str] = None
    REPLICATE_API_TOKEN: Optional[str] = None
    MAGENTA_API_KEY: Optional[str] = None
    TEPAND_API_KEY: Optional[str] = None
    ACES_API_KEY: Optional[str] = None
    SUNI_API_KEY: Optional[str] = None
    BEETHOVEN_API_KEY: Optional[str] = None
    MUREKA_API_KEY: Optional[str] = None
    LANDR_API_KEY: Optional[str] = None
    
    # Email settings
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = 587
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = None
    
    # Storage settings
    STORAGE_PROVIDER: str = "local"  # local, s3, gcs, azure
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None
    AWS_REGION: Optional[str] = "us-east-1"
    
    # CDN settings
    CDN_URL: Optional[str] = None
    
    # Monitoring and logging
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: Optional[str] = None
    
    # Subscription tiers
    FREE_TIER_LIMITS: dict = {
        "api_calls": 100,
        "file_size_mb": 10,
        "concurrent_sessions": 1,
        "storage_gb": 1
    }
    PREMIUM_TIER_LIMITS: dict = {
        "api_calls": 1000,
        "file_size_mb": 50,
        "concurrent_sessions": 3,
        "storage_gb": 10
    }
    PRO_TIER_LIMITS: dict = {
        "api_calls": 10000,
        "file_size_mb": 100,
        "concurrent_sessions": 10,
        "storage_gb": 100
    }
    
    @validator("ALLOWED_HOSTS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    @validator("DATABASE_URL", pre=True)
    def validate_database_url(cls, v: str) -> str:
        if not v:
            raise ValueError("DATABASE_URL is required")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
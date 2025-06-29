from datetime import datetime, timedelta
from typing import Any, Union, Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
# HTTPBearer, HTTPAuthorizationCredentials removed as reusable_oauth2 is moved
from fastapi.security import OAuth2PasswordBearer
# from sqlalchemy.ext.asyncio import AsyncSession # No longer needed directly here
# from pydantic import BaseModel # TokenPayload moved
from app.core.config import settings
# from app.core.database import get_db # No longer needed here
# from app.crud.user import user as user_crud # Will be used in deps
# from app.models.user import User # Will be used in deps
from app.schemas.auth import TokenPayload # Import TokenPayload from new location
from typing import Dict, List # Added Dict, List for to_encode type hint
import structlog

logger = structlog.get_logger()

# pwd_context and password hashing functions moved to app.core.password_utils

# reusable_oauth2 moved to app.api.deps

# TokenPayload class moved to app.schemas.auth


def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None, scopes: Optional[List[str]] = None
) -> str:
    """Create JWT access token"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode: Dict[str, Any] = {"exp": expire, "sub": str(subject), "type": "access"}
    if scopes:
        to_encode["scopes"] = scopes
    else:
        to_encode["scopes"] = []

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    logger.debug("Access token created", subject=str(subject))
    return encoded_jwt

def create_refresh_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT refresh token"""
    if expires_delta: # Allow overriding refresh token expiry for specific cases
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {"exp": expire, "sub": str(subject), "type": "refresh"}
    logger.debug("Refresh token created", subject=str(subject))
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def _verify_token_payload(token: str) -> TokenPayload:
    """Helper to verify and decode token into TokenPayload schema."""
    try:
        payload_dict = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return TokenPayload(**payload_dict)
    except JWTError as e:
        logger.warning("JWT verification failed", error=str(e), token_type=payload_dict.get("type") if 'payload_dict' in locals() else "unknown")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials - token error",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected error during token payload parsing: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials - payload error",
            headers={"WWW-Authenticate": "Bearer"},
        )

# verify_password and get_password_hash moved to app.core.password_utils

def validate_password(password: str) -> bool:
    """Validate password strength"""
    # This function uses settings, not pwd_context, so it can remain here
    # or be moved to password_utils if preferred. Keeping here for now.
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        return False
    
    if settings.PASSWORD_REQUIRE_UPPERCASE and not any(c.isupper() for c in password):
        return False
    
    if settings.PASSWORD_REQUIRE_LOWERCASE and not any(c.islower() for c in password):
        return False
    
    if settings.PASSWORD_REQUIRE_DIGITS and not any(c.isdigit() for c in password):
        return False
    
    if settings.PASSWORD_REQUIRE_SPECIAL and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False
    
    return True

# get_current_user, get_current_active_user, get_current_active_superuser moved to app.api.deps.py

def check_user_permissions(user: "User", required_permission: str) -> bool: # Type hint User with quotes for forward ref if User not imported
    """Check if user has required permission"""
    # Implement permission checking logic based on your needs
    if user.is_superuser:
        return True
    
    # Add more granular permission checks here
    return False

def generate_password_reset_token(email: str) -> str:
    """Generate password reset token"""
    delta = timedelta(hours=24)  # Token expires in 24 hours
    now = datetime.utcnow()
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {"exp": exp, "nbf": now, "sub": email, "type": "password_reset"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt

def verify_password_reset_token(token: str) -> Optional[str]:
    """Verify password reset token and return email"""
    try:
        token_payload = _verify_token_payload(token)
        if token_payload.type != "password_reset" or token_payload.sub is None:
            logger.warning("Invalid password reset token type or missing subject", token_type=token_payload.type)
            return None
        # Expiry is implicitly checked by jwt.decode in _verify_token_payload
        return token_payload.sub
    except HTTPException: # Raised by _verify_token_payload on JWTError/decode failure
        logger.warning("Password reset token verification failed (JWTError or payload issue)")
        return None

def generate_email_verification_token(email: str) -> str:
    """Generate email verification token"""
    delta = timedelta(hours=48)  # Token expires in 48 hours
    now = datetime.utcnow()
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode(
        {"exp": exp, "nbf": now, "sub": email, "type": "email_verification"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt

def verify_email_verification_token(token: str) -> Optional[str]:
    """Verify email verification token and return email"""
    try:
        token_payload = _verify_token_payload(token)
        if token_payload.type != "email_verification" or token_payload.sub is None:
            logger.warning("Invalid email verification token type or missing subject", token_type=token_payload.type)
            return None
        return token_payload.sub
    except HTTPException:
        logger.warning("Email verification token verification failed (JWTError or payload issue)")
        return None
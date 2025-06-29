from datetime import datetime, timedelta
from typing import Any, Union, Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer # Added OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession # Changed to AsyncSession
from pydantic import BaseModel # Added for TokenPayload
from app.core.config import settings
from app.core.database import get_db # For async
from app.crud.user import user as user_crud # Ensure this matches your crud instantiation
from app.models.user import User
import structlog

logger = structlog.get_logger()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    scopes={"me": "Read information about the current user."}
)

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    type: Optional[str] = None
    scopes: List[str] = []


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

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)

def validate_password(password: str) -> bool:
    """Validate password strength"""
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

async def get_current_user(
    token: str = Depends(reusable_oauth2),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user from access token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials - user retrieval",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_payload = _verify_token_payload(token)
        
    if token_payload.sub is None or token_payload.type != "access":
        logger.warning("Invalid token payload for access", payload_sub=token_payload.sub, payload_type=token_payload.type)
        raise credentials_exception
    
    user = await user_crud.get(db, id=token_payload.sub)
    if user is None:
        logger.warning("User from token not found in DB", user_id_from_token=token_payload.sub)
        raise credentials_exception
    
    if not user.is_active:
        logger.warning("Attempt to use token for inactive user", user_id=user.id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    
    if hasattr(user, 'is_account_locked') and user.is_account_locked():
        logger.warning("Attempt to use token for locked account", user_id=user.id)
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Account is locked")
    
    logger.debug("Current user retrieved", user_id=user.id)
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user (relies on get_current_user to have already checked active status)"""
    return current_user

async def get_current_active_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Get current active superuser"""
    if not current_user.is_superuser:
        logger.warning("Non-superuser attempted admin access", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    logger.debug("Superuser access granted", user_id=current_user.id)
    return current_user

def check_user_permissions(user: User, required_permission: str) -> bool:
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
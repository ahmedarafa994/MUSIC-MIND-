from typing import Generator, AsyncGenerator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.core.config import settings
from app.db.database import get_async_db, AsyncSessionLocal # get_async_db is preferred
from app.models.user import User
from app.crud.user import user_crud
from app.schemas.auth import TokenPayload # Moved from core.security
from app.core.security import _verify_token_payload # Keep core token verification logic separate

import structlog

logger = structlog.get_logger(__name__)

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    # scopes={"me": "Read information about the current user."} # Scopes can be defined per endpoint if needed
)

async def get_current_user(
    token: str = Depends(reusable_oauth2),
    db: AsyncSession = Depends(get_async_db)
) -> User:
    """
    Get current authenticated user from access token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials - user retrieval",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token_payload = _verify_token_payload(token) # Use the helper from core.security
    except HTTPException as e: # Catch HTTPException from _verify_token_payload
        logger.warning("Token verification failed in get_current_user", detail=e.detail)
        raise e # Re-raise the specific exception from _verify_token_payload

    if token_payload.sub is None or token_payload.type != "access":
        logger.warning("Invalid token payload for access", payload_sub=token_payload.sub, payload_type=token_payload.type)
        raise credentials_exception

    user = await user_crud.get(db, id=token_payload.sub)
    if user is None:
        logger.warning("User from token not found in DB", user_id_from_token=token_payload.sub)
        raise credentials_exception

    if not user.is_active: # Assuming User model has is_active
        logger.warning("Attempt to use token for inactive user", user_id=user.id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    if hasattr(user, 'is_account_locked') and user.is_account_locked(): # Assuming User model has this method
        logger.warning("Attempt to use token for locked account", user_id=user.id)
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="Account is locked")

    logger.debug("Current user retrieved", user_id=user.id)
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get current active user.
    Relies on get_current_user to have already checked active status.
    """
    # is_active check is already performed in get_current_user
    return current_user

async def get_current_active_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """
    Get current active superuser.
    """
    if not current_user.is_superuser: # Assuming User model has is_superuser
        logger.warning("Non-superuser attempted admin access", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    logger.debug("Superuser access granted", user_id=current_user.id)
    return current_user

# Placeholder for get_db if any synchronous parts still need it, though preference is async
# def get_db_sync() -> Generator[Session, None, None]:
#     db = SessionLocalSync() # Assuming SessionLocalSync is defined in database.py for sync sessions
#     try:
#         yield db
#     finally:
#         db.close()

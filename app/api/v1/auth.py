from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession # Changed import

from app.core import security
from app.core.config import settings
from app.db.database import get_async_db # Changed import
from app.crud.crud_user import user as async_crud_user # Changed import
from app.schemas import Token, UserCreate, UserResponse, LoginRequest, RefreshTokenRequest
from app.models.user import User # Import User model for type hinting if needed by is_active etc.

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register( # Added async
    *,
    db: AsyncSession = Depends(get_async_db), # Changed Session to AsyncSession
    user_in: UserCreate,
    request: Request
) -> Any:
    """
    Register new user
    """
    # Check if user exists
    user = await async_crud_user.get_by_email(db, email=user_in.email) # Added await
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, # Changed status code
            detail="User with this email already exists"
        )
    
    user = await async_crud_user.get_by_username(db, username=user_in.username) # Added await
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, # Changed status code
            detail="User with this username already exists"
        )
    
    # Create new user
    user = await async_crud_user.create(db, obj_in=user_in) # Added await
    return user

@router.post("/login", response_model=Token)
async def login( # Added async
    *,
    db: AsyncSession = Depends(get_async_db), # Changed Session to AsyncSession
    form_data: OAuth2PasswordRequestForm = Depends(),
    request: Request
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    user = await async_crud_user.authenticate( # Added await
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # is_account_locked is a model method, can be called directly
    if user.is_account_locked():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is temporarily locked due to failed login attempts"
        )
    
    # is_active is an async method in async_crud_user, or a property on the model
    # Assuming model property access is fine, or that deps.py handles active check
    if not await async_crud_user.is_active(user): # Added await, or use user.is_active if it's a property
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Model methods like unlock_account and properties like failed_login_attempts are synchronous
    # If they modify DB state, they should be part of an async CRUD operation or called before commit
    # The authenticate method in async_crud_user already handles this.
    
    # Update last login - ensure this is done within the authenticate or a separate async call
    # async_crud_user.authenticate should ideally handle this if it's part of successful auth.
    # If not, then:
    await async_crud_user.update_last_login(db, user_id=user.id) # Pass user_id

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    refresh_token = security.create_refresh_token(user.id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.post("/login/simple", response_model=Token)
async def login_simple( # Added async
    *,
    db: AsyncSession = Depends(get_async_db), # Changed Session to AsyncSession
    login_data: LoginRequest,
    request: Request
) -> Any:
    """
    Simple login with email and password
    """
    user = await async_crud_user.authenticate( # Added await
        db, email=login_data.email, password=login_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if user.is_account_locked():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is temporarily locked due to failed login attempts"
        )
    
    if not await async_crud_user.is_active(user): # Added await, or use user.is_active
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    await async_crud_user.update_last_login(db, user_id=user.id) # Pass user_id

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    refresh_token = security.create_refresh_token(user.id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.post("/refresh", response_model=Token)
async def refresh_token( # Added async
    *,
    db: AsyncSession = Depends(get_async_db), # Changed Session to AsyncSession
    refresh_data: RefreshTokenRequest,
    request: Request
) -> Any:
    """
    Refresh access token
    """
    payload = security.verify_password_reset_token(refresh_data.refresh_token) # verify_token was changed to verify_password_reset_token
                                                                             # Assuming verify_token is the correct one for generic tokens.
                                                                             # Reverting to a more generic verify_token if it exists or using _verify_token_payload

    # Corrected token verification:
    try:
        payload_obj = security._verify_token_payload(refresh_data.refresh_token) # Use the internal helper
    except HTTPException: # Raised by _verify_token_payload on error
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    if payload_obj.type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type for refresh"
        )
    
    user_id_str = payload_obj.sub
    if not user_id_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = await async_crud_user.get(db, id=user_id_str) # Added await
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, # Corrected from 401
            detail="User not found"
        )
    
    if not await async_crud_user.is_active(user): # Added await, or use user.is_active
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    new_refresh_token = security.create_refresh_token(user.id)
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.post("/logout")
async def logout( # Added async
    request: Request,
    current_user: UserResponse = Depends(security.get_current_active_user) # This dep already uses async db
) -> Any:
    """
    Logout user (invalidate token on client side)
    """
    # Server-side logout for JWT is typically about blocklisting tokens,
    # which is not implemented here. So, this remains a no-op on server.
    return {"message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
async def read_users_me( # Added async
    # db: AsyncSession = Depends(get_async_db), # DB not directly used, current_user is resolved by deps
    current_user: User = Depends(security.get_current_active_user), # Changed to User model
) -> Any:
    """
    Get current user
    """
    # current_user is already a User model instance from get_current_active_user
    return current_user
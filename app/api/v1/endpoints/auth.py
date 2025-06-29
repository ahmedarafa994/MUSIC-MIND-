from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm # Keep for form dependency if used directly
from sqlalchemy.ext.asyncio import AsyncSession # Changed import

from app.db.database import get_async_db # Changed import
from app.core.security import ( # Keep token generation and direct verification utils
    create_access_token,
    create_refresh_token,
    # verify_token, # This might be _verify_token_payload or specific token type verifiers
    generate_password_reset_token,
    verify_password_reset_token,
    generate_email_verification_token,
    verify_email_verification_token,
)
from app.api.deps import get_current_user # Import from deps
from app.crud.user import user_crud
from app.schemas.auth import (
    Token,
    LoginRequest,
    RegisterRequest,
    RefreshTokenRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    ChangePasswordRequest,
    EmailVerificationRequest,
    EmailVerificationConfirm,
    LoginResponse,
    LogoutResponse
)
from app.schemas.user import UserResponse, UserCreate
from app.models.user import User
from app.core.config import settings
import structlog

logger = structlog.get_logger()

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_db)
):
    """Register a new user"""
    # Check if user already exists
    existing_user = await user_crud.get_by_email(db, email=user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    existing_username = await user_crud.get_by_username(db, username=user_data.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Create new user
    # Assuming UserCreate doesn't need bio, phone_number, country for initial creation
    user_create = UserCreate(
        email=user_data.email,
        username=user_data.username,
        password=user_data.password,
        full_name=user_data.full_name,
        bio=None, # Explicitly set to None if not in RegisterRequest
        phone_number=None,
        country=None
    )
    
    user = await user_crud.create(db, obj_in=user_create)
    
    # Generate email verification token
    verification_token = generate_email_verification_token(user.email)
    # Assuming set_email_verification_token is async or will be refactored
    await user_crud.set_email_verification_token(db, user=user, token=verification_token)
    
    # TODO: Send verification email
    
    logger.info("New user registered", 
                user_id=str(user.id), 
                email=user.email,
                ip_address=request.client.host)
    
    return user

@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_db)
):
    """Login user and return access token"""
    user = await user_crud.authenticate( # await
        db, email=login_data.email, password=login_data.password
    )
    
    if not user:
        # Record failed login attempt if user exists
        existing_user = await user_crud.get_by_email(db, email=login_data.email) # await
        if existing_user:
            await user_crud.record_failed_login(db, user=existing_user) # await
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    if user.is_account_locked(): # This is a model method, likely synchronous
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is temporarily locked due to failed login attempts"
        )
    
    # Reset failed login attempts on successful login
    await user_crud.reset_failed_login_attempts(db, user=user) # await
    
    # Create tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(user.id), expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(subject=str(user.id))
    
    # Update last login
    await user_crud.update_last_login(db, user_id=user.id, ip_address=request.client.host) # await, pass user_id
    
    logger.info("User logged in", 
                user_id=str(user.id), 
                email=user.email,
                ip_address=request.client.host)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user={
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "is_verified": user.is_verified,
            "subscription_tier": user.subscription_tier
        },
        requires_email_verification=not user.is_verified
    )

@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """Refresh access token using refresh token"""
    try:
        # Use _verify_token_payload from app.core.security
        # It raises HTTPException on failure, so we can catch that.
        token_payload = _verify_token_payload(refresh_data.refresh_token)
        if token_payload.type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = token_payload.sub
        if not user_id: # sub should not be None for a valid refresh token
             raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

        user = await user_crud.get(db, id=user_id) # await
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new tokens
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=str(user.id), expires_delta=access_token_expires
        )
        new_refresh_token = create_refresh_token(subject=str(user.id))
        
        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

@router.post("/logout", response_model=LogoutResponse)
async def logout(
    current_user: User = Depends(get_current_user)
):
    """Logout user (client should discard tokens)"""
    logger.info("User logged out", user_id=str(current_user.id))
    return LogoutResponse(message="Successfully logged out")

@router.post("/password-reset")
async def request_password_reset(
    reset_data: PasswordResetRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """Request password reset"""
    user = await user_crud.get_by_email(db, email=reset_data.email) # await
    if not user:
        # Don't reveal if email exists or not
        return {"message": "If the email exists, a password reset link has been sent"}
    
    # Generate password reset token
    reset_token = generate_password_reset_token(user.email)
    await user_crud.set_password_reset_token(db, user=user, token=reset_token) # await
    
    # TODO: Send password reset email
    
    logger.info("Password reset requested", user_id=str(user.id), email=user.email)
    
    return {"message": "If the email exists, a password reset link has been sent"}

@router.post("/password-reset/confirm")
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_async_db)
):
    """Confirm password reset with token"""
    email = verify_password_reset_token(reset_data.token) # This is a sync function from core.security
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token"
        )
    
    user = await user_crud.get_by_email(db, email=email) # await
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update password
    await user_crud.update_password(db, user=user, new_password=reset_data.new_password) # await
    await user_crud.clear_password_reset_token(db, user=user) # await
    
    logger.info("Password reset completed", user_id=str(user.id))
    
    return {"message": "Password has been reset successfully"}

@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Change user password"""
    # current_user.verify_password is a model method, likely sync, which is fine.
    if not current_user.verify_password(password_data.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    await user_crud.update_password(db, user=current_user, new_password=password_data.new_password) # await
    
    logger.info("Password changed", user_id=str(current_user.id))
    
    return {"message": "Password changed successfully"}

@router.post("/verify-email")
async def request_email_verification(
    verification_data: EmailVerificationRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """Request email verification"""
    user = await user_crud.get_by_email(db, email=verification_data.email) # await
    if not user:
        return {"message": "If the email exists, a verification link has been sent"}
    
    if user.is_verified: # model property, sync is fine
        return {"message": "Email is already verified"}
    
    # Generate verification token
    verification_token = generate_email_verification_token(user.email) # sync util
    await user_crud.set_email_verification_token(db, user=user, token=verification_token) # await
    
    # TODO: Send verification email
    
    logger.info("Email verification requested", user_id=str(user.id))
    
    return {"message": "If the email exists, a verification link has been sent"}

@router.post("/verify-email/confirm")
async def confirm_email_verification(
    verification_data: EmailVerificationConfirm,
    db: AsyncSession = Depends(get_async_db)
):
    """Confirm email verification with token"""
    email = verify_email_verification_token(verification_data.token) # sync util
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    user = await user_crud.get_by_email(db, email=email) # await
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.is_verified: # model property, sync is fine
        return {"message": "Email is already verified"}
    
    # Verify user
    await user_crud.verify_user(db, user=user) # await
    await user_crud.clear_email_verification_token(db, user=user) # await
    
    logger.info("Email verified", user_id=str(user.id))
    
    return {"message": "Email verified successfully"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information"""
    return current_user
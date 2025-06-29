from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession # Changed import

from app.db.database import get_async_db # Changed import
from app.crud.user import user_crud
from app.crud.audio_file import audio_file_crud
from app.crud.agent_session import agent_session_crud
from app.schemas.user import (
    UserResponse, 
    UserUpdate, 
    UserStats, 
    UserProfile,
    UserPreferences,
    UserPreferencesUpdate,
    SubscriptionUpdate,
    SubscriptionInfo
)
from app.schemas.common import PaginatedResponse, SuccessResponse
from app.api.deps import get_current_user, get_current_active_superuser # Changed import
from app.models.user import User
import structlog

logger = structlog.get_logger()

router = APIRouter()

@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile"""
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Update current user profile"""
    updated_user = await user_crud.update(db, db_obj=current_user, obj_in=user_update)
    logger.info("User profile updated", user_id=str(current_user.id))
    return updated_user

@router.get("/me/stats", response_model=UserStats)
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Get user statistics"""
    stats = await user_crud.get_user_stats(db, user_id=current_user.id) # Pass user_id
    return UserStats(**stats)

@router.delete("/me", response_model=SuccessResponse)
async def delete_current_user(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Delete current user account"""
    # TODO: Implement proper data deletion workflow
    # - Delete all user files from storage
    # - Cancel active sessions
    # - Remove from billing system
    # - Send confirmation email
    
    await user_crud.remove(db, id=current_user.id)
    logger.info("User account deleted", user_id=str(current_user.id))
    
    return SuccessResponse(
        message="Account successfully deleted",
        data={"user_id": str(current_user.id)}
    )

@router.get("/me/audio-files")
async def get_user_audio_files(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: str = Query(None),
    search: str = Query(None)
):
    """Get user's audio files"""
    # This would use audio_file_crud when implemented
    # For now, return empty list
    return {
        "items": [],
        "total": 0,
        "page": (skip // limit) + 1,
        "size": limit,
        "pages": 0,
        "has_next": False,
        "has_prev": False
    }

@router.get("/me/sessions")
async def get_user_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: str = Query(None)
):
    """Get user's agent sessions"""
    # This would use agent_session_crud when implemented
    # For now, return empty list
    return {
        "items": [],
        "total": 0,
        "page": (skip // limit) + 1,
        "size": limit,
        "pages": 0,
        "has_next": False,
        "has_prev": False
    }

@router.get("/me/preferences", response_model=UserPreferences)
async def get_user_preferences(
    current_user: User = Depends(get_current_user)
):
    """Get user preferences"""
    # TODO: Implement user preferences model
    # For now, return default preferences
    return UserPreferences()

@router.put("/me/preferences", response_model=UserPreferences)
async def update_user_preferences(
    preferences: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user preferences"""
    # TODO: Implement user preferences update
    logger.info("User preferences updated", user_id=str(current_user.id))
    return UserPreferences()

@router.get("/me/subscription", response_model=SubscriptionInfo)
async def get_subscription_info(
    current_user: User = Depends(get_current_user)
):
    """Get user subscription information"""
    limits = current_user.get_subscription_limits()
    
    days_remaining = None
    if current_user.subscription_end_date:
        from datetime import datetime
        delta = current_user.subscription_end_date - datetime.utcnow()
        days_remaining = max(0, delta.days)
    
    return SubscriptionInfo(
        tier=current_user.subscription_tier,
        start_date=current_user.subscription_start_date,
        end_date=current_user.subscription_end_date,
        is_active=current_user.subscription_tier != "free",
        days_remaining=days_remaining,
        auto_renew=False,  # TODO: Implement auto-renew logic
        limits=limits
    )

@router.put("/me/subscription", response_model=SubscriptionInfo)
async def update_subscription(
    subscription_update: SubscriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user subscription"""
    # TODO: Integrate with payment processing
    updated_user = user_crud.update_subscription(
        db, 
        user=current_user, 
        tier=subscription_update.tier,
        start_date=subscription_update.start_date,
        end_date=subscription_update.end_date
    )
    
    logger.info("Subscription updated", 
                user_id=str(current_user.id), 
                tier=subscription_update.tier)
    
    return await get_subscription_info(current_user)

@router.post("/me/upgrade-subscription")
async def upgrade_subscription(
    subscription_tier: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upgrade user subscription"""
    if subscription_tier not in ["premium", "pro"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid subscription tier"
        )
    
    # TODO: Integrate with payment processing
    from datetime import datetime, timedelta
    
    updated_user = user_crud.update_subscription(
        db, 
        user=current_user, 
        tier=subscription_tier,
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=30)
    )
    
    logger.info("Subscription upgraded", 
                user_id=str(current_user.id), 
                tier=subscription_tier)
    
    return SuccessResponse(
        message=f"Subscription upgraded to {subscription_tier}",
        data={"tier": subscription_tier}
    )

# Admin endpoints
@router.get("/", response_model=PaginatedResponse[UserResponse])
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: str = Query(None),
    subscription_tier: str = Query(None),
    is_active: bool = Query(None)
):
    """List all users (admin only)"""
    filters = {}
    if subscription_tier:
        filters["subscription_tier"] = subscription_tier
    if is_active is not None:
        filters["is_active"] = is_active
    
    if search:
        users = user_crud.search_users(db, query=search, skip=skip, limit=limit)
        total = len(users)  # Simplified count
    else:
        result = user_crud.get_paginated(
            db, 
            page=(skip // limit) + 1, 
            size=limit,
            filters=filters
        )
        users = result["items"]
        total = result["total"]
    
    return PaginatedResponse(
        items=users,
        total=total,
        page=(skip // limit) + 1,
        size=limit,
        pages=(total + limit - 1) // limit,
        has_next=(skip + limit) < total,
        has_prev=skip > 0
    )

@router.get("/{user_id}", response_model=UserProfile)
async def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """Get user by ID (admin only)"""
    user = user_crud.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.put("/{user_id}/activate")
async def activate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """Activate user account (admin only)"""
    user = user_crud.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user_crud.activate_user(db, user=user)
    logger.info("User activated by admin", 
                user_id=user_id, 
                admin_id=str(current_user.id))
    
    return SuccessResponse(message="User activated successfully")

@router.put("/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """Deactivate user account (admin only)"""
    user = user_crud.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user_crud.deactivate_user(db, user=user)
    logger.info("User deactivated by admin", 
                user_id=user_id, 
                admin_id=str(current_user.id))
    
    return SuccessResponse(message="User deactivated successfully")

@router.get("/{user_id}/stats", response_model=UserStats)
async def get_user_stats_admin(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """Get user statistics (admin only)"""
    user = user_crud.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    stats = user_crud.get_user_stats(db, user=user)
    return UserStats(**stats)
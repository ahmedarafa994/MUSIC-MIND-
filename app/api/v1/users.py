from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession # Changed import

from app.db.database import get_async_db # Changed import
from app.crud.crud_user import user as async_crud_user # Changed import
# Assuming async versions of other CRUD modules will be available
from app.crud.crud_audio_file import audio_file as async_crud_audio_file
from app.crud.crud_agent_session import agent_session as async_crud_agent_session
from app.schemas import UserResponse, UserUpdate, UserProfile, UserStats
from app.core.security import get_current_active_user, get_current_superuser
from app.models.user import User

router = APIRouter()

@router.get("/me", response_model=UserProfile)
async def read_user_me( # Added async
    # db: AsyncSession = Depends(get_async_db), # DB not directly used
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get current user profile
    """
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_user_me( # Added async
    *,
    db: AsyncSession = Depends(get_async_db), # Changed Session to AsyncSession
    user_in: UserUpdate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Update current user
    """
    user = await async_crud_user.update(db, db_obj=current_user, obj_in=user_in) # Added await
    return user

@router.get("/me/stats", response_model=UserStats)
async def read_user_stats( # Added async
    db: AsyncSession = Depends(get_async_db), # Changed Session to AsyncSession
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get current user statistics
    """
    # Get user statistics using async CRUD operations
    # Note: get_by_user for audio_file returns a list, so len() is appropriate.
    # get_user_storage_usage and get_user_session_stats need to be async and called with await.
    # Assuming async_crud_audio_file.get_user_storage_usage exists and is async.
    # Assuming async_crud_agent_session.get_user_session_stats exists and is async.

    user_files = await async_crud_audio_file.get_by_user(db, user_id=current_user.id)
    total_files = len(user_files)
    
    # Assuming get_user_storage_usage is an async method in async_crud_audio_file
    storage_usage_stats = await async_crud_audio_file.get_user_storage_usage(db, user_id=current_user.id)
    storage_used_mb = storage_usage_stats.get("total_size_mb", 0.0)

    # Assuming get_user_stats is an async method in async_crud_user that gathers session stats
    # Or, if get_user_session_stats is separate:
    # session_stats = await async_crud_agent_session.get_user_session_stats(db, user_id=current_user.id)
    # For now, using the combined get_user_stats from async_crud_user:
    full_user_stats = await async_crud_user.get_user_stats(db, user_id=current_user.id)

    return UserStats(
        total_files=total_files,
        total_sessions=full_user_stats.get("total_sessions", 0),
        total_processing_time=full_user_stats.get("total_processing_time_seconds", 0.0),
        total_cost=full_user_stats.get("total_cost", 0.0),
        storage_used_mb=storage_used_mb,
        api_calls_this_month=current_user.api_usage_count,
        # These might come from full_user_stats or current_user model directly
        subscription_tier=current_user.subscription_tier,
        account_age_days=(datetime.utcnow() - current_user.created_at).days if current_user.created_at else 0,
        login_count=0, # Placeholder, as login_count was not in the async model/crud
        last_login=current_user.last_login
    )

@router.get("/{user_id}", response_model=UserResponse)
async def read_user( # Added async
    *,
    db: AsyncSession = Depends(get_async_db), # Changed Session to AsyncSession
    user_id: str, # Assuming user_id is UUID, should match model type
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """
    Get user by ID (superuser only)
    """
    user = await async_crud_user.get(db, id=user_id) # Added await
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user

@router.put("/{user_id}", response_model=UserResponse)
async def update_user( # Added async
    *,
    db: AsyncSession = Depends(get_async_db), # Changed Session to AsyncSession
    user_id: str, # Assuming user_id is UUID
    user_in: UserUpdate,
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """
    Update user (superuser only)
    """
    user = await async_crud_user.get(db, id=user_id) # Added await
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    user = await async_crud_user.update(db, db_obj=user, obj_in=user_in) # Added await
    return user

@router.get("/", response_model=List[UserResponse])
async def read_users( # Added async
    db: AsyncSession = Depends(get_async_db), # Changed Session to AsyncSession
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """
    Retrieve users (superuser only)
    """
    users = await async_crud_user.get_multi(db, skip=skip, limit=limit) # Added await
    return users

@router.delete("/{user_id}")
async def delete_user( # Added async
    *,
    db: AsyncSession = Depends(get_async_db), # Changed Session to AsyncSession
    user_id: str, # Assuming user_id is UUID
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """
    Delete user (superuser only)
    """
    user_to_delete = await async_crud_user.get(db, id=user_id) # Added await, changed var name
    if not user_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    
    # Soft delete by deactivating using the async CRUD method
    await async_crud_user.deactivate_user(db, user=user_to_delete) # Added await
    # db.commit() # Commit is handled by CRUDBase or endpoint
    
    return {"message": "User deactivated successfully"} # Changed message

@router.get("/search/", response_model=List[UserResponse])
async def search_users( # Added async
    *,
    db: AsyncSession = Depends(get_async_db), # Changed Session to AsyncSession
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=50, le=100),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """
    Search users (superuser only)
    """
    users = await async_crud_user.search_users(db, query=q, limit=limit) # Added await
    return users
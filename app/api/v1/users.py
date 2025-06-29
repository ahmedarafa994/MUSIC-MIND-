from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.crud import user as crud_user
from app.schemas import UserResponse, UserUpdate, UserProfile, UserStats
from app.core.security import get_current_active_user, get_current_superuser
from app.models.user import User

router = APIRouter()

@router.get("/me", response_model=UserProfile)
def read_user_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get current user profile
    """
    return current_user

@router.put("/me", response_model=UserResponse)
def update_user_me(
    *,
    db: Session = Depends(get_db),
    user_in: UserUpdate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Update current user
    """
    user = crud_user.update(db, db_obj=current_user, obj_in=user_in)
    return user

@router.get("/me/stats", response_model=UserStats)
def read_user_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get current user statistics
    """
    from app.crud import audio_file, agent_session
    
    # Get user statistics
    total_files = len(audio_file.get_by_user(db, user_id=current_user.id))
    storage_used_mb = audio_file.get_user_storage_usage(db, user_id=current_user.id)
    session_stats = agent_session.get_user_session_stats(db, user_id=current_user.id)
    
    return UserStats(
        total_files=total_files,
        total_sessions=session_stats["total_sessions"],
        total_processing_time=session_stats["average_execution_time"],
        total_cost=session_stats["total_cost"],
        storage_used_mb=storage_used_mb,
        api_calls_this_month=current_user.api_usage_count
    )

@router.get("/{user_id}", response_model=UserResponse)
def read_user(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """
    Get user by ID (superuser only)
    """
    user = crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=404, detail="User not found"
        )
    return user

@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """
    Update user (superuser only)
    """
    user = crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=404, detail="User not found"
        )
    user = crud_user.update(db, db_obj=user, obj_in=user_in)
    return user

@router.get("/", response_model=List[UserResponse])
def read_users(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """
    Retrieve users (superuser only)
    """
    users = crud_user.get_multi(db, skip=skip, limit=limit)
    return users

@router.delete("/{user_id}")
def delete_user(
    *,
    db: Session = Depends(get_db),
    user_id: str,
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """
    Delete user (superuser only)
    """
    user = crud_user.get(db, id=user_id)
    if not user:
        raise HTTPException(
            status_code=404, detail="User not found"
        )
    
    # Soft delete by deactivating
    user.is_active = False
    db.commit()
    
    return {"message": "User deleted successfully"}

@router.get("/search/", response_model=List[UserResponse])
def search_users(
    *,
    db: Session = Depends(get_db),
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=50, le=100),
    current_user: User = Depends(get_current_superuser),
) -> Any:
    """
    Search users (superuser only)
    """
    users = crud_user.search_users(db, query=q, limit=limit)
    return users
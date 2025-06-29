from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_active_superuser
from app.models.user import User
from app.crud.user import user as user_crud # Assuming user_crud is 'user'
from app.crud.audio_file import audio_file as audio_file_crud
from app.crud.agent_session import agent_session as agent_session_crud
from app.crud.api_key import api_key as api_key_crud
from app.schemas.user import UserResponse, UserUpdate # Assuming UserUpdate can be used by admin
from app.schemas.audio_file import AudioFileResponse
from app.schemas.agent_session import AgentSessionResponse
from app.schemas.api_key import APIKeyResponse
from app.schemas.main import SystemStats # Assuming a SystemStats schema exists or will be created

import structlog

logger = structlog.get_logger(__name__)
router = APIRouter()

@router.get("/users", response_model=List[UserResponse])
async def admin_list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    search: Optional[str] = Query(None, description="Search query for username, email, or full name")
):
    """
    (Admin) List all users. Supports pagination and search.
    """
    if search:
        users = await user_crud.search_users(db, query=search, skip=skip, limit=limit)
    else:
        users = await user_crud.get_multi(db, skip=skip, limit=limit)
    logger.info("Admin listed users", admin_user_id=current_user.id, count=len(users))
    return users

@router.get("/users/{user_id}", response_model=UserResponse)
async def admin_get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
):
    """
    (Admin) Get a specific user by ID.
    """
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    logger.info("Admin retrieved user", admin_user_id=current_user.id, target_user_id=user_id)
    return user

@router.put("/users/{user_id}", response_model=UserResponse)
async def admin_update_user(
    user_id: uuid.UUID,
    user_in: UserUpdate, # Or a more specific AdminUserUpdate schema
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
):
    """
    (Admin) Update a user's details.
    """
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    updated_user = await user_crud.update(db, db_obj=user, obj_in=user_in)
    logger.info("Admin updated user", admin_user_id=current_user.id, target_user_id=user_id)
    return updated_user

@router.patch("/users/{user_id}/activate")
async def admin_activate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
):
    """(Admin) Activate a user account."""
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_active:
        raise HTTPException(status_code=400, detail="User is already active")
    activated_user = await user_crud.activate_user(db, user=user)
    logger.info("Admin activated user", admin_user_id=current_user.id, target_user_id=user_id)
    return {"message": "User activated successfully", "user_id": activated_user.id}

@router.patch("/users/{user_id}/deactivate")
async def admin_deactivate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
):
    """(Admin) Deactivate a user account."""
    user = await user_crud.get(db, id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="User is already inactive")
    deactivated_user = await user_crud.deactivate_user(db, user=user)
    logger.info("Admin deactivated user", admin_user_id=current_user.id, target_user_id=user_id)
    return {"message": "User deactivated successfully", "user_id": deactivated_user.id}


@router.get("/system-stats", response_model=SystemStats) # Placeholder, SystemStats schema needed
async def admin_get_system_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser)
):
    """
    (Admin) Get overall system statistics.
    This is a placeholder and would require aggregation logic.
    """
    total_users = await user_crud.count(db)
    # total_files = await audio_file_crud.count(db)
    # active_sessions = len(await agent_session_crud.get_active_sessions(db))
    # Add more stats as needed...

    logger.info("Admin requested system stats", admin_user_id=current_user.id)
    return {
        "total_users": total_users,
        "total_files": 0, # Placeholder
        "active_sessions": 0, # Placeholder
        # "total_processing_time": 0.0,
        # "average_processing_time": 0.0,
        # "success_rate": 0.0,
        # "storage_used_gb": 0.0
    }

# Example: Endpoint to view all audio files (admin)
@router.get("/audio-files", response_model=List[AudioFileResponse])
async def admin_list_all_audio_files(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """(Admin) List all audio files in the system."""
    files = await audio_file_crud.get_multi(db, skip=skip, limit=limit)
    logger.info("Admin listed all audio files", admin_user_id=current_user.id, count=len(files))
    return files

# Example: Endpoint to view all agent sessions (admin)
@router.get("/agent-sessions", response_model=List[AgentSessionResponse])
async def admin_list_all_agent_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """(Admin) List all agent sessions in the system."""
    sessions = await agent_session_crud.get_multi(db, skip=skip, limit=limit)
    logger.info("Admin listed all agent sessions", admin_user_id=current_user.id, count=len(sessions))
    return sessions

# Example: Endpoint to view all API Keys (admin)
@router.get("/api-keys", response_model=List[APIKeyResponse])
async def admin_list_all_api_keys(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_superuser),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500)
):
    """(Admin) List all API keys in the system."""
    keys = await api_key_crud.get_multi(db, skip=skip, limit=limit)
    logger.info("Admin listed all API keys", admin_user_id=current_user.id, count=len(keys))
    return keys

# Add more admin-specific endpoints here, e.g.,
# - Triggering maintenance tasks
# - Viewing system logs (though usually done via log aggregation tools)
# - Managing global settings
# - Deleting any user's content (with caution)

import uuid # Add this import if not already present at the top
from typing import Optional # Add this import if not already present at the top

from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession # Changed import
import uuid
from datetime import datetime

from app.db.database import get_async_db # Changed import
from app.crud.agent_session import agent_session as async_crud_agent_session # Changed import
from app.crud.crud_audio_file import audio_file as async_crud_audio_file # For mastering session
from app.schemas import (
    AgentSessionCreate, AgentSessionResponse, AgentSessionDetail,
    MusicGenerationRequest, MusicGenerationResponse,
    MasteringRequest, # AudioAnalysisRequest not used yet
)
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.agent_session import SessionStatus # For checking is_complete

router = APIRouter()

@router.post("/", response_model=AgentSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session( # Added async
    *,
    db: AsyncSession = Depends(get_async_db), # Changed
    session_in: AgentSessionCreate,
    current_user: User = Depends(get_current_active_user),
    background_tasks: BackgroundTasks
) -> Any:
    """
    Create new agent session
    """
    if not current_user.can_make_api_call():
        raise HTTPException(
            status_code=429,
            detail="API usage limit exceeded"
        )
    
    session = await async_crud_agent_session.create_with_user(db, obj_in=session_in, user_id=current_user.id) # await
    
    current_user.increment_api_usage()
    db.add(current_user) # Add to session for commit
    await db.commit() # await
    await db.refresh(current_user) # refresh if needed
    
    background_tasks.add_task(process_session, session.id)
    
    return session

@router.get("/", response_model=List[AgentSessionResponse])
async def read_sessions( # Added async
    db: AsyncSession = Depends(get_async_db), # Changed
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Retrieve user's agent sessions
    """
    sessions = await async_crud_agent_session.get_by_user(db, user_id=current_user.id, skip=skip, limit=limit) # await
    return sessions

@router.get("/{session_id}", response_model=AgentSessionDetail)
async def read_session( # Added async
    *,
    db: AsyncSession = Depends(get_async_db), # Changed
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get agent session by ID
    """
    session = await async_crud_agent_session.get(db, id=session_id) # await
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return session

@router.post("/{session_id}/cancel")
async def cancel_session( # Added async
    *,
    db: AsyncSession = Depends(get_async_db), # Changed
    session_id: uuid.UUID,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Cancel agent session
    """
    session = await async_crud_agent_session.get(db, id=session_id) # await
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Check using Enum members for clarity
    if session.status in [SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.CANCELLED]:
        raise HTTPException(status_code=400, detail="Session already completed or cancelled")
    
    await async_crud_agent_session.cancel_session(db, session_id=session_id, reason=reason) # await
    
    return {"message": "Session cancelled successfully"}

@router.get("/active/", response_model=List[AgentSessionResponse])
async def read_active_sessions( # Added async
    db: AsyncSession = Depends(get_async_db), # Changed
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get user's active sessions
    """
    sessions = await async_crud_agent_session.get_active_sessions(db, user_id=current_user.id) # await
    return sessions

@router.post("/music-generation", response_model=MusicGenerationResponse)
async def create_music_generation_session( # Added async
    *,
    db: AsyncSession = Depends(get_async_db), # Changed
    request_data: MusicGenerationRequest,
    current_user: User = Depends(get_current_active_user),
    background_tasks: BackgroundTasks
) -> Any:
    """
    Create music generation session
    """
    if not current_user.can_make_api_call():
        raise HTTPException(
            status_code=429,
            detail="API usage limit exceeded"
        )
    
    session_data = AgentSessionCreate(
        session_type="music_generation",
        user_prompt=request_data.prompt,
        audio_file_id=request_data.reference_file_id
    )
    
    session = await async_crud_agent_session.create_with_user(db, obj_in=session_data, user_id=current_user.id) # await
    
    session.parsed_requirements = request_data.dict(exclude={"prompt", "reference_file_id"})
    db.add(session) # Add to session for commit
    # No need to commit here if create_with_user already commits.
    # If create_with_user doesn't commit, then: await db.commit(); await db.refresh(session)
    
    current_user.increment_api_usage()
    db.add(current_user)
    await db.commit() # This commit will save both session and user changes
    await db.refresh(session)
    await db.refresh(current_user)
    
    background_tasks.add_task(process_music_generation, session.id, request_data)
    
    return MusicGenerationResponse(
        session_id=session.id,
        status="queued",
        estimated_completion_time=300,
        queue_position=1
    )

@router.post("/mastering", response_model=MusicGenerationResponse)
async def create_mastering_session( # Added async
    *,
    db: AsyncSession = Depends(get_async_db), # Changed
    request_data: MasteringRequest,
    current_user: User = Depends(get_current_active_user),
    background_tasks: BackgroundTasks
) -> Any:
    """
    Create mastering session
    """
    if not current_user.can_make_api_call():
        raise HTTPException(
            status_code=429,
            detail="API usage limit exceeded"
        )
    
    audio_file = await async_crud_audio_file.get(db, id=request_data.audio_file_id) # await
    if not audio_file:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    if audio_file.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    session_data = AgentSessionCreate(
        session_type="mastering",
        user_prompt=f"Master audio file {audio_file.filename}",
        audio_file_id=request_data.audio_file_id
    )
    
    session = await async_crud_agent_session.create_with_user(db, obj_in=session_data, user_id=current_user.id) # await
    
    session.parsed_requirements = request_data.dict(exclude={"audio_file_id"})
    db.add(session)
    
    current_user.increment_api_usage()
    db.add(current_user)
    await db.commit() # Commit both session and user changes
    await db.refresh(session)
    await db.refresh(current_user)
    
    background_tasks.add_task(process_mastering, session.id, request_data)
    
    return MusicGenerationResponse(
        session_id=session.id,
        status="queued",
        estimated_completion_time=120,
        queue_position=1
    )

# Background task functions (already async, no changes needed for their signature)
async def process_session(session_id: uuid.UUID):
    """Process agent session in background"""
    # This would contain the actual AI processing logic
    # For now, we'll just simulate processing
    pass

async def process_music_generation(session_id: uuid.UUID, request_data: MusicGenerationRequest):
    """Process music generation in background"""
    # This would contain the actual music generation logic
    # For now, we'll just simulate processing
    pass

async def process_mastering(session_id: uuid.UUID, request_data: MasteringRequest):
    """Process mastering in background"""
    # This would contain the actual mastering logic
    # For now, we'll just simulate processing
    pass
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from app.db.database import get_db
from app.crud import agent_session as crud_session
from app.schemas import (
    AgentSessionCreate, AgentSessionResponse, AgentSessionDetail,
    MusicGenerationRequest, MusicGenerationResponse,
    MasteringRequest, AudioAnalysisRequest
)
from app.core.security import get_current_active_user
from app.models.user import User

router = APIRouter()

@router.post("/", response_model=AgentSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    *,
    db: Session = Depends(get_db),
    session_in: AgentSessionCreate,
    current_user: User = Depends(get_current_active_user),
    background_tasks: BackgroundTasks
) -> Any:
    """
    Create new agent session
    """
    # Check user limits
    if not current_user.can_make_api_call():
        raise HTTPException(
            status_code=429,
            detail="API usage limit exceeded"
        )
    
    # Create session
    session = crud_session.create_with_user(db, obj_in=session_in, user_id=current_user.id)
    
    # Increment user API usage
    current_user.increment_api_usage()
    db.commit()
    
    # Start session processing in background
    background_tasks.add_task(process_session, session.id)
    
    return session

@router.get("/", response_model=List[AgentSessionResponse])
def read_sessions(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Retrieve user's agent sessions
    """
    sessions = crud_session.get_by_user(db, user_id=current_user.id, skip=skip, limit=limit)
    return sessions

@router.get("/{session_id}", response_model=AgentSessionDetail)
def read_session(
    *,
    db: Session = Depends(get_db),
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get agent session by ID
    """
    session = crud_session.get(db, id=session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return session

@router.post("/{session_id}/cancel")
def cancel_session(
    *,
    db: Session = Depends(get_db),
    session_id: uuid.UUID,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Cancel agent session
    """
    session = crud_session.get(db, id=session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    if session.is_complete:
        raise HTTPException(status_code=400, detail="Session already completed")
    
    crud_session.cancel_session(db, session_id=session_id, reason=reason)
    
    return {"message": "Session cancelled successfully"}

@router.get("/active/", response_model=List[AgentSessionResponse])
def read_active_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get user's active sessions
    """
    sessions = crud_session.get_active_sessions(db, user_id=current_user.id)
    return sessions

@router.post("/music-generation", response_model=MusicGenerationResponse)
def create_music_generation_session(
    *,
    db: Session = Depends(get_db),
    request_data: MusicGenerationRequest,
    current_user: User = Depends(get_current_active_user),
    background_tasks: BackgroundTasks
) -> Any:
    """
    Create music generation session
    """
    # Check user limits
    if not current_user.can_make_api_call():
        raise HTTPException(
            status_code=429,
            detail="API usage limit exceeded"
        )
    
    # Create session
    session_data = AgentSessionCreate(
        session_type="music_generation",
        user_prompt=request_data.prompt,
        audio_file_id=request_data.reference_file_id
    )
    
    session = crud_session.create_with_user(db, obj_in=session_data, user_id=current_user.id)
    
    # Store generation parameters
    session.parsed_requirements = request_data.dict(exclude={"prompt", "reference_file_id"})
    db.commit()
    
    # Increment user API usage
    current_user.increment_api_usage()
    db.commit()
    
    # Start processing in background
    background_tasks.add_task(process_music_generation, session.id, request_data)
    
    return MusicGenerationResponse(
        session_id=session.id,
        status="queued",
        estimated_completion_time=300,  # 5 minutes estimate
        queue_position=1
    )

@router.post("/mastering", response_model=MusicGenerationResponse)
def create_mastering_session(
    *,
    db: Session = Depends(get_db),
    request_data: MasteringRequest,
    current_user: User = Depends(get_current_active_user),
    background_tasks: BackgroundTasks
) -> Any:
    """
    Create mastering session
    """
    # Check user limits
    if not current_user.can_make_api_call():
        raise HTTPException(
            status_code=429,
            detail="API usage limit exceeded"
        )
    
    # Validate audio file exists and belongs to user
    from app.crud import audio_file as crud_audio_file
    audio_file = crud_audio_file.get(db, id=request_data.audio_file_id)
    if not audio_file:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    if audio_file.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Create session
    session_data = AgentSessionCreate(
        session_type="mastering",
        user_prompt=f"Master audio file {audio_file.filename}",
        audio_file_id=request_data.audio_file_id
    )
    
    session = crud_session.create_with_user(db, obj_in=session_data, user_id=current_user.id)
    
    # Store mastering parameters
    session.parsed_requirements = request_data.dict(exclude={"audio_file_id"})
    db.commit()
    
    # Increment user API usage
    current_user.increment_api_usage()
    db.commit()
    
    # Start processing in background
    background_tasks.add_task(process_mastering, session.id, request_data)
    
    return MusicGenerationResponse(
        session_id=session.id,
        status="queued",
        estimated_completion_time=120,  # 2 minutes estimate
        queue_position=1
    )

# Background task functions
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
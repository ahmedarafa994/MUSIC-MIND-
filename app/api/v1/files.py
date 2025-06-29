from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Query, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession # Changed import
import uuid
import os
import aiofiles
import hashlib
from datetime import datetime

from app.db.database import get_async_db # Changed import
from app.crud import audio_file as crud_audio_file
from app.schemas import AudioFileResponse, AudioFileDetail, AudioFileUpdate, FileUploadResponse
from app.api.deps import get_current_active_user # Changed import
from app.core.config import settings
from app.models.user import User
from app.models.audio_file import AudioFile

router = APIRouter()

def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA-256 hash of file"""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

async def save_upload_file(upload_file: UploadFile, destination: str) -> None:
    """Save uploaded file to destination"""
    async with aiofiles.open(destination, 'wb') as f:
        while content := await upload_file.read(8192):
            await f.write(content)

def process_audio_metadata(file_path: str) -> dict:
    """Extract audio metadata from file"""
    try:
        import librosa
        import soundfile as sf
        
        # Get basic info
        info = sf.info(file_path)
        
        # Load audio for analysis
        y, sr = librosa.load(file_path, sr=None)
        
        return {
            "duration": info.duration,
            "sample_rate": info.samplerate,
            "channels": info.channels,
            "format": info.format,
            "codec": info.subtype,
            "bit_rate": None,  # Would need more advanced analysis
        }
    except Exception:
        # Fallback if librosa is not available
        return {
            "duration": None,
            "sample_rate": None,
            "channels": None,
            "format": None,
            "codec": None,
            "bit_rate": None,
        }

@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    *,
    db: AsyncSession = Depends(get_async_db),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    background_tasks: BackgroundTasks
) -> Any:
    """
    Upload audio file
    """
    # Validate file type
    if file.content_type not in settings.ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file.content_type} not allowed"
        )
    
    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset position
    
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE} bytes"
        )
    
    # Generate unique filename
    file_id = uuid.uuid4()
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{file_id}{file_extension}"
    file_path = os.path.join(settings.UPLOAD_PATH, filename)
    
    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_PATH, exist_ok=True)
    
    # Save file
    await save_upload_file(file, file_path)
    
    # Calculate file hash
    file_hash = calculate_file_hash(file_path)
    
    # Check for duplicate files
    existing_file = await crud_audio_file.get_by_hash(db, file_hash=file_hash) # Added await
    if existing_file and existing_file.user_id == current_user.id:
        # Remove uploaded file and return existing
        os.remove(file_path)
        return FileUploadResponse(
            file_id=existing_file.id,
            filename=existing_file.filename,
            file_size=existing_file.file_size
        )
    
    # Extract audio metadata
    metadata = process_audio_metadata(file_path)
    
    # Create database record
    audio_file_data = {
        "filename": filename,
        "original_filename": file.filename,
        "file_path": file_path,
        "file_size": file_size,
        "mime_type": file.content_type,
        "file_hash": file_hash,
        **metadata
    }
    
    audio_file = AudioFile(**audio_file_data, user_id=current_user.id, id=file_id)
    db.add(audio_file)
    await db.commit() # Added await
    await db.refresh(audio_file) # Added await
    
    return FileUploadResponse(
        file_id=audio_file.id,
        filename=audio_file.filename,
        file_size=audio_file.file_size
    )

@router.get("/", response_model=List[AudioFileResponse])
async def read_files( # Added async
    db: AsyncSession = Depends(get_async_db), # Changed Session to AsyncSession
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Retrieve user's audio files
    """
    files = await crud_audio_file.get_by_user(db, user_id=current_user.id, skip=skip, limit=limit) # Added await
    return files

@router.get("/public", response_model=List[AudioFileResponse])
async def read_public_files( # Added async
    db: AsyncSession = Depends(get_async_db), # Changed Session to AsyncSession
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve public audio files
    """
    files = await crud_audio_file.get_public_files(db, skip=skip, limit=limit) # Added await
    return files

@router.get("/{file_id}", response_model=AudioFileDetail)
async def read_file( # Added async
    *,
    db: AsyncSession = Depends(get_async_db), # Changed Session to AsyncSession
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get audio file by ID
    """
    audio_file = await crud_audio_file.get(db, id=file_id) # Added await
    if not audio_file:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    if not audio_file.can_be_accessed_by_user(current_user.id): # Model method, likely sync
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return audio_file

@router.put("/{file_id}", response_model=AudioFileResponse)
async def update_file( # Added async
    *,
    db: AsyncSession = Depends(get_async_db), # Changed Session to AsyncSession
    file_id: uuid.UUID,
    file_in: AudioFileUpdate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Update audio file
    """
    audio_file = await crud_audio_file.get(db, id=file_id) # Added await
    if not audio_file:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    if audio_file.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    audio_file = await crud_audio_file.update(db, db_obj=audio_file, obj_in=file_in) # Added await
    return audio_file

@router.delete("/{file_id}")
async def delete_file( # Added async
    *,
    db: AsyncSession = Depends(get_async_db), # Changed Session to AsyncSession
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Delete audio file
    """
    audio_file = await crud_audio_file.get(db, id=file_id) # Added await
    if not audio_file:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    if audio_file.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Soft delete
    await crud_audio_file.soft_delete(db, file_id=file_id) # Added await
    
    return {"message": "Audio file deleted successfully"}

@router.get("/{file_id}/download")
async def download_file(
    *,
    db: Session = Depends(get_db),
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Download audio file
    """
    audio_file = crud_audio_file.get(db, id=file_id)
    if not audio_file:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    if not audio_file.can_be_accessed_by_user(current_user.id):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    if not os.path.exists(audio_file.file_path):
        raise HTTPException(status_code=404, detail="Physical file not found")
    
    # Increment download count
    crud_audio_file.increment_download_count(db, file_id=file_id)
    
    return FileResponse(
        path=audio_file.file_path,
        filename=audio_file.original_filename,
        media_type=audio_file.mime_type
    )

@router.post("/{file_id}/play")
def play_file(
    *,
    db: Session = Depends(get_db),
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Record file play event
    """
    audio_file = crud_audio_file.get(db, id=file_id)
    if not audio_file:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    if not audio_file.can_be_accessed_by_user(current_user.id):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Increment play count
    crud_audio_file.increment_play_count(db, file_id=file_id)
    
    return {"message": "Play count updated"}

@router.get("/search/", response_model=List[AudioFileResponse])
def search_files(
    *,
    db: Session = Depends(get_db),
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=50, le=100),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Search user's audio files
    """
    files = crud_audio_file.search_files(db, user_id=current_user.id, query=q, limit=limit)
    return files
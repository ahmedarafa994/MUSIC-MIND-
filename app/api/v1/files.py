from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Query, BackgroundTasks
from fastapi.responses import FileResponse # StreamingResponse not used, can be removed if not planned
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import os
import aiofiles # For async file saving
import hashlib
from datetime import datetime
from fastapi.concurrency import run_in_threadpool # For blocking functions

from app.db.database import get_async_db
from app.crud.crud_audio_file import audio_file as async_crud_audio_file # Renamed for clarity
from app.schemas import AudioFileResponse, AudioFileDetail, AudioFileUpdate, FileUploadResponse
from app.api.deps import get_current_active_user
from app.core.config import settings
from app.models.user import User
from app.models.audio_file import AudioFile

router = APIRouter()

async def calculate_file_hash_async(file_path: str) -> str:
    """Calculate SHA-256 hash of file asynchronously."""
    return await run_in_threadpool(calculate_file_hash_sync, file_path)

def calculate_file_hash_sync(file_path: str) -> str:
    """Synchronous Calculate SHA-256 hash of file"""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

async def save_upload_file(upload_file: UploadFile, destination: str) -> None:
    """Save uploaded file to destination"""
    # Ensure destination directory exists (synchronous, but usually fast and acceptable at this stage)
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    async with aiofiles.open(destination, 'wb') as f:
        while content := await upload_file.read(8192): # Read in chunks
            await f.write(content)

async def process_audio_metadata_async(file_path: str) -> dict:
    """Extract audio metadata from file asynchronously."""
    return await run_in_threadpool(process_audio_metadata_sync, file_path)

def process_audio_metadata_sync(file_path: str) -> dict:
    """Synchronous Extract audio metadata from file"""
    try:
        import librosa
        import soundfile as sf
        
        info = sf.info(file_path)
        y, sr = librosa.load(file_path, sr=None) # This is the blocking part
        
        return {
            "duration": info.duration,
            "sample_rate": info.samplerate,
            "channels": info.channels,
            "format": info.format,
            "codec": info.subtype,
            "bit_rate": None,
        }
    except Exception:
        return {
            "duration": None, "sample_rate": None, "channels": None,
            "format": None, "codec": None, "bit_rate": None,
        }

@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    *,
    db: AsyncSession = Depends(get_async_db),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    # background_tasks: BackgroundTasks # Not used in current logic
) -> Any:
    """
    Upload audio file
    """
    if file.content_type not in settings.ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=400, detail=f"File type {file.content_type} not allowed")
    
    # Get file size properly from UploadFile
    contents = await file.read()
    file_size = len(contents)
    await file.seek(0) # Reset file pointer after reading

    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail=f"File size exceeds maximum: {settings.MAX_UPLOAD_SIZE} bytes")
    
    file_id = uuid.uuid4()
    file_extension = os.path.splitext(file.filename)[1]
    filename_on_disk = f"{file_id}{file_extension}"
    file_path = os.path.join(settings.UPLOAD_PATH, filename_on_disk)
    
    await save_upload_file(file, file_path) # save_upload_file already ensures directory
    
    file_hash = await calculate_file_hash_async(file_path)
    
    existing_file = await async_crud_audio_file.get_by_field(db, field="file_hash", value=file_hash) # More generic
    if existing_file and existing_file.user_id == current_user.id:
        await run_in_threadpool(os.remove, file_path) # Async remove
        return FileUploadResponse(
            file_id=existing_file.id,
            filename=existing_file.original_filename, # Use original for response
            file_size=existing_file.file_size
        )
    
    metadata = await process_audio_metadata_async(file_path)
    
    audio_file_schema = AudioFileCreate(
        filename=file.filename, # User's desired filename or original, system uses file_id based name
        genre=metadata.get("genre"), # Example, metadata might not provide this directly
        mood=metadata.get("mood"),
        is_public=False, # Default
        # Populate other fields from AudioFileCreate as needed
    )

    # Use the specific CRUD method for creating with all details
    audio_file_db = await async_crud_audio_file.create_with_user_and_details(
        db,
        obj_in=audio_file_schema, # Pass the schema
        user_id=current_user.id,
        original_filename=file.filename,
        file_size=file_size,
        mime_type=file.content_type,
        file_path=file_path, # Path on disk
        # Add other metadata from 'metadata' dict to specific model fields
        duration=metadata.get("duration"),
        sample_rate=metadata.get("sample_rate"),
        channels=metadata.get("channels"),
        # format=metadata.get("format"), # This is already covered by mime_type or could be more specific
        # codec=metadata.get("codec"),
        file_hash=file_hash,
        # id=file_id # id is generated by model default
    )
    
    return FileUploadResponse(
        file_id=audio_file_db.id,
        filename=audio_file_db.original_filename,
        file_size=audio_file_db.file_size
    )

@router.get("/", response_model=List[AudioFileResponse])
async def read_files(
    db: AsyncSession = Depends(get_async_db),
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    files = await async_crud_audio_file.get_by_user(db, user_id=current_user.id, skip=skip, limit=limit)
    return files

@router.get("/public", response_model=List[AudioFileResponse])
async def read_public_files(
    db: AsyncSession = Depends(get_async_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    # Assuming get_public_files exists or is added to CRUDAudioFile
    files = await async_crud_audio_file.get_multi_by_field(db, field="is_public", value=True, skip=skip, limit=limit)
    return files

@router.get("/{file_id}", response_model=AudioFileDetail)
async def read_file(
    *,
    db: AsyncSession = Depends(get_async_db),
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    audio_file = await async_crud_audio_file.get(db, id=file_id)
    if not audio_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found")
    
    if not audio_file.is_public and audio_file.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    
    return audio_file

@router.put("/{file_id}", response_model=AudioFileResponse)
async def update_file(
    *,
    db: AsyncSession = Depends(get_async_db),
    file_id: uuid.UUID,
    file_in: AudioFileUpdate,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    audio_file = await async_crud_audio_file.get(db, id=file_id)
    if not audio_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found")
    
    if audio_file.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    
    audio_file = await async_crud_audio_file.update(db, db_obj=audio_file, obj_in=file_in)
    return audio_file

@router.delete("/{file_id}", status_code=status.HTTP_200_OK) # Return 200 for successful delete
async def delete_file(
    *,
    db: AsyncSession = Depends(get_async_db),
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    audio_file = await async_crud_audio_file.get(db, id=file_id)
    if not audio_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found")
    
    if audio_file.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    
    await async_crud_audio_file.soft_delete(db, id=file_id) # Use id for soft_delete
    
    # Optionally, delete physical file if it's a soft delete and policy dictates
    # await run_in_threadpool(os.remove, audio_file.file_path)

    return {"message": "Audio file deleted successfully"}

@router.get("/{file_id}/download")
async def download_file(
    *,
    db: AsyncSession = Depends(get_async_db), # Changed to async
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    audio_file = await async_crud_audio_file.get(db, id=file_id) # await
    if not audio_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found")
    
    if not audio_file.is_public and audio_file.user_id != current_user.id: # Check permissions
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    
    if not await run_in_threadpool(os.path.exists, audio_file.file_path): # Async check
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Physical file not found")
    
    await async_crud_audio_file.increment_download_count(db, audio_file_id=file_id) # await
    
    return FileResponse(
        path=audio_file.file_path,
        filename=audio_file.original_filename,
        media_type=audio_file.mime_type
    )

@router.post("/{file_id}/play", status_code=status.HTTP_200_OK)
async def play_file( # Changed to async
    *,
    db: AsyncSession = Depends(get_async_db), # Changed to async
    file_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
) -> Any:
    audio_file = await async_crud_audio_file.get(db, id=file_id) # await
    if not audio_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found")
    
    if not audio_file.is_public and audio_file.user_id != current_user.id: # Check permissions
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")
    
    await async_crud_audio_file.increment_play_count(db, audio_file_id=file_id) # await
    
    return {"message": "Play count updated"}

@router.get("/search/", response_model=List[AudioFileResponse])
async def search_files( # Changed to async
    *,
    db: AsyncSession = Depends(get_async_db), # Changed to async
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(default=50, le=100),
    current_user: User = Depends(get_current_active_user),
) -> Any:
    # Assuming CRUDAudioFile has an async search_files method
    # If not, it would need to be implemented based on CRUDBase.search or similar
    files = await async_crud_audio_file.search(db, query=q, fields=["original_filename", "filename", "genre", "mood"], limit=limit)
    # Filter further by user_id if search doesn't handle it
    user_files = [f for f in files if f.user_id == current_user.id or f.is_public]
    return user_files
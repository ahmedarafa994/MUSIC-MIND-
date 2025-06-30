from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession # Changed import
import uuid
import os
import asyncio
import aiofiles # For async file operations

from app.db.database import get_async_db # Changed import
from app.core.security import get_current_active_user
from app.models.user import User
from app.services.music_agent import music_agent
from app.schemas import BaseSchema
from pydantic import Field
# Assuming async CRUD for user is available for updating API usage
from app.crud.crud_user import user as async_crud_user


router = APIRouter()

class MusicGenerationRequest(BaseSchema):
    prompt: str = Field(..., min_length=10, max_length=2000, description="Text prompt for music generation")
    genre: Optional[str] = Field(None, description="Desired music genre")
    mood: Optional[str] = Field(None, description="Desired mood/emotion")
    duration: Optional[int] = Field(30, ge=10, le=300, description="Duration in seconds")
    style: Optional[str] = Field("balanced", description="Processing style: balanced, creative, professional")
    tempo: Optional[int] = Field(None, ge=60, le=200, description="Tempo in BPM")
    key: Optional[str] = Field(None, description="Musical key")

class MusicProcessingRequest(BaseSchema):
    operation: str = Field(..., description="Type of operation: enhance, master, style_transfer")
    style: Optional[str] = Field("balanced", description="Processing style")
    target_genre: Optional[str] = Field(None, description="Target genre for style transfer")
    enhancement_level: Optional[str] = Field("moderate", description="Enhancement level: light, moderate, heavy")

class MusicResponse(BaseSchema):
    success: bool
    message: str
    job_id: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    processing_time: Optional[float] = None
    cost: Optional[float] = None

@router.post("/generate", response_model=MusicResponse)
async def generate_music(
    request: MusicGenerationRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db) # Changed
):
    """Generate music from text prompt using AI"""
    
    if not current_user.can_make_api_call(): # This model method should be fine
        raise HTTPException(
            status_code=429,
            detail="API usage limit exceeded"
        )
    
    try:
        context = {
            "user_id": str(current_user.id),
            "operation": "generation",
            "parameters": {
                "genre": request.genre,
                "mood": request.mood,
                "duration": request.duration,
                "tempo": request.tempo,
                "key": request.key,
                "style": request.style
            }
        }
        
        result = await music_agent.process_request(request.prompt, context)
        
        # Update user API usage
        current_user.increment_api_usage() # Modifies the object
        db.add(current_user) # Add to session to track changes
        await db.commit() # Persist changes
        await db.refresh(current_user) # Refresh if needed
        
        if result.get("success", False):
            return MusicResponse(
                success=True,
                message="Music generated successfully",
                results=result.get("results", {}),
                processing_time=result.get("execution_metadata", {}).get("total_duration", 0),
                cost=result.get("execution_metadata", {}).get("total_cost", 0)
            )
        else:
            return MusicResponse(
                success=False,
                message=result.get("message", "Music generation failed")
            )
            
    except Exception as e:
        # Consider rolling back db changes if an error occurs after db.commit()
        # but before the function returns, though here commit is the last db op.
        raise HTTPException(
            status_code=500,
            detail=f"Music generation failed: {str(e)}"
        )

@router.post("/process-file", response_model=MusicResponse)
async def process_audio_file(
    file: UploadFile = File(...),
    operation: str = Form(...),
    style: str = Form("balanced"),
    target_genre: Optional[str] = Form(None),
    enhancement_level: str = Form("moderate"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db) # Changed
):
    """Process uploaded audio file with AI"""
    
    if not current_user.can_make_api_call():
        raise HTTPException(
            status_code=429,
            detail="API usage limit exceeded"
        )
    
    if not file.content_type.startswith('audio/'):
        raise HTTPException(
            status_code=400,
            detail="File must be an audio file"
        )
    
    temp_dir = "/tmp/music_processing" # Define a base temp directory
    os.makedirs(temp_dir, exist_ok=True) # Ensure temp dir exists

    file_id = str(uuid.uuid4())
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{file_id}{file_extension}"
    file_path = os.path.join(temp_dir, filename)

    try:
        async with aiofiles.open(file_path, "wb") as buffer: # Async file write
            content = await file.read()
            await buffer.write(content)
        
        if operation == "enhance":
            prompt = f"Enhance this audio file with {enhancement_level} enhancement level"
        elif operation == "master":
            prompt = f"Master this audio file with {style} style"
        elif operation == "style_transfer" and target_genre:
            prompt = f"Transform this audio to {target_genre} style"
        else:
            prompt = f"Process this audio file with {operation} operation"
        
        context = {
            "user_id": str(current_user.id),
            "operation": operation,
            "input_file": file_path, # Pass path to agent
            "parameters": {
                "style": style,
                "target_genre": target_genre,
                "enhancement_level": enhancement_level
            }
        }
        
        result = await music_agent.process_request(prompt, context)
        
        current_user.increment_api_usage()
        db.add(current_user)
        await db.commit()
        await db.refresh(current_user)
        
        if result.get("success", False):
            return MusicResponse(
                success=True,
                message="Audio processed successfully",
                results=result.get("results", {}),
                processing_time=result.get("execution_metadata", {}).get("total_duration", 0),
                cost=result.get("execution_metadata", {}).get("total_cost", 0)
            )
        else:
            return MusicResponse(
                success=False,
                message=result.get("message", "Audio processing failed")
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Audio processing failed: {str(e)}"
        )
    finally: # Ensure cleanup of temp file
        if os.path.exists(file_path):
            try:
                await aiofiles.os.remove(file_path) # Async remove
            except Exception as e_remove:
                # Log error during cleanup, but don't override original exception
                # (Requires logger to be imported and configured)
                # logger.error(f"Failed to remove temp file {file_path}: {e_remove}")
                pass


@router.get("/agent/status")
async def get_agent_status(
    current_user: User = Depends(get_current_active_user)
):
    """Get current status of the music agent"""
    
    try:
        status = await music_agent.get_agent_status()
        return status
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get agent status: {str(e)}"
        )

@router.get("/capabilities")
async def get_music_capabilities():
    """Get available music processing capabilities"""
    
    try:
        available_services = await music_agent._get_available_tools()
        
        capabilities = {
            "text_to_music": [],
            "audio_enhancement": [],
            "style_transfer": [],
            "melody_generation": [],
            "rhythm_generation": []
        }
        
        for tool in available_services:
            tool_capabilities = tool.get("capabilities", [])
            
            if "text_to_music" in tool_capabilities:
                capabilities["text_to_music"].append(tool["name"])
            if "audio_enhancement" in tool_capabilities:
                capabilities["audio_enhancement"].append(tool["name"])
            if "style_transfer" in tool_capabilities:
                capabilities["style_transfer"].append(tool["name"])
            if "melody_generation" in tool_capabilities:
                capabilities["melody_generation"].append(tool["name"])
            if "rhythm_generation" in tool_capabilities:
                capabilities["rhythm_generation"].append(tool["name"])
        
        return {
            "capabilities": capabilities,
            "total_services": len(available_services),
            "supported_operations": [
                "generate", "enhance", "master", "style_transfer", 
                "melody_generation", "rhythm_enhancement"
            ],
            "supported_formats": ["mp3", "wav", "flac", "aac", "ogg"],
            "max_duration": 300,
            "max_file_size": "100MB"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get capabilities: {str(e)}"
        )
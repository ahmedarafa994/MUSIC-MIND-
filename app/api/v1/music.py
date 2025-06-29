from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
import uuid
import os
import asyncio

from app.db.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.services.music_agent import music_agent
from app.schemas import BaseSchema
from pydantic import Field

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
    db: Session = Depends(get_db)
):
    """Generate music from text prompt using AI"""
    
    # Check user limits
    if not current_user.can_make_api_call():
        raise HTTPException(
            status_code=429,
            detail="API usage limit exceeded"
        )
    
    try:
        # Build context for the music agent
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
        
        # Process request through music agent
        result = await music_agent.process_request(request.prompt, context)
        
        # Update user API usage
        current_user.increment_api_usage()
        db.commit()
        
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
    db: Session = Depends(get_db)
):
    """Process uploaded audio file with AI"""
    
    # Check user limits
    if not current_user.can_make_api_call():
        raise HTTPException(
            status_code=429,
            detail="API usage limit exceeded"
        )
    
    # Validate file type
    if not file.content_type.startswith('audio/'):
        raise HTTPException(
            status_code=400,
            detail="File must be an audio file"
        )
    
    try:
        # Save uploaded file
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1]
        filename = f"{file_id}{file_extension}"
        file_path = f"/tmp/{filename}"
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Build processing request
        if operation == "enhance":
            prompt = f"Enhance this audio file with {enhancement_level} enhancement level"
        elif operation == "master":
            prompt = f"Master this audio file with {style} style"
        elif operation == "style_transfer" and target_genre:
            prompt = f"Transform this audio to {target_genre} style"
        else:
            prompt = f"Process this audio file with {operation} operation"
        
        # Build context
        context = {
            "user_id": str(current_user.id),
            "operation": operation,
            "input_file": file_path,
            "parameters": {
                "style": style,
                "target_genre": target_genre,
                "enhancement_level": enhancement_level
            }
        }
        
        # Process through music agent
        result = await music_agent.process_request(prompt, context)
        
        # Update user API usage
        current_user.increment_api_usage()
        db.commit()
        
        # Clean up uploaded file
        try:
            os.remove(file_path)
        except:
            pass
        
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
        # Clean up file on error
        try:
            os.remove(file_path)
        except:
            pass
            
        raise HTTPException(
            status_code=500,
            detail=f"Audio processing failed: {str(e)}"
        )

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
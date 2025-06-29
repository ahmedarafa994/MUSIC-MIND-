from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, UploadFile, File
from sqlalchemy.orm import Session
import uuid
import os

from app.db.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.services.master_chain_orchestrator import orchestrator
from app.schemas import BaseSchema
from pydantic import Field

router = APIRouter()

class ProcessingRequest(BaseSchema):
    workflow_type: str = Field(default="auto", description="Workflow type: auto, custom, or preset")
    preset_name: str = Field(default="standard_mastering", description="Preset name if using preset workflow")
    custom_steps: list = Field(default=[], description="Custom steps if using custom workflow")
    creativity_level: str = Field(default="medium", description="Creativity level: low, medium, high")
    target_genre: str = Field(default="auto", description="Target genre for processing")
    quality_priority: str = Field(default="balanced", description="Quality priority: speed, balanced, quality")

    # Mastering specific options
    mastering_service_type: Optional[str] = Field(
        default="landr",
        description="Mastering service: 'landr' or 'matchering'"
    )
    landr_mastering_options: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Options for LANDR mastering (e.g., {'intensity': 'medium', 'style': 'balanced'})"
    )
    # For Matchering, reference_file_id would point to an already uploaded file.
    # output_formats is a list of dicts, e.g., [{'type': 'pcm16', 'filename_suffix': '_16bit.wav'}]
    matchering_mastering_options: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Options for Matchering (e.g., {'reference_audio_file_id': 'uuid', 'output_formats': []})"
    )

class ProcessingResponse(BaseSchema):
    job_id: str
    status: str
    message: str

class JobStatusResponse(BaseSchema):
    id: str
    status: str
    progress: float
    current_step: str
    created_at: str
    updated_at: str
    estimated_completion: str = None
    error_message: str = None
    intermediate_results: list = None
    final_results: dict = None

@router.post("/upload-and-process", response_model=ProcessingResponse)
async def upload_and_process_audio(
    file: UploadFile = File(...),
    reference_file: Optional[UploadFile] = File(None, description="Reference audio file for Matchering"),
    workflow_type: str = "auto",
    preset_name: str = "standard_mastering",
    creativity_level: str = "medium",
    target_genre: str = "auto",
    mastering_service_type: Optional[str] = "landr",
    landr_mastering_options_json: Optional[str] = Field(None, description="JSON string for LANDR options"),
    matchering_mastering_options_json: Optional[str] = Field(None, description="JSON string for Matchering options (e.g. output_formats)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload audio file (and optional reference file) and start processing."""
    
    import json

    # Validate target file type
    if not file.content_type.startswith('audio/'):
        raise HTTPException(status_code=400, detail="Target file must be an audio file")
    
    # Save target uploaded file
    target_file_id = str(uuid.uuid4())
    target_file_extension = os.path.splitext(file.filename)[1]
    target_filename = f"{target_file_id}{target_file_extension}"
    # Consider using a settings-defined upload path
    target_file_path = os.path.join(settings.UPLOAD_PATH, target_filename)
    os.makedirs(settings.UPLOAD_PATH, exist_ok=True)
    
    with open(target_file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # Handle reference file for Matchering
    reference_file_path = None
    if mastering_service_type == "matchering" and reference_file:
        if not reference_file.content_type.startswith('audio/'):
            # Clean up target file if reference is invalid
            os.remove(target_file_path)
            raise HTTPException(status_code=400, detail="Reference file must be an audio file")

        ref_file_id = str(uuid.uuid4())
        ref_file_extension = os.path.splitext(reference_file.filename)[1]
        ref_filename = f"ref_{ref_file_id}{ref_file_extension}"
        reference_file_path = os.path.join(settings.UPLOAD_PATH, ref_filename)

        with open(reference_file_path, "wb") as buffer:
            content = await reference_file.read()
            buffer.write(content)
    elif mastering_service_type == "matchering" and not reference_file:
        # Clean up target file if reference is required but not provided
        os.remove(target_file_path)
        raise HTTPException(status_code=400, detail="Reference file is required for Matchering service.")

    # Parse JSON options
    parsed_landr_options = None
    if landr_mastering_options_json:
        try:
            parsed_landr_options = json.loads(landr_mastering_options_json)
        except json.JSONDecodeError:
            if reference_file_path: os.remove(reference_file_path) # Cleanup
            os.remove(target_file_path) # Cleanup
            raise HTTPException(status_code=400, detail="Invalid JSON format for LANDR options.")

    parsed_matchering_options = {} # Default to empty dict
    if matchering_mastering_options_json:
        try:
            parsed_matchering_options = json.loads(matchering_mastering_options_json)
        except json.JSONDecodeError:
            if reference_file_path: os.remove(reference_file_path) # Cleanup
            os.remove(target_file_path) # Cleanup
            raise HTTPException(status_code=400, detail="Invalid JSON format for Matchering options.")
    
    # Add reference file path to matchering options if it was uploaded
    if reference_file_path:
        parsed_matchering_options["reference_audio_file_path"] = reference_file_path


    # Create workflow configuration
    workflow_config = {
        "type": workflow_type,
        "preset": preset_name,
        "creativity": creativity_level,
        "target_genre": target_genre,
        "steps": [],  # For custom workflows
        "mastering_settings": {
            "service_type": mastering_service_type,
            "landr_options": parsed_landr_options,
            "matchering_options": parsed_matchering_options,
        }
    }
    
    # Start processing job
    try:
        job_id = await orchestrator.create_processing_job(
            user_id=str(current_user.id),
            project_id=str(uuid.uuid4()),  # Generate project ID
            input_audio_path=file_path,
            workflow_config=workflow_config
        )
        
        return ProcessingResponse(
            job_id=job_id,
            status="started",
            message="Processing job started successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start processing: {str(e)}"
        )

@router.post("/process-existing", response_model=ProcessingResponse)
async def process_existing_audio(
    request: ProcessingRequest,
    audio_file_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Process an existing audio file"""
    
    # In a real implementation, you'd fetch the file from database
    # For now, we'll simulate with a dummy path
    file_path = f"/tmp/existing_{audio_file_id}.wav"
    
    workflow_config = {
        "type": request.workflow_type,
        "preset": request.preset_name,
        "creativity": request.creativity_level,
        "target_genre": request.target_genre,
        "steps": request.custom_steps,
        # Mastering specific configurations
        "mastering_settings": {
            "service_type": request.mastering_service_type,
            "landr_options": request.landr_mastering_options,
            "matchering_options": request.matchering_mastering_options,
             # Note: For Matchering, orchestrator will need to resolve reference_audio_file_id to a path
        }
    }
    
    try:
        job_id = await orchestrator.create_processing_job(
            user_id=str(current_user.id),
            project_id=str(uuid.uuid4()),
            input_audio_path=file_path,
            workflow_config=workflow_config
        )
        
        return ProcessingResponse(
            job_id=job_id,
            status="started",
            message="Processing job started successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start processing: {str(e)}"
        )

@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get status of a processing job"""
    
    job_status = await orchestrator.get_job_status(job_id)
    
    if not job_status:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )
    
    return JobStatusResponse(**job_status)

@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Cancel a processing job"""
    
    success = await orchestrator.cancel_job(job_id)
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Job cannot be cancelled or not found"
        )
    
    return {"message": "Job cancelled successfully"}

@router.get("/presets")
async def get_available_presets():
    """Get list of available workflow presets"""
    
    presets = [
        {
            "name": "standard_mastering",
            "display_name": "Standard Mastering",
            "description": "Professional mastering workflow for most music types",
            "estimated_time": "2-3 minutes",
            "best_for": ["pop", "rock", "electronic", "general"]
        },
        {
            "name": "creative_enhancement",
            "display_name": "Creative Enhancement",
            "description": "Creative processing with style transfer and enhancement",
            "estimated_time": "4-5 minutes",
            "best_for": ["experimental", "electronic", "ambient"]
        },
        {
            "name": "generation_from_scratch",
            "display_name": "Generate from Scratch",
            "description": "Complete music generation from text or audio prompts",
            "estimated_time": "5-8 minutes",
            "best_for": ["new_compositions", "backing_tracks", "demos"]
        },
        {
            "name": "vocal_enhancement",
            "display_name": "Vocal Enhancement",
            "description": "Specialized processing for vocal-heavy tracks",
            "estimated_time": "2-3 minutes",
            "best_for": ["vocals", "singer_songwriter", "acoustic"]
        }
    ]
    
    return {"presets": presets}

@router.get("/models/status")
async def get_model_status(
    current_user: User = Depends(get_current_active_user)
):
    """Get status of all AI models"""
    
    from app.services.model_services import ModelServiceManager
    
    model_manager = ModelServiceManager()
    
    model_status = {}
    for model_name in model_manager.service_endpoints.keys():
        is_available = await model_manager.is_model_available(model_name)
        capabilities = await model_manager.get_model_capabilities(model_name)
        
        model_status[model_name] = {
            "available": is_available,
            "capabilities": capabilities,
            "endpoint": model_manager.service_endpoints[model_name]
        }
    
    return {"models": model_status}
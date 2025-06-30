import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field # Added Field
from app.services.master_chain_orchestrator import ProcessingStatus # Reuse enum
# Assuming a common BaseSchema for Config: from_attributes = True
from .common import BaseSchema as CommonBaseSchema # Use alias to avoid Pydantic BaseModel conflict

class ProcessingJobBase(CommonBaseSchema): # Inherit from common BaseSchema
    user_id: uuid.UUID
    project_id: Optional[uuid.UUID] = None
    input_audio_path: str = Field(..., max_length=1024)
    workflow_config: Optional[Dict[str, Any]] = None
    status: str = Field(default=ProcessingStatus.PENDING.value, max_length=50)
    progress: float = Field(default=0.0, ge=0.0, le=100.0)
    current_step: Optional[str] = Field(None, max_length=255)
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None # Text field, no max_length from model
    intermediate_results: Optional[List[Dict[str, Any]]] = None
    final_results: Optional[Dict[str, Any]] = None

class ProcessingJobCreate(ProcessingJobBase):
    # id can be added here if client can suggest an ID, otherwise DB generates
    pass

class ProcessingJobUpdate(CommonBaseSchema): # Inherit from common BaseSchema
    status: Optional[str] = Field(None, max_length=50)
    progress: Optional[float] = Field(None, ge=0.0, le=100.0)
    current_step: Optional[str] = Field(None, max_length=255)
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None
    intermediate_results: Optional[List[Dict[str, Any]]] = None
    final_results: Optional[Dict[str, Any]] = None
    # Add other fields that can be updated, ensure they match model's mutability

class ProcessingJobResponse(ProcessingJobBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    # No Config class needed if inherited from CommonBaseSchema which should have it
    # class Config:
    # from_attributes = True (already in CommonBaseSchema)

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from .common import BaseSchema, SessionStatus, SessionType

# Base agent session schemas
class AgentSessionBase(BaseSchema):
    session_type: SessionType
    user_prompt: str = Field(..., min_length=10, max_length=5000)
    priority: int = Field(default=5, ge=1, le=10)

class AgentSessionCreate(AgentSessionBase):
    audio_file_id: Optional[uuid.UUID] = None
    max_execution_time: int = Field(default=3600, ge=60, le=7200)
    parameters: Optional[Dict[str, Any]] = None

class AgentSessionUpdate(BaseSchema):
    user_prompt: Optional[str] = Field(None, min_length=10, max_length=5000)
    priority: Optional[int] = Field(None, ge=1, le=10)
    max_execution_time: Optional[int] = Field(None, ge=60, le=7200)
    parameters: Optional[Dict[str, Any]] = None

class AgentSessionResponse(AgentSessionBase):
    id: uuid.UUID
    user_id: uuid.UUID
    audio_file_id: Optional[uuid.UUID]
    status: SessionStatus
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    cancelled_tasks: int
    total_cost: float
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    estimated_completion_time: Optional[datetime]

class AgentSessionDetail(AgentSessionResponse):
    parsed_requirements: Optional[Dict[str, Any]]
    selected_tools: Optional[List[str]]
    execution_plan: Optional[Dict[str, Any]]
    total_execution_time: Optional[float]
    queue_time: Optional[float]
    processing_time: Optional[float]
    tokens_used: int
    compute_units_used: float
    api_costs: Optional[Dict[str, float]]
    output_file_paths: Optional[List[str]]
    final_response: Optional[str]
    quality_metrics: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]
    error_message: Optional[str]
    error_code: Optional[str]
    retry_count: int
    max_retries: int

# Music generation specific schemas
class MusicGenerationRequest(BaseSchema):
    prompt: str = Field(..., min_length=10, max_length=2000)
    genre: Optional[str] = Field(None, max_length=100)
    mood: Optional[str] = Field(None, max_length=100)
    tempo: Optional[int] = Field(None, ge=60, le=200)
    duration: Optional[int] = Field(None, ge=10, le=300)  # seconds
    key: Optional[str] = Field(None, max_length=10)
    time_signature: Optional[str] = Field(None, max_length=10)
    instruments: Optional[List[str]] = Field(None, max_items=10)
    style: Optional[str] = Field(None, max_length=100)
    reference_file_id: Optional[uuid.UUID] = None
    creativity_level: float = Field(default=0.7, ge=0.0, le=1.0)
    quality_preset: str = Field(default="balanced", regex="^(fast|balanced|high_quality)$")

class MusicGenerationResponse(BaseSchema):
    session_id: uuid.UUID
    status: str
    estimated_completion_time: Optional[int]  # seconds
    queue_position: Optional[int]
    cost_estimate: Optional[float]

# Audio enhancement schemas
class AudioEnhancementRequest(BaseSchema):
    audio_file_id: uuid.UUID
    enhancement_type: str = Field(..., regex="^(denoise|enhance|restore|upscale)$")
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)
    preserve_dynamics: bool = True
    target_quality: str = Field(default="high", regex="^(standard|high|studio)$")
    custom_parameters: Optional[Dict[str, Any]] = None

class AudioEnhancementResponse(BaseSchema):
    session_id: uuid.UUID
    original_file_id: uuid.UUID
    enhanced_file_id: Optional[uuid.UUID] = None
    status: str
    progress: int
    enhancement_type: str

# Task execution schemas
class AgentTaskExecution(BaseSchema):
    id: uuid.UUID
    session_id: uuid.UUID
    task_name: str
    task_type: str
    tool_name: Optional[str]
    status: str
    input_data: Optional[Dict[str, Any]]
    output_data: Optional[Dict[str, Any]]
    parameters: Optional[Dict[str, Any]]
    execution_time: Optional[float]
    memory_used_mb: Optional[float]
    cpu_usage_percent: Optional[float]
    cost: float
    tokens_used: int
    api_calls_made: int
    error_message: Optional[str]
    error_code: Optional[str]
    retry_count: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

# Session progress tracking
class SessionProgress(BaseSchema):
    session_id: uuid.UUID
    status: SessionStatus
    progress_percentage: int = Field(..., ge=0, le=100)
    current_step: Optional[str]
    total_steps: Optional[int]
    completed_steps: int
    estimated_completion: Optional[datetime]
    current_task: Optional[str]
    queue_position: Optional[int]

# Session statistics
class SessionStats(BaseSchema):
    total_sessions: int
    active_sessions: int
    completed_sessions: int
    failed_sessions: int
    average_execution_time: float
    total_cost: float
    success_rate: float
    popular_session_types: List[Dict[str, Any]]

# Session search and filtering
class SessionSearchParams(BaseSchema):
    query: Optional[str] = Field(None, max_length=200)
    session_type: Optional[SessionType] = None
    status: Optional[SessionStatus] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    min_cost: Optional[float] = Field(None, ge=0)
    max_cost: Optional[float] = Field(None, ge=0)
    min_duration: Optional[float] = Field(None, ge=0)
    max_duration: Optional[float] = Field(None, ge=0)

# Session templates
class SessionTemplate(BaseSchema):
    name: str = Field(..., max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    session_type: SessionType
    default_parameters: Dict[str, Any]
    estimated_cost: Optional[float]
    estimated_duration: Optional[int]  # seconds
    tags: Optional[List[str]] = Field(None, max_items=5)

class SessionTemplateResponse(SessionTemplate):
    id: uuid.UUID
    user_id: uuid.UUID
    is_public: bool
    usage_count: int
    created_at: datetime
    updated_at: Optional[datetime]

# Batch session operations
class BatchSessionOperation(BaseSchema):
    session_ids: List[uuid.UUID] = Field(..., min_items=1, max_items=20)
    operation: str = Field(..., regex="^(cancel|retry|delete|archive)$")
    reason: Optional[str] = Field(None, max_length=500)

class BatchSessionOperationResult(BaseSchema):
    operation: str
    total_sessions: int
    successful: int
    failed: int
    results: List[Dict[str, Any]]

# Session feedback and rating
class SessionFeedback(BaseSchema):
    session_id: uuid.UUID
    rating: int = Field(..., ge=1, le=5)
    feedback_text: Optional[str] = Field(None, max_length=1000)
    quality_rating: Optional[int] = Field(None, ge=1, le=5)
    speed_rating: Optional[int] = Field(None, ge=1, le=5)
    ease_of_use_rating: Optional[int] = Field(None, ge=1, le=5)
    would_recommend: Optional[bool] = None

class SessionFeedbackResponse(SessionFeedback):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime

# Session sharing and collaboration
class SessionShare(BaseSchema):
    session_id: uuid.UUID
    share_type: str = Field(..., regex="^(view|collaborate|fork)$")
    expires_at: Optional[datetime] = None
    password: Optional[str] = Field(None, max_length=100)

class SessionShareResponse(SessionShare):
    share_id: uuid.UUID
    share_url: str
    created_at: datetime

# Real-time session updates
class SessionUpdate(BaseSchema):
    session_id: uuid.UUID
    update_type: str
    data: Dict[str, Any]
    timestamp: datetime

# Session cost breakdown
class SessionCostBreakdown(BaseSchema):
    session_id: uuid.UUID
    total_cost: float
    api_costs: Dict[str, float]  # Cost by API service
    compute_costs: Dict[str, float]  # Cost by compute resource
    storage_costs: float
    bandwidth_costs: float
    breakdown_by_task: List[Dict[str, Any]]
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from .common import BaseSchema, FileStatus

# Base audio file schemas
class AudioFileBase(BaseSchema):
    filename: str = Field(..., max_length=255)
    genre: Optional[str] = Field(None, max_length=100)
    mood: Optional[str] = Field(None, max_length=100)
    tempo: Optional[int] = Field(None, ge=60, le=200)
    key: Optional[str] = Field(None, max_length=10)
    time_signature: Optional[str] = Field(None, max_length=10)
    is_public: bool = False
    tags: Optional[List[str]] = Field(None, max_items=10)

class AudioFileCreate(AudioFileBase):
    pass

class AudioFileUpdate(BaseSchema):
    filename: Optional[str] = Field(None, max_length=255)
    genre: Optional[str] = Field(None, max_length=100)
    mood: Optional[str] = Field(None, max_length=100)
    tempo: Optional[int] = Field(None, ge=60, le=200)
    key: Optional[str] = Field(None, max_length=10)
    time_signature: Optional[str] = Field(None, max_length=10)
    is_public: Optional[bool] = None
    tags: Optional[List[str]] = Field(None, max_items=10)

class AudioFileResponse(AudioFileBase):
    id: uuid.UUID
    user_id: uuid.UUID
    original_filename: str
    file_size: int
    mime_type: str
    duration: Optional[float]
    sample_rate: Optional[int]
    channels: Optional[int]
    format: Optional[str]
    status: FileStatus
    processing_progress: int
    created_at: datetime
    updated_at: Optional[datetime]
    download_url: Optional[str] = None
    stream_url: Optional[str] = None

class AudioFileDetail(AudioFileResponse):
    file_path: str
    bit_rate: Optional[int]
    codec: Optional[str]
    file_hash: Optional[str]
    ai_model_used: Optional[str]
    processing_parameters: Optional[Dict[str, Any]]
    quality_score: Optional[float]
    mastering_preset: Optional[str]
    effects_applied: Optional[List[str]]
    
    # Audio analysis results
    loudness_lufs: Optional[float]
    peak_db: Optional[float]
    dynamic_range: Optional[float]
    spectral_centroid: Optional[float]
    zero_crossing_rate: Optional[float]
    
    # Usage statistics
    download_count: int
    play_count: int
    share_count: int
    
    # Versioning
    version: int
    parent_file_id: Optional[uuid.UUID]
    
    # Storage information
    storage_provider: str
    cdn_url: Optional[str]
    backup_path: Optional[str]
    
    # Timestamps
    processing_started_at: Optional[datetime]
    processing_completed_at: Optional[datetime]
    last_accessed_at: Optional[datetime]
    expires_at: Optional[datetime]

# Audio file upload schemas
class AudioFileUploadRequest(BaseSchema):
    filename: str = Field(..., max_length=255)
    file_size: int = Field(..., gt=0, le=500*1024*1024)  # Max 500MB
    mime_type: str = Field(..., max_length=100)
    checksum: Optional[str] = Field(None, max_length=64)
    
    @validator('mime_type')
    def validate_mime_type(cls, v):
        allowed_types = [
            'audio/mpeg', 'audio/wav', 'audio/flac', 'audio/aac',
            'audio/ogg', 'audio/mp4', 'audio/x-wav', 'audio/x-flac'
        ]
        if v not in allowed_types:
            raise ValueError(f'Unsupported audio format: {v}')
        return v

class AudioFileUploadResponse(BaseSchema):
    file_id: uuid.UUID
    upload_url: str
    expires_at: datetime
    max_file_size: int

# Audio processing schemas
class AudioProcessingRequest(BaseSchema):
    audio_file_id: uuid.UUID
    processing_type: str = Field(..., pattern="^(normalize|enhance|master|analyze)$")
    parameters: Optional[Dict[str, Any]] = None

class AudioProcessingResponse(BaseSchema):
    session_id: uuid.UUID
    status: str
    estimated_completion_time: Optional[int]  # seconds
    queue_position: Optional[int]

# Audio analysis schemas
class AudioAnalysisRequest(BaseSchema):
    audio_file_id: uuid.UUID
    analysis_type: str = Field(..., pattern="^(full|basic|spectral|rhythm|harmony)$")
    include_visualization: bool = False

class AudioAnalysisResponse(BaseSchema):
    analysis_id: uuid.UUID
    audio_file_id: uuid.UUID
    analysis_type: str
    results: Dict[str, Any]
    visualizations: Optional[List[str]] = None  # URLs to visualization images
    recommendations: Optional[List[str]] = None
    created_at: datetime

# Audio mastering schemas
class MasteringRequest(BaseSchema):
    audio_file_id: uuid.UUID
    preset: Optional[str] = Field(None, max_length=100)
    target_loudness: Optional[float] = Field(None, ge=-30.0, le=0.0)
    dynamic_range: Optional[float] = Field(None, ge=1.0, le=20.0)
    enhance_bass: Optional[bool] = False
    enhance_treble: Optional[bool] = False
    stereo_width: Optional[float] = Field(None, ge=0.0, le=2.0)
    limiter_threshold: Optional[float] = Field(None, ge=-20.0, le=0.0)
    eq_settings: Optional[Dict[str, float]] = None
    compression_ratio: Optional[float] = Field(None, ge=1.0, le=20.0)

class MasteringResponse(BaseSchema):
    session_id: uuid.UUID
    original_file_id: uuid.UUID
    mastered_file_id: Optional[uuid.UUID] = None
    status: str
    progress: int
    estimated_completion: Optional[datetime]
    parameters_used: Dict[str, Any]

# Audio format conversion schemas
class FormatConversionRequest(BaseSchema):
    audio_file_id: uuid.UUID
    target_format: str = Field(..., pattern="^(mp3|wav|flac|aac|ogg)$")
    quality: str = Field(default="high", pattern="^(low|medium|high|lossless)$")
    sample_rate: Optional[int] = Field(None, ge=8000, le=192000)
    bit_rate: Optional[int] = Field(None, ge=64, le=320)

class FormatConversionResponse(BaseSchema):
    conversion_id: uuid.UUID
    original_file_id: uuid.UUID
    converted_file_id: Optional[uuid.UUID] = None
    status: str
    progress: int

# Audio search and filtering schemas
class AudioFileSearchParams(BaseSchema):
    query: Optional[str] = Field(None, max_length=200)
    genre: Optional[str] = Field(None, max_length=100)
    mood: Optional[str] = Field(None, max_length=100)
    tempo_min: Optional[int] = Field(None, ge=60)
    tempo_max: Optional[int] = Field(None, le=200)
    duration_min: Optional[float] = Field(None, ge=0)
    duration_max: Optional[float] = Field(None, le=3600)
    key: Optional[str] = Field(None, max_length=10)
    format: Optional[str] = Field(None, max_length=20)
    status: Optional[FileStatus] = None
    is_public: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    tags: Optional[List[str]] = Field(None, max_items=5)

# Audio file statistics
class AudioFileStats(BaseSchema):
    total_files: int
    total_size_mb: float
    average_duration: float
    most_common_genre: Optional[str]
    most_common_format: Optional[str]
    processing_success_rate: float
    popular_files: List[Dict[str, Any]]

# Audio file sharing schemas
class AudioFileShareRequest(BaseSchema):
    audio_file_id: uuid.UUID
    share_type: str = Field(..., pattern="^(public|private|link)$")
    expires_at: Optional[datetime] = None
    password: Optional[str] = Field(None, max_length=100)
    allow_download: bool = True

class AudioFileShareResponse(BaseSchema):
    share_id: uuid.UUID
    share_url: str
    share_type: str
    expires_at: Optional[datetime]
    created_at: datetime

# Audio file versioning schemas
class AudioFileVersion(BaseSchema):
    version_id: uuid.UUID
    version_number: int
    parent_file_id: uuid.UUID
    changes_description: Optional[str] = Field(None, max_length=500)
    created_at: datetime
    file_size: int
    processing_parameters: Optional[Dict[str, Any]]

class AudioFileVersionHistory(BaseSchema):
    file_id: uuid.UUID
    versions: List[AudioFileVersion]
    current_version: int

# Batch operations
class BatchAudioOperation(BaseSchema):
    file_ids: List[uuid.UUID] = Field(..., min_items=1, max_items=50)
    operation: str = Field(..., pattern="^(delete|archive|make_public|make_private|analyze)$")
    parameters: Optional[Dict[str, Any]] = None

class BatchAudioOperationResult(BaseSchema):
    operation: str
    total_files: int
    successful: int
    failed: int
    results: List[Dict[str, Any]]
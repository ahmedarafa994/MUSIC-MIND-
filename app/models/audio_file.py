from sqlalchemy import Integer, String, DateTime, Boolean, Text, Float, ForeignKey, func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB as PG_JSONB
from app.db.database import Base
import uuid
from datetime import datetime
from typing import Optional, List, Any, TYPE_CHECKING # Added Optional, List, Any
import os # os was unused, can be removed if not needed elsewhere

if TYPE_CHECKING:
    from .user import User
    from .agent_session import AgentSession
    # For self-referential relationship if versions is a list of AudioFile
    # from .audio_file import AudioFile as AudioFileVersion

class AudioFile(Base):
    __tablename__ = "audio_files"

    # id, created_at, updated_at are inherited from Base

    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # File information
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)  # in bytes
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # SHA-256 hash for deduplication
    
    # Audio metadata
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # in seconds
    sample_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bit_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    channels: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # mp3, wav, flac, etc.
    codec: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Processing status
    status: Mapped[str] = mapped_column(String(50), default="uploaded")  # uploaded, processing, completed, failed, queued
    processing_progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processing_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Music generation metadata
    genre: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    mood: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tempo: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # BPM
    key: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # C, D, E, etc.
    time_signature: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # 4/4, 3/4, etc.
    
    # AI processing metadata
    ai_model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    processing_parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(PG_JSONB, nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0.0-1.0
    mastering_preset: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    effects_applied: Mapped[Optional[List[str]]] = mapped_column(PG_JSONB, nullable=True) # Assuming JSONB for list of strings
    
    # Audio analysis results
    loudness_lufs: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    peak_db: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    dynamic_range: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spectral_centroid: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    zero_crossing_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # File management
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    play_count: Mapped[int] = mapped_column(Integer, default=0)
    share_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_file_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("audio_files.id"), nullable=True)
    
    # Storage and CDN
    storage_provider: Mapped[str] = mapped_column(String(50), default="local")  # local, s3, gcs, etc.
    cdn_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    backup_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Timestamps
    last_accessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="audio_files")
    agent_sessions: Mapped[List["AgentSession"]] = relationship("AgentSession", back_populates="audio_file")
    # For self-referential relationship, if 'versions' is a list of child AudioFile objects.
    versions: Mapped[List["AudioFile"]] = relationship("AudioFile", backref="parent_file", remote_side=[Base.id])


    def __repr__(self):
        return f"<AudioFile(id={self.id}, filename={self.filename}, status={self.status})>"

    @property
    def file_size_mb(self) -> float:
        """Get file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)

    @property
    def file_size_human(self) -> str:
        """Get human-readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    @property
    def duration_formatted(self) -> str:
        """Get formatted duration string"""
        if not self.duration:
            return "Unknown"
        
        hours = int(self.duration // 3600)
        minutes = int((self.duration % 3600) // 60)
        seconds = int(self.duration % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"

    @property
    def processing_time(self) -> float:
        """Get processing time in seconds"""
        if self.processing_started_at and self.processing_completed_at:
            return (self.processing_completed_at - self.processing_started_at).total_seconds()
        return 0.0

    def is_processing_complete(self) -> bool:
        """Check if processing is complete"""
        return self.status in ["completed", "failed"]

    def is_audio_format(self) -> bool:
        """Check if file is an audio format"""
        audio_mimes = [
            'audio/mpeg', 'audio/wav', 'audio/flac', 'audio/aac',
            'audio/ogg', 'audio/mp4', 'audio/x-wav', 'audio/x-flac'
        ]
        return self.mime_type in audio_mimes

    def mark_as_processing(self):
        """Mark file as processing"""
        self.status = "processing"
        self.processing_started_at = datetime.utcnow()
        self.processing_progress = 0

    def mark_as_processed(self, success: bool = True, error_message: str = None):
        """Mark file as processed"""
        if success:
            self.status = "completed"
            self.processing_progress = 100
            self.processing_completed_at = datetime.utcnow()
        else:
            self.status = "failed"
            self.error_message = error_message
            self.processing_completed_at = datetime.utcnow()

    def update_progress(self, progress: int):
        """Update processing progress"""
        self.processing_progress = max(0, min(100, progress))

    def increment_download_count(self):
        """Increment download counter"""
        self.download_count += 1

    def increment_play_count(self):
        """Increment play counter"""
        self.play_count += 1
        self.last_accessed_at = datetime.utcnow()

    def soft_delete(self):
        """Soft delete the file"""
        self.is_deleted = True
        self.updated_at = datetime.utcnow()

    def restore(self):
        """Restore soft deleted file"""
        self.is_deleted = False
        self.updated_at = datetime.utcnow()

    def get_public_url(self) -> str:
        """Get public URL for the file"""
        if self.cdn_url:
            return self.cdn_url
        return f"/api/v1/files/{self.id}/download"

    def can_be_accessed_by_user(self, user_id: str) -> bool:
        """Check if file can be accessed by user"""
        return str(self.user_id) == str(user_id) or self.is_public
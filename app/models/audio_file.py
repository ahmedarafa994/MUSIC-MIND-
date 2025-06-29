from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSON
from app.db.database import Base
import uuid
from datetime import datetime
import os

class AudioFile(Base):
    __tablename__ = "audio_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # File information
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)  # in bytes
    mime_type = Column(String(100), nullable=False)
    file_hash = Column(String(64), nullable=True)  # SHA-256 hash for deduplication
    
    # Audio metadata
    duration = Column(Float, nullable=True)  # in seconds
    sample_rate = Column(Integer, nullable=True)
    bit_rate = Column(Integer, nullable=True)
    channels = Column(Integer, nullable=True)
    format = Column(String(50), nullable=True)  # mp3, wav, flac, etc.
    codec = Column(String(50), nullable=True)
    
    # Processing status
    status = Column(String(50), default="uploaded")  # uploaded, processing, completed, failed, queued
    processing_progress = Column(Integer, default=0)  # 0-100
    error_message = Column(Text, nullable=True)
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    processing_completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Music generation metadata
    genre = Column(String(100), nullable=True)
    mood = Column(String(100), nullable=True)
    tempo = Column(Integer, nullable=True)  # BPM
    key = Column(String(10), nullable=True)  # C, D, E, etc.
    time_signature = Column(String(10), nullable=True)  # 4/4, 3/4, etc.
    
    # AI processing metadata
    ai_model_used = Column(String(100), nullable=True)
    processing_parameters = Column(JSON, nullable=True)
    quality_score = Column(Float, nullable=True)  # 0.0-1.0
    mastering_preset = Column(String(100), nullable=True)
    effects_applied = Column(JSON, nullable=True)
    
    # Audio analysis results
    loudness_lufs = Column(Float, nullable=True)
    peak_db = Column(Float, nullable=True)
    dynamic_range = Column(Float, nullable=True)
    spectral_centroid = Column(Float, nullable=True)
    zero_crossing_rate = Column(Float, nullable=True)
    
    # File management
    is_public = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    download_count = Column(Integer, default=0)
    play_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    
    # Versioning
    version = Column(Integer, default=1)
    parent_file_id = Column(UUID(as_uuid=True), ForeignKey("audio_files.id"), nullable=True)
    
    # Storage and CDN
    storage_provider = Column(String(50), default="local")  # local, s3, gcs, etc.
    cdn_url = Column(String(500), nullable=True)
    backup_path = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_accessed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="audio_files")
    agent_sessions = relationship("AgentSession", back_populates="audio_file")
    parent_file = relationship("AudioFile", remote_side=[id], backref="versions")

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
import uuid
from sqlalchemy import Column, ForeignKey, String, DateTime, JSON, Float, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import enum

from app.db.database import Base # Ensure this points to your SQLAlchemy Base

class MasteringServiceType(str, enum.Enum):
    LANDR = "landr"
    MATCHERIN_LOCAL = "matchering_local" # Example for local Matchering
    # Add other services as needed

class JobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SERVICE_ERROR = "service_error" # For errors from the external service
    DOWNLOAD_FAILED = "download_failed"
    CANCELLED = "cancelled"


class AudioMasteringJob(Base):
    __tablename__ = "audio_mastering_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    original_file_id = Column(UUID(as_uuid=True), ForeignKey("audio_files.id"), nullable=False, index=True)

    service = Column(SAEnum(MasteringServiceType), nullable=False)
    service_job_id = Column(String, nullable=True, index=True, comment="Job ID from the external mastering service")

    status = Column(SAEnum(JobStatus), nullable=False, default=JobStatus.PENDING, index=True)
    progress = Column(Float, nullable=True, default=0.0) # Progress percentage (0-100)

    request_options = Column(JSON, nullable=True, comment="Options sent to the mastering service")
    service_response_details = Column(JSON, nullable=True, comment="Detailed response or metadata from the service")
    error_message = Column(String, nullable=True)

    mastered_file_id = Column(UUID(as_uuid=True), ForeignKey("audio_files.id"), nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User") # Relationship to User model
    original_audio_file = relationship("AudioFile", foreign_keys=[original_file_id])
    mastered_audio_file = relationship("AudioFile", foreign_keys=[mastered_file_id])

    def __repr__(self):
        return f"<AudioMasteringJob(id={self.id}, service='{self.service}', status='{self.status}')>"

import uuid
from sqlalchemy import ForeignKey, String, DateTime, Float, Enum as SAEnum, func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB as PG_JSONB # Using JSONB
import enum
from typing import Optional, Dict, Any, TYPE_CHECKING # Added Optional, Dict, Any
from datetime import datetime # Added datetime

from app.db.database import Base # Ensure this points to your SQLAlchemy Base

if TYPE_CHECKING:
    from .user import User
    from .audio_file import AudioFile

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

    # id, created_at, updated_at are inherited from Base

    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    original_file_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("audio_files.id"), nullable=False, index=True)

    service: Mapped[MasteringServiceType] = mapped_column(SAEnum(MasteringServiceType, name="masteringservicetype"), nullable=False)
    service_job_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True, comment="Job ID from the external mastering service")

    status: Mapped[JobStatus] = mapped_column(SAEnum(JobStatus, name="jobstatus"), nullable=False, default=JobStatus.PENDING, index=True)
    progress: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0.0) # Progress percentage (0-100)

    request_options: Mapped[Optional[Dict[str, Any]]] = mapped_column(PG_JSONB, nullable=True, comment="Options sent to the mastering service")
    service_response_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(PG_JSONB, nullable=True, comment="Detailed response or metadata from the service")
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    mastered_file_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("audio_files.id"), nullable=True, index=True)

    user: Mapped["User"] = relationship("User") # Relationship to User model
    original_audio_file: Mapped["AudioFile"] = relationship("AudioFile", foreign_keys=[original_file_id])
    mastered_audio_file: Mapped[Optional["AudioFile"]] = relationship("AudioFile", foreign_keys=[mastered_file_id])

    def __repr__(self):
        return f"<AudioMasteringJob(id={self.id}, service='{self.service}', status='{self.status}')>"

import uuid
from sqlalchemy import String, Float, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB as PG_JSONB
from app.db.database import Base
from app.services.master_chain_orchestrator import ProcessingStatus # Re-using Enum
from typing import TYPE_CHECKING, Optional, List, Dict, Any
from datetime import datetime

if TYPE_CHECKING:
    from .user import User

class ProcessingJobDB(Base):
    __tablename__ = "processing_jobs"

    # id, created_at, updated_at are inherited from Base

    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=True, index=True) # Assuming project_id is also UUID

    input_audio_path: Mapped[str] = mapped_column(String(1024))
    workflow_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(PG_JSONB, nullable=True)

    status: Mapped[str] = mapped_column(String(50), default=ProcessingStatus.PENDING.value, index=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    current_step: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    estimated_completion: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True) # CORRECTED: DateTime
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    intermediate_results: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(PG_JSONB, nullable=True)
    final_results: Mapped[Optional[Dict[str, Any]]] = mapped_column(PG_JSONB, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship() # Add back_populates in User model if needed

    def __repr__(self):
        return f"<ProcessingJobDB(id={self.id}, user_id={self.user_id}, status='{self.status}')>"

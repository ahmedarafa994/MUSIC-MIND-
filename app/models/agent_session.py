from sqlalchemy import Integer, String, DateTime, Boolean, Text, Float, ForeignKey, func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB as PG_JSONB
from app.db.database import Base
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, TYPE_CHECKING # Added Optional, List, Dict, Any

if TYPE_CHECKING:
    from .user import User
    from .audio_file import AudioFile
    from .agent_session import AgentTaskExecution # Self-reference for task_executions - uncommented

class SessionStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

class AgentSession(Base):
    __tablename__ = "agent_sessions"

    # id, created_at, updated_at are inherited from Base

    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    audio_file_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("audio_files.id"), nullable=True, index=True)
    
    # Session metadata
    session_type: Mapped[str] = mapped_column(String(100), nullable=False)  # music_generation, mastering, analysis
    status: Mapped[SessionStatus] = mapped_column(String(50), default=SessionStatus.ACTIVE) # Uses Enum
    priority: Mapped[int] = mapped_column(Integer, default=5)  # 1-10, higher is more priority
    
    # Request information
    user_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_requirements: Mapped[Optional[Dict[str, Any]]] = mapped_column(PG_JSONB, nullable=True)
    selected_tools: Mapped[Optional[List[str]]] = mapped_column(PG_JSONB, nullable=True)  # List of tools selected by agent
    execution_plan: Mapped[Optional[Dict[str, Any]]] = mapped_column(PG_JSONB, nullable=True)  # Planned execution steps
    
    # Execution tracking
    total_tasks: Mapped[int] = mapped_column(Integer, default=0)
    completed_tasks: Mapped[int] = mapped_column(Integer, default=0)
    failed_tasks: Mapped[int] = mapped_column(Integer, default=0)
    cancelled_tasks: Mapped[int] = mapped_column(Integer, default=0)
    
    # Performance metrics
    total_execution_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # in seconds
    queue_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Time spent in queue
    processing_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Actual processing time
    
    # Cost tracking
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)  # in USD
    api_costs: Mapped[Optional[Dict[str, float]]] = mapped_column(PG_JSONB, nullable=True)  # Breakdown by service
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    compute_units_used: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Results
    output_file_paths: Mapped[Optional[List[str]]] = mapped_column(PG_JSONB, nullable=True)  # List of generated file paths
    final_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quality_metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(PG_JSONB, nullable=True)
    additional_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(PG_JSONB, nullable=True)  # Additional session metadata
    
    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_traceback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    
    # Resource limits
    max_execution_time: Mapped[int] = mapped_column(Integer, default=3600)  # seconds
    max_memory_mb: Mapped[int] = mapped_column(Integer, default=1024)
    max_file_size_mb: Mapped[int] = mapped_column(Integer, default=100)
    
    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="agent_sessions")
    audio_file: Mapped[Optional["AudioFile"]] = relationship("AudioFile", back_populates="agent_sessions")
    task_executions: Mapped[List["AgentTaskExecution"]] = relationship("AgentTaskExecution", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AgentSession(id={self.id}, type={self.session_type}, status={self.status})>"

    @property
    def success_rate(self) -> float:
        """Calculate task success rate"""
        if self.total_tasks == 0:
            return 0.0
        return (self.completed_tasks / self.total_tasks) * 100

    @property
    def is_complete(self) -> bool:
        """Check if session is complete"""
        return self.status in [SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.CANCELLED]

    @property
    def is_active(self) -> bool:
        """Check if session is active"""
        return self.status == SessionStatus.ACTIVE

    @property
    def can_retry(self) -> bool:
        """Check if session can be retried"""
        return self.retry_count < self.max_retries and self.status == SessionStatus.FAILED

    def start_session(self):
        """Mark session as started"""
        self.status = SessionStatus.ACTIVE
        self.started_at = datetime.utcnow()

    def complete_session(self, final_response: str = None):
        """Mark session as completed"""
        self.status = SessionStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if final_response:
            self.final_response = final_response
        
        # Calculate total execution time
        if self.started_at:
            self.total_execution_time = (self.completed_at - self.started_at).total_seconds()

    def fail_session(self, error_message: str, error_code: str = None, traceback: str = None):
        """Mark session as failed"""
        self.status = SessionStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        self.error_code = error_code
        self.error_traceback = traceback
        
        if self.started_at:
            self.total_execution_time = (self.completed_at - self.started_at).total_seconds()

    def cancel_session(self, reason: str = None):
        """Cancel the session"""
        self.status = SessionStatus.CANCELLED
        self.completed_at = datetime.utcnow()
        if reason:
            self.error_message = f"Cancelled: {reason}"

    def add_task_execution(self, task_execution):
        """Add a task execution to this session"""
        self.task_executions.append(task_execution)
        self.total_tasks += 1

    def mark_task_completed(self):
        """Mark a task as completed"""
        self.completed_tasks += 1
        if self.completed_tasks == self.total_tasks and self.status == SessionStatus.ACTIVE:
            self.complete_session()

    def mark_task_failed(self):
        """Mark a task as failed"""
        self.failed_tasks += 1

    def add_cost(self, amount: float, service: str = None):
        """Add cost to the session"""
        self.total_cost += amount
        if service and self.api_costs:
            if service in self.api_costs:
                self.api_costs[service] += amount
            else:
                self.api_costs[service] = amount
        elif service:
            self.api_costs = {service: amount}

    def is_expired(self) -> bool:
        """Check if session has expired"""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False

    def get_execution_summary(self) -> dict:
        """Get execution summary"""
        return {
            "session_id": str(self.id),
            "status": self.status,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "success_rate": self.success_rate,
            "total_cost": self.total_cost,
            "execution_time": self.total_execution_time,
            "created_at": self.created_at,
            "completed_at": self.completed_at
        }

class AgentTaskExecution(Base):
    __tablename__ = "agent_task_executions"

    # id, created_at, updated_at are inherited from Base (updated_at might not be used here, but Base has it)

    session_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("agent_sessions.id"), nullable=False, index=True)
    
    # Task information
    task_name: Mapped[str] = mapped_column(String(200), nullable=False)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)  # tool_execution, api_call, processing
    tool_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[TaskStatus] = mapped_column(String(50), default=TaskStatus.PENDING) # Uses Enum
    
    # Execution details
    input_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(PG_JSONB, nullable=True)
    output_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(PG_JSONB, nullable=True)
    parameters: Mapped[Optional[Dict[str, Any]]] = mapped_column(PG_JSONB, nullable=True)
    
    # Performance metrics
    execution_time: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # in seconds
    memory_used_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cpu_usage_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Cost tracking
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    api_calls_made: Mapped[int] = mapped_column(Integer, default=0)
    
    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_traceback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    session: Mapped["AgentSession"] = relationship("AgentSession", back_populates="task_executions")

    def __repr__(self):
        return f"<AgentTaskExecution(id={self.id}, task={self.task_name}, status={self.status})>"

    def start_execution(self):
        """Mark task execution as started"""
        self.status = TaskStatus.RUNNING
        self.started_at = datetime.utcnow()

    def complete_execution(self, output_data: dict = None):
        """Mark task execution as completed"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if output_data:
            self.output_data = output_data
        
        # Calculate execution time
        if self.started_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds()

    def fail_execution(self, error_message: str, error_code: str = None, traceback: str = None):
        """Mark task execution as failed"""
        self.status = TaskStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        self.error_code = error_code
        self.error_traceback = traceback
        
        if self.started_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds()

    def cancel_execution(self):
        """Cancel task execution"""
        self.status = TaskStatus.CANCELLED
        self.completed_at = datetime.utcnow()
        
        if self.started_at:
            self.execution_time = (self.completed_at - self.started_at).total_seconds()

    @property
    def is_complete(self) -> bool:
        """Check if task execution is complete"""
        return self.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]

    @property
    def was_successful(self) -> bool:
        """Check if task execution was successful"""
        return self.status == TaskStatus.COMPLETED
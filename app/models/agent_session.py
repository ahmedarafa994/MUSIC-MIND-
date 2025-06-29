from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID, JSON
from app.db.database import Base
import uuid
from datetime import datetime
from enum import Enum

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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    audio_file_id = Column(UUID(as_uuid=True), ForeignKey("audio_files.id"), nullable=True, index=True)
    
    # Session metadata
    session_type = Column(String(100), nullable=False)  # music_generation, mastering, analysis
    status = Column(String(50), default=SessionStatus.ACTIVE)
    priority = Column(Integer, default=5)  # 1-10, higher is more priority
    
    # Request information
    user_prompt = Column(Text, nullable=False)
    parsed_requirements = Column(JSON, nullable=True)
    selected_tools = Column(JSON, nullable=True)  # List of tools selected by agent
    execution_plan = Column(JSON, nullable=True)  # Planned execution steps
    
    # Execution tracking
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)
    cancelled_tasks = Column(Integer, default=0)
    
    # Performance metrics
    total_execution_time = Column(Float, nullable=True)  # in seconds
    queue_time = Column(Float, nullable=True)  # Time spent in queue
    processing_time = Column(Float, nullable=True)  # Actual processing time
    
    # Cost tracking
    total_cost = Column(Float, default=0.0)  # in USD
    api_costs = Column(JSON, nullable=True)  # Breakdown by service
    tokens_used = Column(Integer, default=0)
    compute_units_used = Column(Float, default=0.0)
    
    # Results
    output_file_paths = Column(JSON, nullable=True)  # List of generated file paths
    final_response = Column(Text, nullable=True)
    quality_metrics = Column(JSON, nullable=True)
    additional_metadata = Column(JSON, nullable=True)  # Additional session metadata
    
    # Error handling
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Resource limits
    max_execution_time = Column(Integer, default=3600)  # seconds
    max_memory_mb = Column(Integer, default=1024)
    max_file_size_mb = Column(Integer, default=100)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="agent_sessions")
    audio_file = relationship("AudioFile", back_populates="agent_sessions")
    task_executions = relationship("AgentTaskExecution", back_populates="session", cascade="all, delete-orphan")

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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("agent_sessions.id"), nullable=False, index=True)
    
    # Task information
    task_name = Column(String(200), nullable=False)
    task_type = Column(String(100), nullable=False)  # tool_execution, api_call, processing
    tool_name = Column(String(100), nullable=True)
    status = Column(String(50), default=TaskStatus.PENDING)
    
    # Execution details
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    parameters = Column(JSON, nullable=True)
    
    # Performance metrics
    execution_time = Column(Float, nullable=True)  # in seconds
    memory_used_mb = Column(Float, nullable=True)
    cpu_usage_percent = Column(Float, nullable=True)
    
    # Cost tracking
    cost = Column(Float, default=0.0)
    tokens_used = Column(Integer, default=0)
    api_calls_made = Column(Integer, default=0)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    session = relationship("AgentSession", back_populates="task_executions")

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
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from datetime import datetime, timedelta
import uuid

from app.models.agent_session import AgentSession, AgentTaskExecution, SessionStatus, TaskStatus
from app.schemas.agent_session import AgentSessionCreate, AgentSessionUpdate, AgentTaskExecutionCreate, AgentTaskExecutionUpdate # Assuming these schemas exist
from app.crud.base import CRUDBase
import structlog

logger = structlog.get_logger(__name__)

class CRUDAgentSession(CRUDBase[AgentSession, AgentSessionCreate, AgentSessionUpdate]):
    async def create_with_user(
        self,
        db: AsyncSession,
        *,
        obj_in: AgentSessionCreate,
        user_id: uuid.UUID
    ) -> AgentSession:
        """Create agent session with user association"""
        obj_in_data = obj_in.dict()
        db_obj = AgentSession(**obj_in_data, user_id=user_id)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        logger.info("Agent session created", session_id=db_obj.id, user_id=user_id, type=obj_in.session_type)
        return db_obj

    async def get_by_user(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[AgentSession]:
        """Get sessions by user"""
        stmt = select(AgentSession).filter(AgentSession.user_id == user_id).order_by(desc(AgentSession.created_at)).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_user_with_filters(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        status_filter: Optional[str] = None,
        type_filter: Optional[str] = None, # Added type_filter
    ) -> List[AgentSession]:
        """Get sessions by user with optional status and type filters."""
        stmt = select(AgentSession).filter(AgentSession.user_id == user_id)
        if status_filter:
            stmt = stmt.filter(AgentSession.status == status_filter)
        if type_filter: # Added type_filter logic
            stmt = stmt.filter(AgentSession.session_type == type_filter)

        stmt = stmt.order_by(desc(AgentSession.created_at)).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()


    async def get_by_status(
        self,
        db: AsyncSession,
        *,
        status: SessionStatus,
        skip: int = 0,
        limit: int = 100
    ) -> List[AgentSession]:
        """Get sessions by status"""
        stmt = select(AgentSession).filter(AgentSession.status == status).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_active_sessions(self, db: AsyncSession, limit: int = 100) -> List[AgentSession]:
        """Get all active sessions"""
        stmt = select(AgentSession).filter(AgentSession.status == SessionStatus.ACTIVE).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def update_status(
        self,
        db: AsyncSession,
        *,
        session_id: uuid.UUID,
        status: SessionStatus, # Use the Enum for type hint
        error_message: Optional[str] = None
    ) -> Optional[AgentSession]:
        """Update session status"""
        session = await self.get(db, id=session_id)
        if not session:
            logger.warning("Session not found for status update", session_id=session_id)
            return None

        session.status = status.value # Use status.value if status is Enum
        session.updated_at = datetime.utcnow()

        if status == SessionStatus.ACTIVE and not session.started_at:
            session.started_at = datetime.utcnow()
        elif status in [SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.CANCELLED]:
            session.completed_at = datetime.utcnow()
            if session.started_at:
                session.total_execution_time = (session.completed_at - session.started_at).total_seconds()

        if error_message:
            session.error_message = error_message

        db.add(session)
        await db.commit()
        await db.refresh(session)
        logger.info("Agent session status updated", session_id=session.id, new_status=status.value)
        return session

    async def update_progress( # Matches usage in sessions.py
        self,
        db: AsyncSession,
        *,
        session_id: uuid.UUID,
        progress: int,
        current_step: Optional[str] = None
        # total_steps: Optional[int] = None,
        # estimated_completion_time: Optional[datetime] = None
    ) -> Optional[AgentSession]:
        """Update session progress and current step"""
        session = await self.get(db, id=session_id)
        if not session:
            logger.warning("Session not found for progress update", session_id=session_id)
            return None

        # Assuming AgentSession model has these fields, if not, they need to be added
        # For now, we'll comment out direct assignment if fields don't exist to prevent errors
        # and assume they might be part of a JSON 'metadata' field or similar.
        # session.progress_percentage = progress
        # if current_step:
        #     session.current_step = current_step
        # if total_steps:
        #     session.total_steps = total_steps
        # if estimated_completion_time:
        #     session.estimated_completion_time = estimated_completion_time

        # A common pattern is to store such dynamic progress info in a JSON field
        if session.metadata is None:
            session.metadata = {}
        session.metadata['progress'] = progress
        if current_step:
            session.metadata['current_step'] = current_step

        session.updated_at = datetime.utcnow()
        db.add(session)
        await db.commit()
        await db.refresh(session)
        logger.debug("Agent session progress updated", session_id=session.id, progress=progress, step=current_step)
        return session

    async def update_results( # Matches usage in sessions.py
        self,
        db: AsyncSession,
        *,
        session_id: uuid.UUID,
        results: Dict[str, Any],
        # output_file_paths: Optional[List[str]] = None, # Add if these specific fields exist
        # final_response: Optional[str] = None,
        # quality_metrics: Optional[Dict[str, Any]] = None,
        # total_cost: Optional[float] = None,
        # tokens_used: Optional[int] = None
    ) -> Optional[AgentSession]:
        """Update session with execution results"""
        session = await self.get(db, id=session_id)
        if not session:
            logger.warning("Session not found for results update", session_id=session_id)
            return None

        session.final_response = results.get("final_summary") # Example: store summary in final_response
        session.output_file_paths = results.get("output_files") # Example: store file paths
        session.quality_metrics = results.get("quality_scores") # Example
        session.total_cost = results.get("total_cost_calculated", session.total_cost) # Example
        session.tokens_used = results.get("tokens_consumed", session.tokens_used) # Example

        # If 'results' is meant to be a generic JSON field for all other results:
        if session.results is None: # Assuming AgentSession model has a 'results' JSONB field
            session.results = {}
        session.results.update(results)

        session.updated_at = datetime.utcnow()
        db.add(session)
        await db.commit()
        await db.refresh(session)
        logger.info("Agent session results updated", session_id=session.id)
        return session

    async def add_task_execution(
        self,
        db: AsyncSession,
        *,
        session_id: uuid.UUID,
        task_data: AgentTaskExecutionCreate
    ) -> Optional[AgentTaskExecution]:
        """Add a task execution record to a session"""
        session = await self.get(db, id=session_id)
        if not session:
            logger.warning("Session not found for adding task execution", session_id=session_id)
            return None

        task_obj = AgentTaskExecution(**task_data.dict(), session_id=session_id)
        db.add(task_obj)
        session.total_tasks = (session.total_tasks or 0) + 1
        db.add(session)
        await db.commit()
        await db.refresh(task_obj)
        await db.refresh(session)
        logger.info("Task execution added to session", session_id=session_id, task_id=task_obj.id, task_name=task_obj.task_name)
        return task_obj

    async def update_task_execution_status(
        self,
        db: AsyncSession,
        *,
        task_execution_id: uuid.UUID,
        status: TaskStatus, # Use Enum
        output_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        cost: Optional[float] = None
    ) -> Optional[AgentTaskExecution]:
        """Update status and details of a task execution"""
        stmt = select(AgentTaskExecution).filter(AgentTaskExecution.id == task_execution_id)
        result = await db.execute(stmt)
        task_execution = result.scalars().first()

        if not task_execution:
            logger.warning("Task execution not found for status update", task_execution_id=task_execution_id)
            return None

        task_execution.status = status.value # Use status.value if status is Enum
        # task_execution.updated_at = datetime.utcnow() # Assuming model has updated_at, if not add it

        if status == TaskStatus.RUNNING and not task_execution.started_at:
            task_execution.started_at = datetime.utcnow()
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            task_execution.completed_at = datetime.utcnow()
            if task_execution.started_at:
                task_execution.execution_time = (task_execution.completed_at - task_execution.started_at).total_seconds()

        if output_data is not None:
            task_execution.output_data = output_data
        if error_message is not None:
            task_execution.error_message = error_message
        if cost is not None:
            task_execution.cost = cost
            session = await self.get(db, id=task_execution.session_id)
            if session:
                session.total_cost = (session.total_cost or 0) + cost
                db.add(session)

        db.add(task_execution)
        await db.commit()
        await db.refresh(task_execution)
        logger.info("Task execution status updated", task_id=task_execution.id, new_status=status.value)

        session = await self.get(db, id=task_execution.session_id)
        if session:
            if status == TaskStatus.COMPLETED:
                session.completed_tasks = (session.completed_tasks or 0) + 1
            elif status == TaskStatus.FAILED:
                session.failed_tasks = (session.failed_tasks or 0) + 1
            elif status == TaskStatus.CANCELLED: # Assuming model has cancelled_tasks
                pass # session.cancelled_tasks = (session.cancelled_tasks or 0) + 1
            db.add(session)
            await db.commit()
            await db.refresh(session)

        return task_execution

agent_session = CRUDAgentSession(AgentSession)

class CRUDAgentTaskExecution(CRUDBase[AgentTaskExecution, AgentTaskExecutionCreate, AgentTaskExecutionUpdate]):
    async def get_by_session(
        self,
        db: AsyncSession,
        *,
        session_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[AgentTaskExecution]:
        stmt = select(AgentTaskExecution).filter(AgentTaskExecution.session_id == session_id).order_by(AgentTaskExecution.created_at).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

agent_task_execution = CRUDAgentTaskExecution(AgentTaskExecution)

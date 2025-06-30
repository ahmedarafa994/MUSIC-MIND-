from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession # Changed import
from sqlalchemy import select, and_, or_, func, desc # Changed import for select, desc
from datetime import datetime, timedelta
import uuid

from app.models.agent_session import AgentSession, AgentTaskExecution, SessionStatus # Added SessionStatus
from app.schemas.agent_session import AgentSessionCreate, AgentSessionUpdate
from app.crud.base import CRUDBase
import logging # Consider structlog if used elsewhere consistently

logger = logging.getLogger(__name__)

class CRUDAgentSession(CRUDBase[AgentSession, AgentSessionCreate, AgentSessionUpdate]):
    async def create_with_user( # Added async
        self,
        db: AsyncSession, # Changed Session to AsyncSession
        *,
        obj_in: AgentSessionCreate,
        user_id: uuid.UUID # Changed type to uuid.UUID
    ) -> AgentSession:
        """Create agent session with user association"""
        obj_in_data = obj_in.dict() if hasattr(obj_in, 'dict') else obj_in # Keep model_dump for Pydantic v2 if used
        obj_in_data["user_id"] = user_id
        db_obj = AgentSession(**obj_in_data)
        db.add(db_obj)
        await db.commit() # Added await
        await db.refresh(db_obj) # Added await
        return db_obj

    async def get_by_user( # Added async
        self,
        db: AsyncSession, # Changed Session to AsyncSession
        *,
        user_id: uuid.UUID, # Changed type to uuid.UUID
        skip: int = 0,
        limit: int = 100
    ) -> List[AgentSession]:
        """Get sessions by user"""
        stmt = select(AgentSession).filter(
            AgentSession.user_id == user_id
        ).order_by(desc(AgentSession.created_at)).offset(skip).limit(limit)
        result = await db.execute(stmt) # Added await
        return result.scalars().all()

    async def get_by_status( # Added async
        self,
        db: AsyncSession, # Changed Session to AsyncSession
        *,
        status: SessionStatus, # Changed type to SessionStatus Enum
        skip: int = 0,
        limit: int = 100
    ) -> List[AgentSession]:
        """Get sessions by status"""
        stmt = select(AgentSession).filter(
            AgentSession.status == status
        ).offset(skip).limit(limit)
        result = await db.execute(stmt) # Added await
        return result.scalars().all()

    async def get_active_sessions(self, db: AsyncSession, *, user_id: uuid.UUID, limit: int = 100) -> List[AgentSession]: # Added async and user_id
        """Get active sessions for a specific user."""
        stmt = select(AgentSession).filter(
            AgentSession.user_id == user_id, # Added user_id filter
            AgentSession.status == SessionStatus.ACTIVE # Use Enum
        ).order_by(desc(AgentSession.created_at)).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def update_status( # Added async
        self,
        db: AsyncSession, # Changed Session to AsyncSession
        *,
        session_id: uuid.UUID, # Changed type to uuid.UUID
        status: SessionStatus, # Changed type to SessionStatus Enum
        error_message: Optional[str] = None # Changed type from str to Optional[str]
    ) -> Optional[AgentSession]:
        """Update session status"""
        session = await self.get(db, id=session_id) # Added await, self.get is from async CRUDBase
        if not session:
            return None
            
        session.status = status
        session.updated_at = datetime.utcnow()
        
        if status == SessionStatus.ACTIVE and not session.started_at:
            session.started_at = datetime.utcnow()
        elif status in [SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.CANCELLED]:
            session.completed_at = datetime.utcnow()
            if session.started_at:
                session.total_execution_time = (
                    session.completed_at - session.started_at
                ).total_seconds()
        
        if error_message:
            session.error_message = error_message
        
        db.add(session)
        await db.commit() # Added await
        await db.refresh(session) # Added await
        return session

    async def update_progress( # Added async
        self,
        db: AsyncSession, # Changed Session to AsyncSession
        *,
        session_id: uuid.UUID, # Changed type to uuid.UUID
        progress: int,
        current_step: Optional[str] = None # Changed type from str to Optional[str]
    ) -> Optional[AgentSession]:
        """Update session progress"""
        session = await self.get(db, id=session_id) # Added await, self.get is from async CRUDBase
        if not session:
            return None
            
        # Assuming progress_percentage and current_step are attributes of AgentSession model
        if hasattr(session, 'progress_percentage'):
            session.progress_percentage = max(0, min(100, progress))
        if current_step and hasattr(session, 'current_step'):
            session.current_step = current_step
        session.updated_at = datetime.utcnow()
        
        db.add(session)
        await db.commit() # Added await
        await db.refresh(session) # Added await
        return session

    async def cancel_session(self, db: AsyncSession, *, session_id: uuid.UUID, reason: Optional[str] = None) -> Optional[AgentSession]: # Added async
        """Cancel an agent session."""
        session = await self.get(db, id=session_id)
        if not session:
            return None
        if session.status in [SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.CANCELLED]: # Check against enum values
            # Consider raising an HTTPException here if called from an API context
            return session # Or indicate it's already completed/cancelled

        session.status = SessionStatus.CANCELLED
        session.completed_at = datetime.utcnow()
        if reason:
            session.error_message = f"Cancelled: {reason}"

        if session.started_at and session.completed_at: # Recalculate execution time
            session.total_execution_time = (session.completed_at - session.started_at).total_seconds()

        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

# Ensure the exported name is clear about its async nature if needed, e.g., async_agent_session_crud
agent_session = CRUDAgentSession(AgentSession) # Renamed from agent_session_crud for consistency with other modules
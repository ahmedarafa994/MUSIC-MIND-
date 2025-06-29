from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta
import uuid

from app.models.agent_session import AgentSession, AgentTaskExecution
from app.schemas.agent_session import AgentSessionCreate, AgentSessionUpdate
from app.crud.base import CRUDBase
import logging

logger = logging.getLogger(__name__)

class CRUDAgentSession(CRUDBase[AgentSession, AgentSessionCreate, AgentSessionUpdate]):
    def create_with_user(
        self,
        db: Session,
        *,
        obj_in: AgentSessionCreate,
        user_id: str
    ) -> AgentSession:
        """Create agent session with user association"""
        obj_in_data = obj_in.dict() if hasattr(obj_in, 'dict') else obj_in
        obj_in_data["user_id"] = user_id
        db_obj = AgentSession(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_by_user(
        self,
        db: Session,
        *,
        user_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[AgentSession]:
        """Get sessions by user"""
        return db.query(AgentSession).filter(
            AgentSession.user_id == user_id
        ).order_by(AgentSession.created_at.desc()).offset(skip).limit(limit).all()

    def get_by_status(
        self,
        db: Session,
        *,
        status: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[AgentSession]:
        """Get sessions by status"""
        return db.query(AgentSession).filter(
            AgentSession.status == status
        ).offset(skip).limit(limit).all()

    def update_status(
        self,
        db: Session,
        *,
        session_id: str,
        status: str,
        error_message: str = None
    ) -> Optional[AgentSession]:
        """Update session status"""
        session = self.get(db, id=session_id)
        if not session:
            return None
            
        session.status = status
        session.updated_at = datetime.utcnow()
        
        if status == "active" and not session.started_at:
            session.started_at = datetime.utcnow()
        elif status in ["completed", "failed", "cancelled"]:
            session.completed_at = datetime.utcnow()
            if session.started_at:
                session.total_execution_time = (
                    session.completed_at - session.started_at
                ).total_seconds()
        
        if error_message:
            session.error_message = error_message
        
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    def update_progress(
        self,
        db: Session,
        *,
        session_id: str,
        progress: int,
        current_step: str = None
    ) -> Optional[AgentSession]:
        """Update session progress"""
        session = self.get(db, id=session_id)
        if not session:
            return None
            
        session.progress_percentage = max(0, min(100, progress))
        if current_step:
            session.current_step = current_step
        session.updated_at = datetime.utcnow()
        
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

agent_session_crud = CRUDAgentSession(AgentSession)
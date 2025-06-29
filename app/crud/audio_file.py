from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from datetime import datetime, timedelta
import uuid

from app.models.audio_file import AudioFile
from app.schemas.audio_file import AudioFileCreate, AudioFileUpdate
from app.crud.base import CRUDBase
import logging

logger = logging.getLogger(__name__)

class CRUDAudioFile(CRUDBase[AudioFile, AudioFileCreate, AudioFileUpdate]):
    def create_with_user(self, db: Session, *, obj_in: AudioFileCreate, user_id: str) -> AudioFile:
        """Create audio file with user association"""
        obj_in_data = obj_in.dict() if hasattr(obj_in, 'dict') else obj_in
        obj_in_data["user_id"] = user_id
        db_obj = AudioFile(**obj_in_data)
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
    ) -> List[AudioFile]:
        """Get audio files by user"""
        return db.query(AudioFile).filter(
            AudioFile.user_id == user_id
        ).offset(skip).limit(limit).all()

    def get_by_status(
        self,
        db: Session,
        *,
        status: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[AudioFile]:
        """Get audio files by status"""
        return db.query(AudioFile).filter(
            AudioFile.status == status
        ).offset(skip).limit(limit).all()

    def update_status(self, db: Session, *, audio_file: AudioFile, status: str) -> AudioFile:
        """Update audio file status"""
        audio_file.status = status
        audio_file.updated_at = datetime.utcnow()
        if status == "processing":
            audio_file.processing_started_at = datetime.utcnow()
        elif status in ["completed", "failed"]:
            audio_file.processing_completed_at = datetime.utcnow()
        db.add(audio_file)
        db.commit()
        db.refresh(audio_file)
        return audio_file

    def increment_download_count(self, db: Session, *, audio_file_id: str) -> bool:
        """Increment download count"""
        try:
            audio_file = self.get(db, id=audio_file_id)
            if audio_file:
                audio_file.download_count += 1
                db.add(audio_file)
                db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to increment download count: {e}")
            return False

audio_file_crud = CRUDAudioFile(AudioFile)
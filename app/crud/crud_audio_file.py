from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc
from datetime import datetime, timedelta
import uuid

from app.models.audio_file import AudioFile
from app.schemas.audio_file import AudioFileCreate, AudioFileUpdate # Assuming these schemas exist
from app.crud.base import CRUDBase
import structlog

logger = structlog.get_logger(__name__)

class CRUDAudioFile(CRUDBase[AudioFile, AudioFileCreate, AudioFileUpdate]):
    async def create_with_user_and_details( # Renamed to be more specific
        self,
        db: AsyncSession,
        *,
        obj_in: AudioFileCreate,
        user_id: uuid.UUID,
        original_filename: str,
        file_size: int,
        mime_type: str,
        file_path: str,
        s3_bucket: Optional[str] = None,
        s3_key: Optional[str] = None,
    ) -> AudioFile:
        """Create audio file with user association and full details."""
        # Note: AudioFileCreate schema should contain fields like 'filename' (user-chosen or derived),
        # 'genre', 'mood', etc. that are part of the base user input for the file.
        # 'filename' in AudioFile model might be the unique system filename.

        db_obj = AudioFile(
            **obj_in.dict(exclude_unset=True),
            user_id=user_id,
            original_filename=original_filename, # Actual name of the uploaded file
            filename=file_path, # System-generated unique name, often same as s3_key or storage path
            file_size=file_size,
            mime_type=mime_type,
            file_path=file_path,
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            status="uploaded",
            is_deleted=False # Explicitly set is_deleted to False on creation
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        logger.info("Audio file created", audio_file_id=db_obj.id, user_id=user_id, system_filename=db_obj.filename)
        return db_obj

    async def get_by_user(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[AudioFile]:
        """Get audio files by user."""
        stmt = select(AudioFile).filter(AudioFile.user_id == user_id)
        if not include_deleted:
            stmt = stmt.filter(AudioFile.is_deleted == False)
        stmt = stmt.order_by(desc(AudioFile.created_at)).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_user_with_filters(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        format_filter: Optional[str] = None,
        search: Optional[str] = None,
        include_deleted: bool = False
    ) -> List[AudioFile]:
        """Get audio files by user with format and search filters."""
        stmt = select(AudioFile).filter(AudioFile.user_id == user_id)
        if not include_deleted:
            stmt = stmt.filter(AudioFile.is_deleted == False)

        if format_filter:
            stmt = stmt.filter(AudioFile.mime_type.ilike(f"%{format_filter}%"))
        if search:
            search_term = f"%{search}%"
            stmt = stmt.filter(
                or_(
                    AudioFile.filename.ilike(search_term), # System filename
                    AudioFile.original_filename.ilike(search_term), # User's original filename
                    AudioFile.genre.ilike(search_term),
                    AudioFile.mood.ilike(search_term)
                )
            )
        stmt = stmt.order_by(desc(AudioFile.created_at)).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_by_status(
        self,
        db: AsyncSession,
        *,
        status: str,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[AudioFile]:
        """Get audio files by status"""
        stmt = select(AudioFile).filter(AudioFile.status == status)
        if not include_deleted:
            stmt = stmt.filter(AudioFile.is_deleted == False)
        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def update_status(self, db: AsyncSession, *, audio_file_id: uuid.UUID, status: str) -> Optional[AudioFile]:
        """Update audio file status"""
        audio_file = await self.get(db, id=audio_file_id) # CRUDBase.get()
        if not audio_file or audio_file.is_deleted: # Do not update if soft-deleted
            logger.warning("Audio file not found or deleted, cannot update status", audio_file_id=audio_file_id)
            return None

        audio_file.status = status
        audio_file.updated_at = datetime.utcnow()

        if status == "processing":
            audio_file.processing_started_at = datetime.utcnow()
            audio_file.processing_progress = 0 # Reset progress when starting
        elif status in ["completed", "failed"]:
            audio_file.processing_completed_at = datetime.utcnow()
            if status == "completed":
                audio_file.processing_progress = 100

        db.add(audio_file)
        await db.commit()
        await db.refresh(audio_file)
        logger.info("Audio file status updated", audio_file_id=audio_file.id, new_status=status)
        return audio_file

    async def update_progress(self, db: AsyncSession, *, audio_file_id: uuid.UUID, progress: int) -> Optional[AudioFile]:
        """Update processing progress"""
        audio_file = await self.get(db, id=audio_file_id)
        if not audio_file or audio_file.is_deleted:
            logger.warning("Audio file not found or deleted, cannot update progress", audio_file_id=audio_file_id)
            return None

        audio_file.processing_progress = max(0, min(100, progress)) # Clamp progress
        audio_file.updated_at = datetime.utcnow()
        db.add(audio_file)
        await db.commit()
        await db.refresh(audio_file)
        logger.debug("Audio file progress updated", audio_file_id=audio_file.id, progress=progress)
        return audio_file

    async def update_metadata_fields(
        self,
        db: AsyncSession,
        *,
        audio_file_id: uuid.UUID,
        metadata_update: Dict[str, Any]
    ) -> Optional[AudioFile]:
        """Update specific audio file metadata fields."""
        audio_file = await self.get(db, id=audio_file_id)
        if not audio_file or audio_file.is_deleted:
            logger.warning("Audio file not found or deleted, cannot update metadata", audio_file_id=audio_file_id)
            return None

        for key, value in metadata_update.items():
            if hasattr(audio_file, key):
                setattr(audio_file, key, value)
            else:
                logger.warning(f"Metadata update: Field '{key}' not found in AudioFile model.", audio_file_id=audio_file_id)

        audio_file.updated_at = datetime.utcnow()
        db.add(audio_file)
        await db.commit()
        await db.refresh(audio_file)
        logger.info("Audio file metadata updated", audio_file_id=audio_file.id, fields_updated=list(metadata_update.keys()))
        return audio_file

    async def increment_play_count(self, db: AsyncSession, *, audio_file_id: uuid.UUID) -> Optional[AudioFile]:
        """Increment play count"""
        audio_file = await self.get(db, id=audio_file_id)
        if not audio_file or audio_file.is_deleted: # Typically can still play if public, but maybe not count if user deleted
            logger.warning("Audio file not found or deleted, cannot increment play count", audio_file_id=audio_file_id)
            return None
        audio_file.play_count = (audio_file.play_count or 0) + 1
        audio_file.last_accessed_at = datetime.utcnow()
        db.add(audio_file)
        await db.commit()
        await db.refresh(audio_file)
        return audio_file

    async def increment_download_count(self, db: AsyncSession, *, audio_file_id: uuid.UUID) -> Optional[AudioFile]:
        """Increment download count"""
        audio_file = await self.get(db, id=audio_file_id)
        if not audio_file or audio_file.is_deleted:
            logger.warning("Audio file not found or deleted, cannot increment download count", audio_file_id=audio_file_id)
            return None
        audio_file.download_count = (audio_file.download_count or 0) + 1
        db.add(audio_file)
        await db.commit()
        await db.refresh(audio_file)
        return audio_file

    async def get_user_storage_usage(self, db: AsyncSession, *, user_id: uuid.UUID) -> Dict[str, Any]:
        """Get user's storage usage statistics (total files and size for non-deleted files)."""
        stmt = select(
            func.count(AudioFile.id),
            func.sum(AudioFile.file_size)
        ).filter(AudioFile.user_id == user_id).filter(AudioFile.is_deleted == False)

        result = await db.execute(stmt)
        total_files, total_size_bytes = result.one_or_none() or (0, 0)

        return {
            'total_files': total_files or 0,
            'total_size_bytes': total_size_bytes or 0,
            'total_size_mb': round((total_size_bytes or 0) / (1024 * 1024), 2)
        }

audio_file = CRUDAudioFile(AudioFile)

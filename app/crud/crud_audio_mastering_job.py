from typing import Any, Dict, Optional, List
import uuid
from sqlalchemy.ext.asyncio import AsyncSession # Changed import
from sqlalchemy import select, update, delete # Added select, update, delete

from app.models.audio_mastering_job import AudioMasteringJob, JobStatus, MasteringServiceType
# from app.schemas.audio_processing import MasteringRequest - Not strictly needed here if options are dict
# Import CRUDBase if you want to inherit from it, or define methods directly.
# For simplicity here, methods are defined directly.

async def create_mastering_job( # Added async
    db: AsyncSession, # Changed Session to AsyncSession
    user_id: uuid.UUID,
    original_file_id: uuid.UUID,
    service: MasteringServiceType,
    service_job_id: Optional[str],
    status: JobStatus,
    request_options: Optional[Dict[str, Any]] = None
) -> AudioMasteringJob:
    """
    Create a new audio mastering job record.
    """
    db_job = AudioMasteringJob(
        user_id=user_id,
        original_file_id=original_file_id,
        service=service,
        service_job_id=service_job_id,
        status=status,
        request_options=request_options
    )
    db.add(db_job)
    await db.commit() # Added await
    await db.refresh(db_job) # Added await
    return db_job

async def get_mastering_job(db: AsyncSession, job_id: uuid.UUID) -> Optional[AudioMasteringJob]: # Added async
    """
    Get an audio mastering job by its internal ID.
    """
    result = await db.execute(select(AudioMasteringJob).filter(AudioMasteringJob.id == job_id)) # Added await
    return result.scalar_one_or_none()

async def get_mastering_jobs_by_user( # Added async
    db: AsyncSession, user_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> List[AudioMasteringJob]:
    """
    Get all mastering jobs for a specific user.
    """
    stmt = (
        select(AudioMasteringJob)
        .filter(AudioMasteringJob.user_id == user_id)
        .order_by(AudioMasteringJob.created_at.desc()) # type: ignore
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt) # Added await
    return result.scalars().all()

async def update_mastering_job_status( # Added async
    db: AsyncSession, # Changed Session to AsyncSession
    job_id: uuid.UUID,
    status: JobStatus,
    progress: Optional[float] = None,
    service_response_details: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
) -> Optional[AudioMasteringJob]:
    """
    Update the status, progress, and other details of a mastering job.
    """
    db_job = await get_mastering_job(db, job_id=job_id) # Added await
    if db_job:
        db_job.status = status
        if progress is not None:
            db_job.progress = progress
        if service_response_details is not None:
            db_job.service_response_details = service_response_details
        if error_message is not None:
            db_job.error_message = error_message
        else:
            if status not in [JobStatus.FAILED, JobStatus.SERVICE_ERROR, JobStatus.DOWNLOAD_FAILED]:
                db_job.error_message = None

        await db.commit() # Added await
        await db.refresh(db_job) # Added await
    return db_job

async def set_mastered_file_id( # Added async
    db: AsyncSession, job_id: uuid.UUID, mastered_file_id: uuid.UUID # Changed Session to AsyncSession
) -> Optional[AudioMasteringJob]:
    """
    Link the mastered audio file (AudioFile record ID) to the mastering job.
    """
    db_job = await get_mastering_job(db, job_id=job_id) # Added await
    if db_job:
        db_job.mastered_file_id = mastered_file_id
        db_job.status = JobStatus.COMPLETED
        if db_job.progress is None or db_job.progress < 100.0:
             db_job.progress = 100.0
        db_job.error_message = None
        await db.commit() # Added await
        await db.refresh(db_job) # Added await
    return db_job

async def update_service_job_id( # Added async
    db: AsyncSession, job_id: uuid.UUID, service_job_id: str # Changed Session to AsyncSession
) -> Optional[AudioMasteringJob]:
    """
    Update the external service's job ID for a mastering job.
    """
    db_job = await get_mastering_job(db, job_id=job_id) # Added await
    if db_job:
        db_job.service_job_id = service_job_id
        await db.commit() # Added await
        await db.refresh(db_job) # Added await
    return db_job

async def delete_mastering_job(db: AsyncSession, job_id: uuid.UUID) -> Optional[AudioMasteringJob]: # Added async
    """
    Delete a mastering job record.
    """
    db_job = await get_mastering_job(db, job_id=job_id) # Added await
    if db_job:
        await db.delete(db_job) # Added await
        await db.commit() # Added await
    return db_job # Returns the object before deletion or None

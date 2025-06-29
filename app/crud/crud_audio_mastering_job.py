from typing import Any, Dict, Optional, List # Added List
import uuid
from sqlalchemy.orm import Session

from app.models.audio_mastering_job import AudioMasteringJob, JobStatus, MasteringServiceType
# from app.schemas.audio_processing import MasteringRequest - Not strictly needed here if options are dict

def create_mastering_job(
    db: Session,
    user_id: uuid.UUID,
    original_file_id: uuid.UUID,
    service: MasteringServiceType, # Ensure this is the enum object or its string value
    service_job_id: Optional[str],
    status: JobStatus, # Ensure this is the enum object or its string value
    request_options: Optional[Dict[str, Any]] = None
) -> AudioMasteringJob:
    """
    Create a new audio mastering job record.
    """
    db_job = AudioMasteringJob(
        user_id=user_id,
        original_file_id=original_file_id,
        service=service, # SQLAlchemy handles enum conversion
        service_job_id=service_job_id,
        status=status, # SQLAlchemy handles enum conversion
        request_options=request_options
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

def get_mastering_job(db: Session, job_id: uuid.UUID) -> Optional[AudioMasteringJob]:
    """
    Get an audio mastering job by its internal ID.
    """
    return db.query(AudioMasteringJob).filter(AudioMasteringJob.id == job_id).first()

def get_mastering_jobs_by_user(
    db: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> List[AudioMasteringJob]:
    """
    Get all mastering jobs for a specific user.
    """
    return (
        db.query(AudioMasteringJob)
        .filter(AudioMasteringJob.user_id == user_id)
        .order_by(AudioMasteringJob.created_at.desc()) # type: ignore
        .offset(skip)
        .limit(limit)
        .all()
    )

def update_mastering_job_status(
    db: Session,
    job_id: uuid.UUID,
    status: JobStatus, # Ensure this is the enum object or its string value
    progress: Optional[float] = None,
    service_response_details: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None
) -> Optional[AudioMasteringJob]:
    """
    Update the status, progress, and other details of a mastering job.
    """
    db_job = get_mastering_job(db, job_id=job_id)
    if db_job:
        db_job.status = status # SQLAlchemy handles enum conversion
        if progress is not None:
            db_job.progress = progress
        if service_response_details is not None:
            db_job.service_response_details = service_response_details
        if error_message is not None:
            db_job.error_message = error_message
        else: # Clear error message if status is not failed/error
            if status not in [JobStatus.FAILED, JobStatus.SERVICE_ERROR, JobStatus.DOWNLOAD_FAILED]:
                db_job.error_message = None

        db.commit()
        db.refresh(db_job)
    return db_job

def set_mastered_file_id(
    db: Session, job_id: uuid.UUID, mastered_file_id: uuid.UUID
) -> Optional[AudioMasteringJob]:
    """
    Link the mastered audio file (AudioFile record ID) to the mastering job.
    """
    db_job = get_mastering_job(db, job_id=job_id)
    if db_job:
        db_job.mastered_file_id = mastered_file_id
        db_job.status = JobStatus.COMPLETED # Ensure status is COMPLETED
        if db_job.progress is None or db_job.progress < 100.0: # Set progress to 100 if not already
             db_job.progress = 100.0
        db_job.error_message = None # Clear any previous error
        db.commit()
        db.refresh(db_job)
    return db_job

def update_service_job_id(
    db: Session, job_id: uuid.UUID, service_job_id: str
) -> Optional[AudioMasteringJob]:
    """
    Update the external service's job ID for a mastering job.
    Useful if the service job ID is obtained after initial job creation.
    """
    db_job = get_mastering_job(db, job_id=job_id)
    if db_job:
        db_job.service_job_id = service_job_id
        db.commit()
        db.refresh(db_job)
    return db_job

def delete_mastering_job(db: Session, job_id: uuid.UUID) -> Optional[AudioMasteringJob]:
    """
    Delete a mastering job record.
    Consider if this should be a soft delete or hard delete.
    For now, it's a hard delete.
    """
    db_job = get_mastering_job(db, job_id=job_id)
    if db_job:
        db.delete(db_job)
        db.commit()
    return db_job

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Path, Body
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import uuid
import os
import structlog
import httpx

from app.db.database import get_db # Sync session provider
from app.core.security import get_current_active_user
from app.core.config import settings
from app.models.user import User
from app.models.audio_file import AudioFile as AudioFileModel
from app.models.audio_mastering_job import AudioMasteringJob, MasteringServiceType, JobStatus

# Import CRUD modules
from app.crud import crud_audio_mastering_job
from app.crud.crud_audio_file import create_sync_derived_audio_file # Specific sync function

from app.services.landr_mastering import LANDRMasteringService
from app.schemas.audio_processing import MasteringRequest, MasteringJobCreateResponse, MasteringJobStatusResponse

logger = structlog.get_logger(__name__)
router = APIRouter()

@router.post("/{file_id}/master", response_model=MasteringJobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def master_audio_file(
    file_id: uuid.UUID = Path(..., description="ID of the audio file to master"),
    mastering_options: MasteringRequest = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    landr_service: LANDRMasteringService = Depends(LANDRMasteringService)
):
    audio_file = db.query(AudioFileModel).filter(AudioFileModel.id == file_id).first()
    if not audio_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found")

    if audio_file.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User does not have access to this file")

    if not audio_file.file_path or not os.path.exists(audio_file.file_path):
        logger.error("Physical file not found for mastering", file_path=audio_file.file_path, file_id=file_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Physical audio file not found")

    if not landr_service.is_configured():
        logger.error("LANDR API Key is not configured.")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Mastering service is not configured.")

    try:
        with open(audio_file.file_path, "rb") as f:
            upload_result = await landr_service.upload_audio_for_mastering(
                audio_file=f,
                filename=audio_file.original_filename or audio_file.filename,
                mastering_options=mastering_options.dict()
            )

        if not upload_result.get("success"):
            logger.error("LANDR upload failed", error=upload_result.get("error"), details=upload_result.get("details"))
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to initiate mastering: {upload_result.get('error')}")

        landr_job_id = upload_result.get("job_id")

        db_mastering_job = crud_audio_mastering_job.create_mastering_job(
            db=db,
            user_id=current_user.id,
            original_file_id=file_id,
            service=MasteringServiceType.LANDR,
            service_job_id=landr_job_id,
            status=JobStatus.PROCESSING, # LANDR status might be 'processing' or similar
            request_options=mastering_options.dict()
        )
        logger.info("LANDR mastering job created in DB", db_job_id=db_mastering_job.id, landr_job_id=landr_job_id, file_id=file_id)

        return MasteringJobCreateResponse(
            job_id=db_mastering_job.id,
            file_id=file_id,
            service_job_id=landr_job_id,
            status=db_mastering_job.status.value, # Return enum's value
            message="Mastering job initiated successfully with LANDR."
        )

    except FileNotFoundError:
        logger.error("File not found during mastering process", file_path=audio_file.file_path)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Audio file missing on server.")
    except httpx.HTTPStatusError as e:
        logger.error("LANDR API HTTPStatusError", error=str(e), response_text=e.response.text)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"LANDR API error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        logger.error("Error during mastering process", error=str(e), exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {str(e)}")


@router.get("/{file_id}/master/{job_id}/status", response_model=MasteringJobStatusResponse)
async def get_mastering_job_status(
    file_id: uuid.UUID = Path(..., description="ID of the original audio file"),
    job_id: uuid.UUID = Path(..., description="Internal ID of the mastering job"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    landr_service: LANDRMasteringService = Depends(LANDRMasteringService)
):
    db_job = crud_audio_mastering_job.get_mastering_job(db, job_id=job_id)

    if not db_job or db_job.original_file_id != file_id or db_job.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mastering job not found or access denied.")

    download_url_for_response = None
    if db_job.status == JobStatus.COMPLETED and db_job.mastered_file_id:
        download_url_for_response = f"{settings.API_V1_STR}/audio/{file_id}/master/{job_id}/download"
        return MasteringJobStatusResponse(
            job_id=db_job.id,
            file_id=db_job.original_file_id,
            status=db_job.status.value,
            progress=100.0,
            mastered_file_id=db_job.mastered_file_id,
            download_url=download_url_for_response
        )

    if db_job.status == JobStatus.FAILED or db_job.status == JobStatus.SERVICE_ERROR or db_job.status == JobStatus.DOWNLOAD_FAILED :
        return MasteringJobStatusResponse(
            job_id=db_job.id,
            file_id=db_job.original_file_id,
            status=db_job.status.value,
            error_message=db_job.error_message or "Mastering process encountered an error."
        )

    if not db_job.service_job_id: # Should not happen if created correctly
        logger.error("Service job ID missing for job", db_job_id=db_job.id)
        crud_audio_mastering_job.update_mastering_job_status(db, job_id=job_id, status=JobStatus.FAILED, error_message="Internal configuration error: Service job ID missing.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Mastering job misconfigured.")

    # Poll LANDR for status if job is still processing according to our DB
    if db_job.status == JobStatus.PROCESSING or db_job.status == JobStatus.PENDING:
        status_result = await landr_service.check_mastering_status(db_job.service_job_id)

        if not status_result.get("success"):
            error_detail = status_result.get('error', 'Unknown error from LANDR status check')
            logger.error("Failed to check LANDR status", landr_job_id=db_job.service_job_id, error=error_detail)
            crud_audio_mastering_job.update_mastering_job_status(db, job_id=job_id, status=JobStatus.SERVICE_ERROR, error_message=f"LANDR status check failed: {error_detail}")
            # Return current DB status with error context
            return MasteringJobStatusResponse(
                job_id=db_job.id,
                file_id=db_job.original_file_id,
                status=JobStatus.SERVICE_ERROR.value,
                error_message=f"LANDR status check failed: {error_detail}",
                service_status=status_result
            )

        current_landr_status_str = status_result.get("status", "").lower()
        progress = float(status_result.get("progress", db_job.progress or 0.0))

        new_db_status = db_job.status # Default to current
        if current_landr_status_str == "completed":
            new_db_status = JobStatus.COMPLETED
            progress = 100.0
            logger.info("LANDR mastering job completed", landr_job_id=db_job.service_job_id, db_job_id=db_job.id)
            download_url_for_response = f"{settings.API_V1_STR}/audio/{file_id}/master/{job_id}/download"
        elif current_landr_status_str == "failed":
            new_db_status = JobStatus.FAILED
            logger.error("LANDR mastering job failed", landr_job_id=db_job.service_job_id, db_job_id=db_job.id, details=status_result)
        elif current_landr_status_str == "processing": # or other active states
            new_db_status = JobStatus.PROCESSING

        if new_db_status != db_job.status or progress != db_job.progress:
             crud_audio_mastering_job.update_mastering_job_status(db, job_id=job_id, status=new_db_status, progress=progress)

        return MasteringJobStatusResponse(
            job_id=db_job.id,
            file_id=db_job.original_file_id,
            status=new_db_status.value,
            progress=progress,
            service_status=status_result, # Full LANDR response for context
            download_url=download_url_for_response,
            mastered_file_id=db_job.mastered_file_id # Could be set by a background worker
        )

    # Fallback for any other status not explicitly handled by polling logic
    return MasteringJobStatusResponse(
        job_id=db_job.id,
        file_id=db_job.original_file_id,
        status=db_job.status.value,
        progress=db_job.progress,
        mastered_file_id=db_job.mastered_file_id
    )


@router.get("/{file_id}/master/{job_id}/download")
async def download_mastered_audio_file(
    file_id: uuid.UUID = Path(..., description="ID of the original audio file"),
    job_id: uuid.UUID = Path(..., description="Internal ID of the mastering job"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    landr_service: LANDRMasteringService = Depends(LANDRMasteringService)
):
    db_job = crud_audio_mastering_job.get_mastering_job(db, job_id=job_id)

    if not db_job or db_job.original_file_id != file_id or db_job.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mastering job not found or access denied.")

    original_audio_file = db.query(AudioFileModel).filter(AudioFileModel.id == db_job.original_file_id).first()
    if not original_audio_file:
        logger.error("Original audio file for job not found in DB", job_id=job_id, original_file_id=db_job.original_file_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original audio file data not found.")

    if db_job.mastered_file_id:
        mastered_audio_file_record = db.query(AudioFileModel).filter(AudioFileModel.id == db_job.mastered_file_id).first()
        if mastered_audio_file_record and mastered_audio_file_record.file_path and os.path.exists(mastered_audio_file_record.file_path):
            logger.info("Serving previously downloaded mastered file", mastered_file_path=mastered_audio_file_record.file_path)
            return FileResponse(
                path=mastered_audio_file_record.file_path,
                filename=f"mastered_{mastered_audio_file_record.original_filename or mastered_audio_file_record.filename}",
                media_type=mastered_audio_file_record.mime_type or "audio/wav"
            )
        else:
            logger.warning("Mastered file record exists but physical file missing or path error", mastered_file_id=db_job.mastered_file_id, path_exists=os.path.exists(mastered_audio_file_record.file_path) if mastered_audio_file_record and mastered_audio_file_record.file_path else False)

    if db_job.status != JobStatus.COMPLETED:
        # Optionally, re-check status before denying download
        status_response = await get_mastering_job_status(file_id, job_id, db, current_user, landr_service)
        if status_response.status != JobStatus.COMPLETED.value: # Compare with enum value
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Mastering job not yet completed. Current status: {status_response.status}")

    if not db_job.service_job_id:
        logger.error("Service job ID missing for completed job, cannot download", db_job_id=db_job.id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Mastering job misconfigured, cannot download.")

    logger.info("Attempting to download mastered audio from LANDR", landr_job_id=db_job.service_job_id, db_job_id=db_job.id)
    download_result = await landr_service.download_mastered_audio(db_job.service_job_id)

    if not download_result.get("success"):
        error_detail = download_result.get('error', 'Unknown error from LANDR download')
        logger.error("Failed to download from LANDR", landr_job_id=db_job.service_job_id, error=error_detail)
        crud_audio_mastering_job.update_mastering_job_status(db, job_id=job_id, status=JobStatus.DOWNLOAD_FAILED, error_message=f"LANDR download failed: {error_detail}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to download mastered file: {error_detail}")

    audio_data = download_result.get("audio_data")
    content_type = download_result.get("content_type", "audio/wav")

    file_extension = ".wav"
    if content_type == "audio/mpeg": file_extension = ".mp3"
    elif content_type == "audio/flac": file_extension = ".flac"
    elif content_type == "audio/aac": file_extension = ".aac"

    os.makedirs(settings.UPLOAD_PATH, exist_ok=True)
    mastered_file_uuid = uuid.uuid4()
    mastered_filename_on_disk = f"{mastered_file_uuid}{file_extension}"
    mastered_file_path = os.path.join(settings.UPLOAD_PATH, mastered_filename_on_disk)

    try:
        with open(mastered_file_path, "wb") as f:
            f.write(audio_data)
        logger.info("Mastered file saved to disk", path=mastered_file_path, db_job_id=db_job.id)
    except Exception as e:
        logger.error("Failed to save mastered file to disk", path=mastered_file_path, error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not save mastered file locally.")

    mastered_audio_file_db = create_sync_derived_audio_file(
        db=db,
        user_id=current_user.id,
        original_audio_file_model=original_audio_file,
        new_filename=mastered_filename_on_disk,
        new_original_filename=f"mastered_{original_audio_file.original_filename or original_audio_file.filename}",
        new_file_path=mastered_file_path,
        new_file_size=len(audio_data),
        new_mime_type=content_type,
        # Potentially extract duration, sample_rate, channels, bit_rate from audio_data here if needed
    )

    crud_audio_mastering_job.set_mastered_file_id(db, job_id=job_id, mastered_file_id=mastered_audio_file_db.id)
    logger.info("Created AudioFile record for mastered track", mastered_file_id=mastered_audio_file_db.id, db_job_id=db_job.id)

    return FileResponse(
        path=mastered_file_path,
        filename=mastered_audio_file_db.original_filename,
        media_type=content_type
    )


# --- Matchering Endpoint ---

from app.services.matchering_service import MatcheringService
from app.schemas.audio_processing import MatcheringRequest # Assuming this is defined
from fastapi import BackgroundTasks # Import BackgroundTasks

async def run_matchering_background_task(
    db_job_id: uuid.UUID,
    target_file_path: str,
    reference_file_path: str,
    original_target_file_id: uuid.UUID, # Used for naming the output, and linking
    current_user_id: uuid.UUID,
    matchering_options: Dict[str, Any],
    db_provider: callable, # To get a new DB session in the background task
    matchering_service_instance: MatcheringService # Pass the instance
):
    """
    Background task to run matchering and update DB.
    """
    logger.info("Matchering background task started", db_job_id=db_job_id)
    db: Session = next(db_provider()) # Get a new DB session for this task

    try:
        # Ensure output directory exists for matchering service (or handled by service)
        # Typically, the service's temp_dir is used.
        # We need a unique filename for the result.
        result_filename_base = f"matchering_mastered_{db_job_id}"

        success, result_msg_or_path, log_file_path = await matchering_service_instance.run_matchering_processing(
            target_file_path=target_file_path,
            reference_file_path=reference_file_path,
            # output_dir is handled by service's self.temp_dir
            # result_filename=result_filename_base, # Service generates unique name
            options=matchering_options
        )

        if success:
            mastered_file_path = result_msg_or_path
            logger.info("Matchering processing successful in background", db_job_id=db_job_id, mastered_file=mastered_file_path)

            original_audio_file = db.query(AudioFileModel).filter(AudioFileModel.id == original_target_file_id).first()
            if not original_audio_file:
                # This should ideally not happen if IDs are correct
                logger.error("Original target file not found in DB for background task", id=original_target_file_id)
                crud_audio_mastering_job.update_mastering_job_status(db, job_id=db_job_id, status=JobStatus.FAILED, error_message="Original file data lost.")
                return

            # Create AudioFile record for the mastered track
            # Determine file extension from mastered_file_path (e.g. .wav)
            _, mastered_file_extension = os.path.splitext(mastered_file_path)
            mastered_content_type = "audio/wav" # Default for Matchering, adjust if it can output others
            if mastered_file_extension.lower() == ".mp3": mastered_content_type = "audio/mpeg"

            mastered_audio_file_db = create_sync_derived_audio_file(
                db=db,
                user_id=current_user_id,
                original_audio_file_model=original_audio_file,
                new_filename=os.path.basename(mastered_file_path), # Filename on disk
                new_original_filename=f"matchering_{original_audio_file.original_filename or original_audio_file.filename}",
                new_file_path=mastered_file_path,
                new_file_size=os.path.getsize(mastered_file_path),
                new_mime_type=mastered_content_type,
                processing_log={"matchering_log_file": log_file_path} # Store log file path
            )

            crud_audio_mastering_job.set_mastered_file_id(db, job_id=db_job_id, mastered_file_id=mastered_audio_file_db.id)
            # Status is already set to COMPLETED by set_mastered_file_id
            logger.info("Matchering job completed and DB updated", db_job_id=db_job_id, mastered_file_id=mastered_audio_file_db.id)

        else:
            error_message = result_msg_or_path
            logger.error("Matchering processing failed in background", db_job_id=db_job_id, error=error_message)
            crud_audio_mastering_job.update_mastering_job_status(db, job_id=db_job_id, status=JobStatus.FAILED, error_message=error_message)

    except Exception as e:
        logger.error("Exception in Matchering background task", db_job_id=db_job_id, error=str(e), exc_info=True)
        crud_audio_mastering_job.update_mastering_job_status(db, job_id=db_job_id, status=JobStatus.FAILED, error_message=f"Unexpected background task error: {str(e)}")
    finally:
        db.close()


@router.post("/{file_id}/matchering-master", response_model=MasteringJobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def matchering_master_audio_file(
    file_id: uuid.UUID = Path(..., description="ID of the target audio file to master"),
    reference_file_id: uuid.UUID = Body(..., description="ID of the reference audio file"),
    # TODO: Add Matchering specific options to a Pydantic model if needed, e.g. MatcheringRequestBody
    # For now, passing options as a dict from a generic MasteringRequest or a new schema
    matchering_options: MatcheringRequest = Body(default_factory=MatcheringRequest), # Use the schema
    background_tasks: BackgroundTasks = Depends(), # Correct way to inject BackgroundTasks
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    matchering_service: MatcheringService = Depends(MatcheringService) # Dependency inject service
):
    if not matchering_service.is_available():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Matchering service is not available (library not installed).")

    target_audio_file = db.query(AudioFileModel).filter(AudioFileModel.id == file_id).first()
    if not target_audio_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target audio file not found.")
    if target_audio_file.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User does not have access to the target file.")
    if not target_audio_file.file_path or not os.path.exists(target_audio_file.file_path):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Target audio file path missing or file not found on server.")

    reference_audio_file = db.query(AudioFileModel).filter(AudioFileModel.id == reference_file_id).first()
    if not reference_audio_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference audio file not found.")
    # Optional: Check if user has access to reference file if it's not public, or if it's their own
    if reference_audio_file.user_id != current_user.id and not reference_audio_file.is_public:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User does not have access to the reference file.")
    if not reference_audio_file.file_path or not os.path.exists(reference_audio_file.file_path):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Reference audio file path missing or file not found on server.")

    # Create initial job record
    db_mastering_job = crud_audio_mastering_job.create_mastering_job(
        db=db,
        user_id=current_user.id,
        original_file_id=file_id,
        service=MasteringServiceType.MATCHERIN_LOCAL,
        service_job_id=None, # Matchering is local, no external service job ID
        status=JobStatus.PENDING,
        request_options=matchering_options.dict() # Store options used
    )

    logger.info("Matchering job created in DB, adding to background tasks", db_job_id=db_mastering_job.id, target_id=file_id, ref_id=reference_file_id)

    background_tasks.add_task(
        run_matchering_background_task,
        db_job_id=db_mastering_job.id,
        target_file_path=target_audio_file.file_path,
        reference_file_path=reference_audio_file.file_path,
        original_target_file_id=target_audio_file.id, # Pass original target ID
        current_user_id=current_user.id,
        matchering_options=matchering_options.dict(),
        db_provider=get_db, # Pass the db session provider
        matchering_service_instance=matchering_service
    )

    return MasteringJobCreateResponse(
        job_id=db_mastering_job.id,
        file_id=file_id,
        service_job_id=None, # No external service job_id for local matchering
        status=db_mastering_job.status.value,
        message="Matchering job accepted and started in background."
    )


# Final inclusion in app/api/v1/api.py should be:
# from app.api.v1 import audio_processing_api
# api_router.include_router(audio_processing_api.router, prefix="/audio", tags=["Audio Processing"])
# (Assuming this router instance is named 'router' in this file)

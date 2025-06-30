from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Path, Body
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession # Changed import
import uuid
import os
import structlog
import httpx
from fastapi.concurrency import run_in_threadpool # For blocking file ops
import aiofiles # For async file writing

from app.db.database import get_async_db # Changed import
from app.core.security import get_current_active_user
from app.core.config import settings
from app.models.user import User
from app.models.audio_file import AudioFile as AudioFileModel
from app.models.audio_mastering_job import AudioMasteringJob, MasteringServiceType, JobStatus

# Import CRUD modules (assuming they are now async)
from app.crud import crud_audio_mastering_job as async_crud_amj
from app.crud.crud_audio_file import audio_file as async_crud_audio_file, create_async_derived_audio_file # Updated import

from app.services.landr_mastering import LANDRMasteringService
from app.schemas.audio_processing import MasteringRequest, MasteringJobCreateResponse, MasteringJobStatusResponse

logger = structlog.get_logger(__name__)
router = APIRouter()

@router.post("/{file_id}/master", response_model=MasteringJobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def master_audio_file(
    file_id: uuid.UUID = Path(..., description="ID of the audio file to master"),
    mastering_options: MasteringRequest = Body(...),
    db: AsyncSession = Depends(get_async_db), # Changed
    current_user: User = Depends(get_current_active_user),
    landr_service: LANDRMasteringService = Depends(LANDRMasteringService)
):
    audio_file = await async_crud_audio_file.get(db, id=file_id) # await
    if not audio_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found")

    if audio_file.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User does not have access to this file")

    if not audio_file.file_path or not await run_in_threadpool(os.path.exists, audio_file.file_path): # await
        logger.error("Physical file not found for mastering", file_path=audio_file.file_path, file_id=file_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Physical audio file not found")

    if not landr_service.is_configured():
        logger.error("LANDR API Key is not configured.")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Mastering service is not configured.")

    try:
        # Reading file content for upload needs to be async or threadpool
        async with aiofiles.open(audio_file.file_path, "rb") as f:
            file_content = await f.read()

        # Pass content to service. LANDRMasteringService.upload_audio_for_mastering should handle bytes.
        # If it expects a file-like object, use io.BytesIO(file_content)
        import io
        upload_result = await landr_service.upload_audio_for_mastering(
            audio_file=io.BytesIO(file_content), # Pass bytes as a file-like object
            filename=audio_file.original_filename or audio_file.filename,
            mastering_options=mastering_options.dict()
        )

        if not upload_result.get("success"):
            logger.error("LANDR upload failed", error=upload_result.get("error"), details=upload_result.get("details"))
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to initiate mastering: {upload_result.get('error')}")

        landr_job_id = upload_result.get("job_id")

        db_mastering_job = await async_crud_amj.create_mastering_job( # await
            db=db,
            user_id=current_user.id,
            original_file_id=file_id,
            service=MasteringServiceType.LANDR,
            service_job_id=landr_job_id,
            status=JobStatus.PROCESSING,
            request_options=mastering_options.dict()
        )
        logger.info("LANDR mastering job created in DB", db_job_id=db_mastering_job.id, landr_job_id=landr_job_id, file_id=file_id)

        return MasteringJobCreateResponse(
            job_id=db_mastering_job.id,
            file_id=file_id,
            service_job_id=landr_job_id,
            status=db_mastering_job.status.value,
            message="Mastering job initiated successfully with LANDR."
        )

    except FileNotFoundError: # This might be less likely if os.path.exists is checked first
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
    db: AsyncSession = Depends(get_async_db), # Changed
    current_user: User = Depends(get_current_active_user),
    landr_service: LANDRMasteringService = Depends(LANDRMasteringService)
):
    db_job = await async_crud_amj.get_mastering_job(db, job_id=job_id) # await

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

    if db_job.status in [JobStatus.FAILED, JobStatus.SERVICE_ERROR, JobStatus.DOWNLOAD_FAILED]: # Simplified check
        return MasteringJobStatusResponse(
            job_id=db_job.id,
            file_id=db_job.original_file_id,
            status=db_job.status.value,
            error_message=db_job.error_message or "Mastering process encountered an error."
        )

    if not db_job.service_job_id:
        logger.error("Service job ID missing for job", db_job_id=db_job.id)
        await async_crud_amj.update_mastering_job_status(db, job_id=job_id, status=JobStatus.FAILED, error_message="Internal configuration error: Service job ID missing.") # await
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Mastering job misconfigured.")

    if db_job.status == JobStatus.PROCESSING or db_job.status == JobStatus.PENDING:
        status_result = await landr_service.check_mastering_status(db_job.service_job_id)

        if not status_result.get("success"):
            error_detail = status_result.get('error', 'Unknown error from LANDR status check')
            logger.error("Failed to check LANDR status", landr_job_id=db_job.service_job_id, error=error_detail)
            await async_crud_amj.update_mastering_job_status(db, job_id=job_id, status=JobStatus.SERVICE_ERROR, error_message=f"LANDR status check failed: {error_detail}") # await
            return MasteringJobStatusResponse(
                job_id=db_job.id,
                file_id=db_job.original_file_id,
                status=JobStatus.SERVICE_ERROR.value,
                error_message=f"LANDR status check failed: {error_detail}",
                service_status=status_result
            )

        current_landr_status_str = status_result.get("status", "").lower()
        progress = float(status_result.get("progress", db_job.progress or 0.0))
        new_db_status = db_job.status

        if current_landr_status_str == "completed":
            new_db_status = JobStatus.COMPLETED
            progress = 100.0
            logger.info("LANDR mastering job completed", landr_job_id=db_job.service_job_id, db_job_id=db_job.id)
            download_url_for_response = f"{settings.API_V1_STR}/audio/{file_id}/master/{job_id}/download"
        elif current_landr_status_str == "failed":
            new_db_status = JobStatus.FAILED
            logger.error("LANDR mastering job failed", landr_job_id=db_job.service_job_id, db_job_id=db_job.id, details=status_result)
        elif current_landr_status_str == "processing":
            new_db_status = JobStatus.PROCESSING

        if new_db_status != db_job.status or progress != db_job.progress:
             await async_crud_amj.update_mastering_job_status(db, job_id=job_id, status=new_db_status, progress=progress) # await

        return MasteringJobStatusResponse(
            job_id=db_job.id,
            file_id=db_job.original_file_id,
            status=new_db_status.value,
            progress=progress,
            service_status=status_result,
            download_url=download_url_for_response,
            mastered_file_id=db_job.mastered_file_id
        )

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
    db: AsyncSession = Depends(get_async_db), # Changed
    current_user: User = Depends(get_current_active_user),
    landr_service: LANDRMasteringService = Depends(LANDRMasteringService)
):
    db_job = await async_crud_amj.get_mastering_job(db, job_id=job_id) # await

    if not db_job or db_job.original_file_id != file_id or db_job.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mastering job not found or access denied.")

    original_audio_file = await async_crud_audio_file.get(db, id=db_job.original_file_id) # await
    if not original_audio_file:
        logger.error("Original audio file for job not found in DB", job_id=job_id, original_file_id=db_job.original_file_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original audio file data not found.")

    if db_job.mastered_file_id:
        mastered_audio_file_record = await async_crud_audio_file.get(db, id=db_job.mastered_file_id) # await
        if mastered_audio_file_record and mastered_audio_file_record.file_path and \
           await run_in_threadpool(os.path.exists, mastered_audio_file_record.file_path): # await
            logger.info("Serving previously downloaded mastered file", mastered_file_path=mastered_audio_file_record.file_path)
            return FileResponse(
                path=mastered_audio_file_record.file_path,
                filename=f"mastered_{mastered_audio_file_record.original_filename or mastered_audio_file_record.filename}",
                media_type=mastered_audio_file_record.mime_type or "audio/wav"
            )
        else:
            path_exists_check = False
            if mastered_audio_file_record and mastered_audio_file_record.file_path:
                path_exists_check = await run_in_threadpool(os.path.exists, mastered_audio_file_record.file_path)
            logger.warning("Mastered file record exists but physical file missing or path error", mastered_file_id=db_job.mastered_file_id, path_exists=path_exists_check)

    if db_job.status != JobStatus.COMPLETED:
        status_response = await get_mastering_job_status(file_id, job_id, db, current_user, landr_service) # await is implicit as it's an async call
        if status_response.status != JobStatus.COMPLETED.value:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Mastering job not yet completed. Current status: {status_response.status}")

    if not db_job.service_job_id:
        logger.error("Service job ID missing for completed job, cannot download", db_job_id=db_job.id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Mastering job misconfigured, cannot download.")

    logger.info("Attempting to download mastered audio from LANDR", landr_job_id=db_job.service_job_id, db_job_id=db_job.id)
    download_result = await landr_service.download_mastered_audio(db_job.service_job_id)

    if not download_result.get("success"):
        error_detail = download_result.get('error', 'Unknown error from LANDR download')
        logger.error("Failed to download from LANDR", landr_job_id=db_job.service_job_id, error=error_detail)
        await async_crud_amj.update_mastering_job_status(db, job_id=job_id, status=JobStatus.DOWNLOAD_FAILED, error_message=f"LANDR download failed: {error_detail}") # await
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Failed to download mastered file: {error_detail}")

    audio_data = download_result.get("audio_data")
    content_type = download_result.get("content_type", "audio/wav")

    file_extension = ".wav"
    if content_type == "audio/mpeg": file_extension = ".mp3"
    elif content_type == "audio/flac": file_extension = ".flac"
    elif content_type == "audio/aac": file_extension = ".aac"

    await run_in_threadpool(os.makedirs, settings.UPLOAD_PATH, exist_ok=True) # await
    mastered_file_uuid = uuid.uuid4()
    mastered_filename_on_disk = f"{mastered_file_uuid}{file_extension}"
    mastered_file_path = os.path.join(settings.UPLOAD_PATH, mastered_filename_on_disk)

    try:
        async with aiofiles.open(mastered_file_path, "wb") as f: # async write
            await f.write(audio_data)
        logger.info("Mastered file saved to disk", path=mastered_file_path, db_job_id=db_job.id)
    except Exception as e:
        logger.error("Failed to save mastered file to disk", path=mastered_file_path, error=str(e))
        # Attempt to clean up partially written file
        if await run_in_threadpool(os.path.exists, mastered_file_path):
            await run_in_threadpool(os.remove, mastered_file_path)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not save mastered file locally.")

    mastered_audio_file_db = await create_async_derived_audio_file( # await and use async version
        db=db,
        user_id=current_user.id,
        original_audio_file_model=original_audio_file,
        new_filename=mastered_filename_on_disk,
        new_original_filename=f"mastered_{original_audio_file.original_filename or original_audio_file.filename}",
        new_file_path=mastered_file_path,
        new_file_size=len(audio_data),
        new_mime_type=content_type,
    )

    await async_crud_amj.set_mastered_file_id(db, job_id=job_id, mastered_file_id=mastered_audio_file_db.id) # await
    logger.info("Created AudioFile record for mastered track", mastered_file_id=mastered_audio_file_db.id, db_job_id=db_job.id)

    return FileResponse(
        path=mastered_file_path,
        filename=mastered_audio_file_db.original_filename,
        media_type=content_type
    )


# --- Matchering Endpoint ---

from app.services.matchering_service import MatcheringService
from app.schemas.audio_processing import MatcheringRequest
from fastapi import BackgroundTasks

async def run_matchering_background_task(
    db_job_id: uuid.UUID,
    target_file_path: str,
    reference_file_path: str,
    original_target_file_id: uuid.UUID,
    current_user_id: uuid.UUID,
    matchering_options: Dict[str, Any],
    # db_provider: callable, # Changed to pass session directly if BackgroundTasks allows async context
    matchering_service_instance: MatcheringService
):
    logger.info("Matchering background task started", db_job_id=db_job_id)

    # Get a new async DB session for this task
    # This assumes BackgroundTasks can handle async functions correctly.
    # If not, this part needs careful management of event loops or running sync in threadpool.
    db: AsyncSession = None
    try:
        db = await anext(get_async_db()) # Get an async session

        success, result_msg_or_path, log_file_path = await matchering_service_instance.run_matchering_processing(
            target_file_path=target_file_path,
            reference_file_path=reference_file_path,
            options=matchering_options
        )

        if success:
            mastered_file_path = result_msg_or_path
            logger.info("Matchering processing successful in background", db_job_id=db_job_id, mastered_file=mastered_file_path)

            original_audio_file = await async_crud_audio_file.get(db, id=original_target_file_id) # await
            if not original_audio_file:
                logger.error("Original target file not found in DB for background task", id=original_target_file_id)
                await async_crud_amj.update_mastering_job_status(db, job_id=db_job_id, status=JobStatus.FAILED, error_message="Original file data lost.") # await
                return

            _, mastered_file_extension = os.path.splitext(mastered_file_path)
            mastered_content_type = "audio/wav"
            if mastered_file_extension.lower() == ".mp3": mastered_content_type = "audio/mpeg"

            mastered_audio_file_db = await create_async_derived_audio_file( # await
                db=db,
                user_id=current_user_id,
                original_audio_file_model=original_audio_file,
                new_filename=os.path.basename(mastered_file_path),
                new_original_filename=f"matchering_{original_audio_file.original_filename or original_audio_file.filename}",
                new_file_path=mastered_file_path,
                new_file_size=await run_in_threadpool(os.path.getsize, mastered_file_path), # await
                new_mime_type=mastered_content_type,
                processing_log={"matchering_log_file": log_file_path}
            )

            await async_crud_amj.set_mastered_file_id(db, job_id=db_job_id, mastered_file_id=mastered_audio_file_db.id) # await
            logger.info("Matchering job completed and DB updated", db_job_id=db_job_id, mastered_file_id=mastered_audio_file_db.id)

        else:
            error_message = result_msg_or_path
            logger.error("Matchering processing failed in background", db_job_id=db_job_id, error=error_message)
            await async_crud_amj.update_mastering_job_status(db, job_id=db_job_id, status=JobStatus.FAILED, error_message=error_message) # await

    except Exception as e:
        logger.error("Exception in Matchering background task", db_job_id=db_job_id, error=str(e), exc_info=True)
        if db: # Ensure db session is available before trying to update status
            await async_crud_amj.update_mastering_job_status(db, job_id=db_job_id, status=JobStatus.FAILED, error_message=f"Unexpected background task error: {str(e)}") # await
    finally:
        if db: # Ensure db session is available before trying to close
            await db.close()


@router.post("/{file_id}/matchering-master", response_model=MasteringJobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
async def matchering_master_audio_file(
    file_id: uuid.UUID = Path(..., description="ID of the target audio file to master"),
    reference_file_id: uuid.UUID = Body(..., description="ID of the reference audio file"),
    matchering_options: MatcheringRequest = Body(default_factory=MatcheringRequest),
    background_tasks: BackgroundTasks = Depends(),
    db: AsyncSession = Depends(get_async_db), # Changed
    current_user: User = Depends(get_current_active_user),
    matchering_service: MatcheringService = Depends(MatcheringService)
):
    if not matchering_service.is_available(): # This is likely a sync check
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Matchering service is not available (library not installed).")

    target_audio_file = await async_crud_audio_file.get(db, id=file_id) # await
    if not target_audio_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target audio file not found.")
    if target_audio_file.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User does not have access to the target file.")
    if not target_audio_file.file_path or not await run_in_threadpool(os.path.exists, target_audio_file.file_path): # await
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Target audio file path missing or file not found on server.")

    reference_audio_file = await async_crud_audio_file.get(db, id=reference_file_id) # await
    if not reference_audio_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference audio file not found.")
    if reference_audio_file.user_id != current_user.id and not reference_audio_file.is_public:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User does not have access to the reference file.")
    if not reference_audio_file.file_path or not await run_in_threadpool(os.path.exists, reference_audio_file.file_path): # await
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Reference audio file path missing or file not found on server.")

    db_mastering_job = await async_crud_amj.create_mastering_job( # await
        db=db,
        user_id=current_user.id,
        original_file_id=file_id,
        service=MasteringServiceType.MATCHERIN_LOCAL,
        service_job_id=None,
        status=JobStatus.PENDING,
        request_options=matchering_options.dict()
    )

    logger.info("Matchering job created in DB, adding to background tasks", db_job_id=db_mastering_job.id, target_id=file_id, ref_id=reference_file_id)

    background_tasks.add_task(
        run_matchering_background_task, # This task is now async
        db_job_id=db_mastering_job.id,
        target_file_path=target_audio_file.file_path,
        reference_file_path=reference_audio_file.file_path,
        original_target_file_id=target_audio_file.id,
        current_user_id=current_user.id,
        matchering_options=matchering_options.dict(),
        # db_provider=get_async_db, # Pass async provider, task will resolve it
        matchering_service_instance=matchering_service
    )

    return MasteringJobCreateResponse(
        job_id=db_mastering_job.id,
        file_id=file_id,
        service_job_id=None,
        status=db_mastering_job.status.value,
        message="Matchering job accepted and started in background."
    )

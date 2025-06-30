import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.crud.base import CRUDBase
from app.models.processing_job import ProcessingJobDB
from app.schemas.processing_job import ProcessingJobCreate, ProcessingJobUpdate
from app.services.master_chain_orchestrator import ProcessingStatus # For type hinting status

class CRUDProcessingJob(CRUDBase[ProcessingJobDB, ProcessingJobCreate, ProcessingJobUpdate]):
    async def create_job(self, db: AsyncSession, *, job_in: ProcessingJobCreate) -> ProcessingJobDB:
        """
        Create a new processing job.
        This is essentially the base create method but can be customized if needed.
        """
        return await super().create(db, obj_in=job_in)

    async def get_job_by_id(self, db: AsyncSession, job_id: uuid.UUID) -> Optional[ProcessingJobDB]:
        """
        Get a processing job by its ID.
        """
        return await super().get(db, id=job_id)

    async def get_jobs_by_user(
        self, db: AsyncSession, *, user_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[ProcessingJobDB]:
        """
        Get all processing jobs for a specific user.
        """
        statement = (
            select(self.model)
            .filter(self.model.user_id == user_id)
            .order_by(desc(self.model.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(statement)
        return result.scalars().all()

    async def get_jobs_by_status(
        self, db: AsyncSession, *, status: ProcessingStatus, skip: int = 0, limit: int = 100
    ) -> List[ProcessingJobDB]:
        """
        Get processing jobs by status.
        """
        statement = (
            select(self.model)
            .filter(self.model.status == status.value) # Use enum value for query
            .order_by(desc(self.model.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(statement)
        return result.scalars().all()

    async def update_job_status(
        self, db: AsyncSession, *, job_id: uuid.UUID, status: ProcessingStatus, progress: Optional[float] = None, current_step: Optional[str] = None, error_message: Optional[str] = None
    ) -> Optional[ProcessingJobDB]:
        """
        Update the status and progress of a processing job.
        """
        job = await self.get(db, id=job_id)
        if not job:
            return None

        update_data: Dict[str, Any] = {"status": status.value}
        if progress is not None:
            update_data["progress"] = progress
        if current_step is not None:
            update_data["current_step"] = current_step
        if error_message is not None: # Only set error if provided
            update_data["error_message"] = error_message
        elif status not in [ProcessingStatus.FAILED, ProcessingStatus.CANCELLED]: # Clear error if status is not error-like
            update_data["error_message"] = None

        if status == ProcessingStatus.COMPLETED:
            update_data["progress"] = 100.0

        return await super().update(db, db_obj=job, obj_in=update_data)

    async def update_job_results(
        self, db: AsyncSession, *, job_id: uuid.UUID, intermediate_results: Optional[List[Dict[str, Any]]] = None, final_results: Optional[Dict[str, Any]] = None
    ) -> Optional[ProcessingJobDB]:
        """
        Update the results of a processing job.
        """
        job = await self.get(db, id=job_id)
        if not job:
            return None

        update_data: Dict[str, Any] = {}
        if intermediate_results is not None:
            update_data["intermediate_results"] = intermediate_results
        if final_results is not None:
            update_data["final_results"] = final_results

        if not update_data: # Nothing to update
            return job

        return await super().update(db, db_obj=job, obj_in=update_data)

# Instantiate the CRUD object
processing_job_crud = CRUDProcessingJob(ProcessingJobDB)

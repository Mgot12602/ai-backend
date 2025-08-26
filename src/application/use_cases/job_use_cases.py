class ActiveJobExistsError(Exception):
    """Raised when there's already an active job for the same user session."""
    def __init__(self, existing_job_id: str):
        super().__init__(f"Active job already exists: {existing_job_id}")
        self.existing_job_id = existing_job_id

from typing import Optional, List
from datetime import datetime, timezone
from src.domain.repositories import JobRepository
from src.domain.entities import Job, JobCreate, JobUpdate, JobStatus
from src.domain.services import QueueService, AIService
from src.application.dto import JobCreateRequest, JobResponse
# Removed manual event publishing - using Celery's built-in events instead
import logging


class EnqueueJobError(Exception):
    """Raised when a job cannot be enqueued to the queue backend."""
    pass


class JobUseCases:
    def __init__(
        self, 
        job_repository: JobRepository, 
        queue_service: QueueService,
        ai_service: AIService
    ):
        self.job_repository = job_repository
        self.queue_service = queue_service
        self.ai_service = ai_service
        self.logger = logging.getLogger(__name__)

    async def create_job(self, user_id: str, job_request: JobCreateRequest) -> JobResponse:
        self.logger.debug(
            "[JobUseCases.create_job] user_id=%s job_type=%s payload_keys=%s",
            user_id,
            job_request.job_type,
            list(job_request.input_data.keys()) if job_request.input_data else [],
        )
        # Enforce single active job per session if session_id is provided
        session_id = getattr(job_request, "session_id", None)
        if session_id:
            existing = await self.job_repository.get_active_by_user_session(user_id, session_id)
            if existing:
                self.logger.debug(
                    "[JobUseCases.create_job] active job exists user_id=%s session_id=%s job_id=%s",
                    user_id,
                    session_id,
                    str(existing.id),
                )
                raise ActiveJobExistsError(str(existing.id))
        job_data = JobCreate(
            user_id=user_id,
            session_id=session_id,
            job_type=job_request.job_type,
            input_data=job_request.input_data
        )
        
        job = await self.job_repository.create(job_data)
        self.logger.debug("[JobUseCases.create_job] created job id=%s", str(job.id))

        # Enqueue job for processing - include user_id and session_id for event monitoring
        enqueue_ok = await self.queue_service.enqueue_job(
            str(job.id), 
            {
                "job_id": str(job.id),
                "job_type": job.job_type.value,
                "input_data": job.input_data,
                "user_id": user_id,
                "session_id": session_id
            }
        )
        self.logger.debug("[JobUseCases.create_job] enqueue_ok=%s job_id=%s", enqueue_ok, str(job.id))
        if not enqueue_ok:
            # Mark job as failed and raise a domain error so the API returns a non-201 status
            self.logger.error("[JobUseCases.create_job] failed to enqueue job id=%s", str(job.id))
            await self.job_repository.update(
                str(job.id),
                JobUpdate(
                    status=JobStatus.FAILED,
                    error_message="Failed to enqueue job for processing"
                ),
            )
            raise EnqueueJobError(f"Failed to enqueue job {str(job.id)}")
        
        return self._to_response(job)

    async def get_job_by_id(self, job_id: str) -> Optional[JobResponse]:
        self.logger.debug("[JobUseCases.get_job_by_id] job_id=%s", job_id)
        job = await self.job_repository.get_by_id(job_id)
        return self._to_response(job) if job else None

    async def get_user_jobs(self, user_id: str, skip: int = 0, limit: int = 100) -> List[JobResponse]:
        self.logger.debug("[JobUseCases.get_user_jobs] user_id=%s skip=%s limit=%s", user_id, skip, limit)
        jobs = await self.job_repository.get_by_user_id(user_id, skip, limit)
        return [self._to_response(job) for job in jobs]

    async def get_jobs_by_status(self, status: JobStatus, skip: int = 0, limit: int = 100) -> List[JobResponse]:
        self.logger.debug("[JobUseCases.get_jobs_by_status] status=%s skip=%s limit=%s", status, skip, limit)
        jobs = await self.job_repository.get_by_status(status, skip, limit)
        return [self._to_response(job) for job in jobs]

    async def update_job_status(
        self, 
        job_id: str, 
        status: JobStatus, 
        output_data: Optional[dict] = None,
        artifact_url: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Optional[JobResponse]:
        self.logger.debug(
            "[JobUseCases.update_job_status] job_id=%s status=%s has_output=%s has_artifact=%s has_error=%s",
            job_id,
            status,
            bool(output_data),
            bool(artifact_url),
            bool(error_message),
        )
        update_data = JobUpdate(
            status=status,
            output_data=output_data,
            artifact_url=artifact_url,
            error_message=error_message
        )
        
        if status == JobStatus.PROCESSING:
            update_data.started_at = datetime.now(timezone.utc)
        elif status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            update_data.completed_at = datetime.now(timezone.utc)
        
        job = await self.job_repository.update(job_id, update_data)
        if job:
            self.logger.debug("[JobUseCases.update_job_status] updated job_id=%s new_status=%s", job_id, job.status)
            # Events are now automatically handled by Celery's built-in event system
        return self._to_response(job) if job else None

    async def process_job(self, job_id: str) -> bool:
        """Process a job using AI service"""
        self.logger.debug("[JobUseCases.process_job] start job_id=%s", job_id)
        job = await self.job_repository.get_by_id(job_id)
        if not job:
            self.logger.warning("[JobUseCases.process_job] job not found job_id=%s", job_id)
            return False

        try:
            # Update status to processing
            await self.update_job_status(job_id, JobStatus.PROCESSING)
            
            # Generate AI content
            self.logger.debug("[JobUseCases.process_job] calling AI service job_type=%s", job.job_type)
            result = await self.ai_service.generate(job.job_type, job.input_data)
            self.logger.debug(
                "[JobUseCases.process_job] AI result received job_id=%s keys=%s",
                job_id,
                list(result.keys()) if isinstance(result, dict) else type(result).__name__,
            )
            
            # Update job with results
            await self.update_job_status(
                job_id, 
                JobStatus.COMPLETED,
                output_data=result.get("output_data"),
                artifact_url=result.get("artifact_url")
            )
            
            return True
            
        except Exception as e:
            # Update job with error
            self.logger.exception("[JobUseCases.process_job] error job_id=%s error=%s", job_id, e)
            await self.update_job_status(
                job_id, 
                JobStatus.FAILED,
                error_message=str(e)
            )
            return False

    def _to_response(self, job: Job) -> JobResponse:
        return JobResponse(
            id=str(job.id),
            user_id=job.user_id,
            session_id=getattr(job, "session_id", None),
            job_type=job.job_type,
            status=job.status,
            input_data=job.input_data,
            output_data=job.output_data,
            artifact_url=job.artifact_url,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            completed_at=job.completed_at
        )

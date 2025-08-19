from typing import Optional, List
from datetime import datetime
from src.domain.repositories import JobRepository
from src.domain.entities import Job, JobCreate, JobUpdate, JobStatus
from src.domain.services import QueueService, AIService
from src.application.dto import JobCreateRequest, JobResponse


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

    async def create_job(self, user_id: str, job_request: JobCreateRequest) -> JobResponse:
        job_data = JobCreate(
            user_id=user_id,
            job_type=job_request.job_type,
            input_data=job_request.input_data
        )
        
        job = await self.job_repository.create(job_data)
        
        # Enqueue job for processing
        await self.queue_service.enqueue_job(
            str(job.id), 
            {
                "job_id": str(job.id),
                "job_type": job.job_type,
                "input_data": job.input_data
            }
        )
        
        return self._to_response(job)

    async def get_job_by_id(self, job_id: str) -> Optional[JobResponse]:
        job = await self.job_repository.get_by_id(job_id)
        return self._to_response(job) if job else None

    async def get_user_jobs(self, user_id: str, skip: int = 0, limit: int = 100) -> List[JobResponse]:
        jobs = await self.job_repository.get_by_user_id(user_id, skip, limit)
        return [self._to_response(job) for job in jobs]

    async def get_jobs_by_status(self, status: JobStatus, skip: int = 0, limit: int = 100) -> List[JobResponse]:
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
        update_data = JobUpdate(
            status=status,
            output_data=output_data,
            artifact_url=artifact_url,
            error_message=error_message
        )
        
        if status == JobStatus.PROCESSING:
            update_data.started_at = datetime.utcnow()
        elif status in [JobStatus.COMPLETED, JobStatus.FAILED]:
            update_data.completed_at = datetime.utcnow()
        
        job = await self.job_repository.update(job_id, update_data)
        return self._to_response(job) if job else None

    async def process_job(self, job_id: str) -> bool:
        """Process a job using AI service"""
        job = await self.job_repository.get_by_id(job_id)
        if not job:
            return False

        try:
            # Update status to processing
            await self.update_job_status(job_id, JobStatus.PROCESSING)
            
            # Generate AI content
            result = await self.ai_service.generate(job.job_type, job.input_data)
            
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

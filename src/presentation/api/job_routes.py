from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from src.application.use_cases import JobUseCases
from src.application.dto import JobCreateRequest, JobResponse
from src.infrastructure.repositories import MongoJobRepository
from src.infrastructure.external.fake_ai_service import FakeAIService
from src.infrastructure.queue.celery_queue_service import CeleryQueueService
from src.config.auth import get_current_user

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_job_use_cases() -> JobUseCases:
    job_repository = MongoJobRepository()
    queue_service = CeleryQueueService()
    ai_service = FakeAIService()
    return JobUseCases(job_repository, queue_service, ai_service)


@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_request: JobCreateRequest,
    current_user: dict = Depends(get_current_user),
    use_cases: JobUseCases = Depends(get_job_use_cases)
):
    """Create and enqueue a new AI job"""
    user_id = current_user["user_id"]
    return await use_cases.create_job(user_id, job_request)


@router.get("/", response_model=List[JobResponse])
async def get_user_jobs(
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
    use_cases: JobUseCases = Depends(get_job_use_cases)
):
    """Get current user's jobs"""
    user_id = current_user["user_id"]
    return await use_cases.get_user_jobs(user_id, skip, limit)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: JobUseCases = Depends(get_job_use_cases)
):
    """Get job by ID"""
    job = await use_cases.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    
    # Check if user owns this job
    if job.user_id != current_user["user_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    
    return job


@router.post("/generate", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def generate_ai_content(
    job_request: JobCreateRequest,
    current_user: dict = Depends(get_current_user),
    use_cases: JobUseCases = Depends(get_job_use_cases)
):
    """Generate AI content - alias for create_job"""
    user_id = current_user["user_id"]
    return await use_cases.create_job(user_id, job_request)

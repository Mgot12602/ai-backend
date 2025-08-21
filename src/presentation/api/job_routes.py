from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from dataclasses import dataclass
from src.application.use_cases.job_use_cases import JobUseCases
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


@dataclass
class JobContext:
    user_id: str
    use_cases: JobUseCases


def get_job_context(
    current_user: dict = Depends(get_current_user),
    use_cases: JobUseCases = Depends(get_job_use_cases),
) -> JobContext:
    """Aggregate common dependencies to avoid duplication in handlers."""
    return JobContext(user_id=current_user["user_id"], use_cases=use_cases)

async def get_owned_job(
    job_id: str,
    ctx: JobContext = Depends(get_job_context),
) -> JobResponse:
    """Fetch a job and ensure the current user owns it."""
    job = await ctx.use_cases.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.user_id != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return job

@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_request: JobCreateRequest,
    ctx: JobContext = Depends(get_job_context),
):
    """Create and enqueue a new AI job"""
    return await ctx.use_cases.create_job(ctx.user_id, job_request)


@router.get("/", response_model=List[JobResponse])
async def get_user_jobs(
    skip: int = 0,
    limit: int = 100,
    ctx: JobContext = Depends(get_job_context),
):
    """Get current user's jobs"""
    return await ctx.use_cases.get_user_jobs(ctx.user_id, skip, limit)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job: JobResponse = Depends(get_owned_job),
):
    """Get job by ID"""
    return job


@router.post("/generate", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def generate_ai_content(
    job_request: JobCreateRequest,
    ctx: JobContext = Depends(get_job_context),
):
    """Generate AI content - alias for create_job"""
    return await ctx.use_cases.create_job(ctx.user_id, job_request)

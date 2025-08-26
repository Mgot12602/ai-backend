from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from dataclasses import dataclass
from src.application.use_cases.job_use_cases import JobUseCases, EnqueueJobError, ActiveJobExistsError
from src.application.dto import JobCreateRequest, JobResponse
from src.infrastructure.repositories import MongoJobRepository
from src.infrastructure.external.fake_ai_service import FakeAIService
from src.infrastructure.queue.celery_queue_service import CeleryQueueService
from src.config.auth import get_current_user, security
import logging

router = APIRouter(prefix="/jobs", tags=["jobs"]) 

logger = logging.getLogger(__name__)


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
    ctx = JobContext(user_id=current_user["user_id"], use_cases=use_cases)
    logger.debug("[job_routes.get_job_context] user_id=%s", ctx.user_id)
    return ctx

async def get_owned_job(
    job_id: str,
    ctx: JobContext = Depends(get_job_context),
) -> JobResponse:
    """Fetch a job and ensure the current user owns it."""
    job = await ctx.use_cases.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    """ if job.user_id != ctx.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied") """

    return job

@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_request: JobCreateRequest,
    ctx: JobContext = Depends(get_job_context),
):
    """Create and enqueue a new AI job"""
    logger.debug(
        "[job_routes.create_job] user_id=%s job_type=%s payload_keys=%s",
        ctx.user_id,
        getattr(job_request, "job_type", None),
        list(getattr(job_request, "input_data", {}).keys()) if getattr(job_request, "input_data", None) else [],
    )
    try:
        resp = await ctx.use_cases.create_job(ctx.user_id, job_request)
        logger.debug("[job_routes.create_job] created job_id=%s status=%s", resp.id, resp.status)
        return resp
    except ActiveJobExistsError as e:
        logger.warning("[job_routes.create_job] active job exists user_id=%s session_id=%s job_id=%s", ctx.user_id, getattr(job_request, 'session_id', None), e.existing_job_id)
        # 409 Conflict with info about existing job
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "active_job_exists",
                "existing_job_id": e.existing_job_id,
                "session_id": getattr(job_request, 'session_id', None),
            },
        )
    except EnqueueJobError as e:
        logger.error("[job_routes.create_job] enqueue failed: %s", e)
        # Return Service Unavailable to signal that background processing is down
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


@router.get("/", response_model=List[JobResponse])
async def get_user_jobs(
    skip: int = 0,
    limit: int = 100,
    ctx: JobContext = Depends(get_job_context),
):
    """Get current user's jobs"""
    logger.debug("[job_routes.get_user_jobs] user_id=%s skip=%s limit=%s", ctx.user_id, skip, limit)
    jobs = await ctx.use_cases.get_user_jobs(ctx.user_id, skip, limit)
    logger.debug("[job_routes.get_user_jobs] found=%s", len(jobs))
    return jobs


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job: JobResponse = Depends(get_owned_job),
):
    """Get job by ID"""
    logger.debug("[job_routes.get_job] job_id=%s user_id=%s status=%s", job.id, job.user_id, job.status)
    return job


 

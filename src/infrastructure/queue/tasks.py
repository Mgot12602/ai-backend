from celery import current_app
from celery.exceptions import SoftTimeLimitExceeded
from src.infrastructure.queue.celery_queue_service import celery_app
from src.application.use_cases import JobUseCases
from src.infrastructure.repositories import MongoJobRepository
from src.infrastructure.external.fake_ai_service import FakeAIService
#from src.infrastructure.storage.s3_storage_service import FakeStorageService
from src.infrastructure.queue.celery_queue_service import CeleryQueueService
from src.infrastructure.database.mongodb import MongoDB
from src.domain.entities import JobStatus
import asyncio
import logging
from src.config.settings import settings


@celery_app.task(soft_time_limit=settings.celery_soft_time_limit, time_limit=settings.celery_time_limit)
def process_job(job_id: str, job_data: dict):
    """Process AI job task"""
    try:
        logger = logging.getLogger(__name__)
        logger.info("[tasks.process_job] start job_id=%s keys=%s", job_id, list(job_data.keys()) if isinstance(job_data, dict) else type(job_data).__name__)
        # Run async job processing
        processed_ok = asyncio.run(_process_job_async(job_id, job_data))
        if processed_ok:
            logger.info("[tasks.process_job] completed job_id=%s", job_id)
            return {"status": "completed", "job_id": job_id}
        else:
            logger.warning("[tasks.process_job] processing failed or job not found job_id=%s", job_id)
            return {"status": "failed", "job_id": job_id}
    except SoftTimeLimitExceeded as e:
        logging.warning("[tasks.process_job] soft time limit exceeded job_id=%s limit=%ss", job_id, settings.celery_soft_time_limit)
        # Best-effort mark job as failed due to timeout
        try:
            asyncio.run(_mark_job_failed_async(job_id, f"Timed out after {settings.celery_soft_time_limit}s"))
        except Exception:
            logging.debug("[tasks.process_job] failed to mark job as FAILED on timeout job_id=%s", job_id)
        return {"status": "failed", "job_id": job_id, "error": "soft_time_limit_exceeded"}
    except Exception as e:
        logging.exception("[tasks.process_job] error job_id=%s error=%s", job_id, e)
        return {"status": "failed", "job_id": job_id, "error": str(e)}


async def _process_job_async(job_id: str, job_data: dict):
    """Async job processing logic"""
    # Fresh DB connection per task to avoid event loop reuse issues
    logging.debug(
        "[tasks._process_job_async] connecting MongoDB url=%s db=%s",
        settings.mongodb_url,
        settings.database_name,
    )
    await MongoDB.connect_to_mongo(settings.mongodb_url, settings.database_name)
    try:
        # Initialize services
        job_repository = MongoJobRepository()
        ai_service = FakeAIService()
        #storage_service = FakeStorageService()
        queue_service = CeleryQueueService()
        
        # Initialize use case
        job_use_cases = JobUseCases(job_repository, queue_service, ai_service)

        # Process the job
        logging.debug("[tasks._process_job_async] calling JobUseCases.process_job job_id=%s", job_id)
        return await job_use_cases.process_job(job_id)
    finally:
        await MongoDB.close_mongo_connection()


async def _mark_job_failed_async(job_id: str, message: str):
    """Best-effort failure marker used by timeout handler."""
    await MongoDB.connect_to_mongo(settings.mongodb_url, settings.database_name)
    try:
        job_repository = MongoJobRepository()
        ai_service = FakeAIService()
        queue_service = CeleryQueueService()
        job_use_cases = JobUseCases(job_repository, queue_service, ai_service)
        await job_use_cases.update_job_status(job_id, JobStatus.FAILED, error_message=message)
    finally:
        await MongoDB.close_mongo_connection()

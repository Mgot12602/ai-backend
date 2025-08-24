from celery import current_app
from src.infrastructure.queue.celery_queue_service import celery_app
from src.application.use_cases import JobUseCases
from src.infrastructure.repositories import MongoJobRepository
from src.infrastructure.external.fake_ai_service import FakeAIService
#from src.infrastructure.storage.s3_storage_service import FakeStorageService
from src.infrastructure.queue.celery_queue_service import CeleryQueueService
from src.infrastructure.database.mongodb import MongoDB
import asyncio
import logging
from src.config.settings import settings


@celery_app.task
def process_job(job_id: str, job_data: dict):
    """Process AI job task"""
    try:
        logger = logging.getLogger(__name__)
        logger.info("[tasks.process_job] start job_id=%s keys=%s", job_id, list(job_data.keys()) if isinstance(job_data, dict) else type(job_data).__name__)
        # Run async job processing
        asyncio.run(_process_job_async(job_id, job_data))
        logger.info("[tasks.process_job] completed job_id=%s", job_id)
        return {"status": "completed", "job_id": job_id}
    except Exception as e:
        logging.exception("[tasks.process_job] error job_id=%s error=%s", job_id, e)
        return {"status": "failed", "job_id": job_id, "error": str(e)}


async def _process_job_async(job_id: str, job_data: dict):
    """Async job processing logic"""
    # Initialize database connection if not already done
    if MongoDB.database is None:
        logging.debug(
            "[tasks._process_job_async] connecting to MongoDB url=%s db=%s",
            settings.mongodb_url,
            settings.database_name,
        )
        await MongoDB.connect_to_mongo(settings.mongodb_url, settings.database_name)
    
    # Initialize services
    job_repository = MongoJobRepository()
    ai_service = FakeAIService()
    #storage_service = FakeStorageService()
    queue_service = CeleryQueueService()
    
    # Initialize use case
    job_use_cases = JobUseCases(job_repository, queue_service, ai_service)
    
    # Simulate expensive computation delay (testing)
    logging.debug("[tasks._process_job_async] simulating 5s processing delay job_id=%s", job_id)
    await asyncio.sleep(5)

    # Process the job
    logging.debug("[tasks._process_job_async] calling JobUseCases.process_job job_id=%s", job_id)
    await job_use_cases.process_job(job_id)

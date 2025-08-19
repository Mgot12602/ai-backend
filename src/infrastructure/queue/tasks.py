from celery import current_app
from src.infrastructure.queue.celery_queue_service import celery_app
from src.application.use_cases import JobUseCases
from src.infrastructure.repositories import MongoJobRepository
from src.infrastructure.external.fake_ai_service import FakeAIService
from src.infrastructure.storage.s3_storage_service import FakeStorageService
from src.infrastructure.queue.celery_queue_service import CeleryQueueService
from src.infrastructure.database.mongodb import MongoDB
import asyncio
import os


@celery_app.task
def process_job(job_id: str, job_data: dict):
    """Process AI job task"""
    try:
        # Run async job processing
        asyncio.run(_process_job_async(job_id, job_data))
        return {"status": "completed", "job_id": job_id}
    except Exception as e:
        print(f"Error processing job {job_id}: {str(e)}")
        return {"status": "failed", "job_id": job_id, "error": str(e)}


async def _process_job_async(job_id: str, job_data: dict):
    """Async job processing logic"""
    # Initialize database connection if not already done
    if MongoDB.database is None:
        connection_string = os.getenv('MONGODB_URL', 'mongodb://localhost:27017')
        database_name = os.getenv('DATABASE_NAME', 'ai_backend')
        await MongoDB.connect_to_mongo(connection_string, database_name)
    
    # Initialize services
    job_repository = MongoJobRepository()
    ai_service = FakeAIService()
    storage_service = FakeStorageService()
    queue_service = CeleryQueueService()
    
    # Initialize use case
    job_use_cases = JobUseCases(job_repository, queue_service, ai_service)
    
    # Process the job
    await job_use_cases.process_job(job_id)

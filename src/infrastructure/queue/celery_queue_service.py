from celery import Celery
from typing import Dict, Any
from src.domain.services import QueueService
import os


# Celery configuration
celery_app = Celery(
    'ai_backend',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    include=['src.infrastructure.queue.tasks']
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'src.infrastructure.queue.tasks.process_job': {'queue': 'ai_jobs'},
    }
)


class CeleryQueueService(QueueService):
    def __init__(self):
        self.celery = celery_app

    async def enqueue_job(self, job_id: str, job_data: Dict[str, Any]) -> bool:
        """Add job to processing queue"""
        try:
            from .tasks import process_job
            process_job.delay(job_id, job_data)
            return True
        except Exception as e:
            print(f"Failed to enqueue job {job_id}: {str(e)}")
            return False

    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        try:
            inspect = self.celery.control.inspect()
            active_tasks = inspect.active()
            scheduled_tasks = inspect.scheduled()
            
            return {
                "active_tasks": len(active_tasks.get('celery@worker', [])) if active_tasks else 0,
                "scheduled_tasks": len(scheduled_tasks.get('celery@worker', [])) if scheduled_tasks else 0,
                "workers": list(active_tasks.keys()) if active_tasks else []
            }
        except Exception as e:
            return {
                "error": str(e),
                "active_tasks": 0,
                "scheduled_tasks": 0,
                "workers": []
            }

from celery import Celery
from typing import Dict, Any
from src.domain.services import QueueService
import logging
from src.config.settings import settings


# Celery configuration
celery_app = Celery(
    'ai_backend',
    broker=settings.redis_url,
    backend=settings.redis_url,
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
        self.logger = logging.getLogger(__name__)

    async def enqueue_job(self, job_id: str, job_data: Dict[str, Any]) -> bool:
        """Add job to processing queue"""
        try:
            from .tasks import process_job
            self.logger.debug(
                "[CeleryQueueService.enqueue_job] enqueue job_id=%s keys=%s",
                job_id,
                list(job_data.keys()) if isinstance(job_data, dict) else type(job_data).__name__,
            )
            process_job.delay(job_id, job_data)
            self.logger.debug("[CeleryQueueService.enqueue_job] enqueued job_id=%s", job_id)
            return True
        except Exception as e:
            self.logger.exception("[CeleryQueueService.enqueue_job] failed job_id=%s error=%s", job_id, e)
            return False

    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        try:
            self.logger.debug("[CeleryQueueService.get_queue_status] inspecting workers")
            inspect = self.celery.control.inspect()
            active_tasks = inspect.active()
            scheduled_tasks = inspect.scheduled()
            
            status = {
                "active_tasks": len(active_tasks.get('celery@worker', [])) if active_tasks else 0,
                "scheduled_tasks": len(scheduled_tasks.get('celery@worker', [])) if scheduled_tasks else 0,
                "workers": list(active_tasks.keys()) if active_tasks else []
            }
            self.logger.debug("[CeleryQueueService.get_queue_status] status=%s", status)
            return status
        except Exception as e:
            self.logger.exception("[CeleryQueueService.get_queue_status] error=%s", e)
            return {
                "error": str(e),
                "active_tasks": 0,
                "scheduled_tasks": 0,
                "workers": []
            }

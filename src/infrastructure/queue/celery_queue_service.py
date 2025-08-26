from celery import Celery
from typing import Dict, Any
from src.domain.services import QueueService
import logging
from src.config.settings import settings
from kombu import Queue


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
    # Queue configuration
    task_default_queue=settings.celery_queue_name,
    task_queues=[Queue(settings.celery_queue_name)],
    task_routes={
        'src.infrastructure.queue.tasks.process_job': {'queue': settings.celery_queue_name},
    },
    # Enable events for monitoring (required for our event monitor)
    worker_send_task_events=True,
    task_send_sent_event=True,
    # Worker configuration
    worker_hijack_root_logger=False,
    worker_redirect_stdouts=True,
    worker_redirect_stdouts_level='INFO',
    broker_connection_retry_on_startup=True,
    # Task execution limits
    task_soft_time_limit=settings.celery_soft_time_limit,
    task_time_limit=settings.celery_time_limit,
    # Task execution behavior
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    task_create_missing_queues=True,
    # Publishing reliability
    task_publish_retry=True,
    task_publish_retry_policy={
        'max_retries': 3,
        'interval_start': 0,
        'interval_step': 0.2,
        'interval_max': 1,
    },
    broker_pool_limit=1,
    broker_heartbeat=30,
    broker_heartbeat_checkrate=2,
)


class CeleryQueueService(QueueService):
    def __init__(self):
        self.celery = celery_app
        self.logger = logging.getLogger(__name__)
        try:
            self.logger.debug(
                "[CeleryQueueService.__init__] broker=%s default_queue=%s routes=%s",
                settings.redis_url,
                celery_app.conf.task_default_queue,
                celery_app.conf.task_routes,
            )
        except Exception as _e:
            # Avoid failing init due to logging
            pass

    async def enqueue_job(self, job_id: str, job_data: Dict[str, Any]) -> bool:
        """Add job to processing queue"""
        try:
            from .tasks import process_job
            self.logger.debug(
                "[CeleryQueueService.enqueue_job] enqueue job_id=%s keys=%s",
                job_id,
                list(job_data.keys()) if isinstance(job_data, dict) else type(job_data).__name__,
            )
            # Explicitly route to the configured queue to avoid any default-queue mismatches
            result = process_job.apply_async(
                args=(job_id, job_data),
                queue=settings.celery_queue_name,
                soft_time_limit=settings.celery_soft_time_limit,
                time_limit=settings.celery_time_limit,
            )
            self.logger.info(
                "[CeleryQueueService.enqueue_job] enqueued job_id=%s queue=%s task_id=%s",
                job_id,
                settings.celery_queue_name,
                getattr(result, 'id', None),
            )
            return True
        except Exception as e:
            self.logger.exception("[CeleryQueueService.enqueue_job] failed job_id=%s error=%s", job_id, e)
            return False

    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        try:
            self.logger.debug("[CeleryQueueService.get_queue_status] inspecting workers")
            inspect = self.celery.control.inspect()
            active_tasks = inspect.active() or {}
            scheduled_tasks = inspect.scheduled() or {}
            reserved_tasks = inspect.reserved() or {}
            active_queues = inspect.active_queues() or {}
            stats = inspect.stats() or {}
            
            status = {
                "active_tasks": sum(len(v) for v in active_tasks.values()),
                "scheduled_tasks": sum(len(v) for v in scheduled_tasks.values()),
                "reserved_tasks": sum(len(v) for v in reserved_tasks.values()),
                "workers": list(set(list(active_tasks.keys()) + list(scheduled_tasks.keys()) + list(reserved_tasks.keys()))),
                "queues": {k: [q.get('name') for q in v] for k, v in active_queues.items()},
                "broker": getattr(self.celery.conf, "broker_url", None),
                "default_queue": getattr(self.celery.conf, "task_default_queue", None),
                "queue_routes": self.celery.conf.task_routes,
                "queue_name_used_for_enqueue": settings.celery_queue_name,
                "pool_limit": getattr(self.celery.conf, "broker_pool_limit", None),
                "heartbeat": getattr(self.celery.conf, "broker_heartbeat", None),
                "heartbeat_checkrate": getattr(self.celery.conf, "broker_heartbeat_checkrate", None),
            }
            self.logger.debug("[CeleryQueueService.get_queue_status] status=%s", status)
            return status
        except Exception as e:
            self.logger.exception("[CeleryQueueService.get_queue_status] error=%s", e)
            return {
                "error": str(e),
                "active_tasks": 0,
                "scheduled_tasks": 0,
                "reserved_tasks": 0,
                "workers": []
            }

"""
Simple Job Notifier - Uses Redis pub/sub for worker-to-API communication
"""
import json
import logging
from typing import Optional
import redis

from src.config.settings import settings

logger = logging.getLogger(__name__)

# Channel for job status notifications
JOB_NOTIFICATION_CHANNEL = "job_notifications"


class SimpleJobNotifier:
    """Simple job status notifier that uses Redis pub/sub"""
    
    @staticmethod
    def notify_job_status_sync(
        user_id: str,
        job_id: str,
        status: str,
        session_id: Optional[str] = None,
        message: Optional[str] = None
    ) -> None:
        """Synchronous notification for use in Celery tasks"""
        try:
            logger.info("[SimpleJobNotifier] notifying: user_id=%s, job_id=%s, status=%s, session_id=%s", 
                       user_id, job_id, status, session_id)
            
            # Create Redis client
            r = redis.from_url(settings.redis_url, decode_responses=True)
            
            # Prepare notification payload
            payload = {
                "type": "job_status_update",
                "user_id": user_id,
                "job_id": job_id,
                "status": status,
                "session_id": session_id,
                "message": message
            }
            
            # Publish to Redis channel
            r.publish(JOB_NOTIFICATION_CHANNEL, json.dumps(payload))
            logger.info("[SimpleJobNotifier] notification published to Redis")
            
        except Exception:
            logger.exception("[SimpleJobNotifier] failed to notify job status sync")

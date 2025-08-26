"""
Redis Notification Subscriber - Listens for job notifications and forwards to WebSockets
"""
import asyncio
import json
import logging
from typing import Optional
from redis.asyncio import Redis

from src.config.settings import settings
from src.presentation.websocket.websocket_routes import notify_job_status_update
from src.infrastructure.events.simple_job_notifier import JOB_NOTIFICATION_CHANNEL

logger = logging.getLogger(__name__)


class RedisNotificationSubscriber:
    """Subscribes to Redis job notifications and forwards to WebSockets"""
    
    def __init__(self):
        self._redis: Optional[Redis] = None
        self._task: Optional[asyncio.Task] = None
        self._stopping = asyncio.Event()

    def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(settings.redis_url, decode_responses=True)
        return self._redis

    async def start(self) -> None:
        """Start listening for Redis notifications"""
        if self._task and not self._task.done():
            return
        self._stopping.clear()
        self._task = asyncio.create_task(self._run(), name="redis_notification_subscriber")
        logger.info("[RedisNotificationSubscriber] started")

    async def stop(self) -> None:
        """Stop listening for Redis notifications"""
        self._stopping.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._redis is not None:
            try:
                await self._redis.close()
            except Exception:
                pass
            self._redis = None
        logger.info("[RedisNotificationSubscriber] stopped")

    async def _run(self) -> None:
        """Main subscription loop"""
        r = self._get_redis()
        pubsub = r.pubsub()
        await pubsub.subscribe(JOB_NOTIFICATION_CHANNEL)
        logger.info("[RedisNotificationSubscriber] subscribed to channel=%s", JOB_NOTIFICATION_CHANNEL)
        
        try:
            async for msg in pubsub.listen():
                if self._stopping.is_set():
                    break
                if not isinstance(msg, dict):
                    continue
                if msg.get("type") != "message":
                    continue
                    
                data = msg.get("data")
                if not data:
                    continue
                    
                try:
                    payload = json.loads(data)
                except Exception:
                    logger.exception("[RedisNotificationSubscriber] invalid payload: %r", data)
                    continue
                    
                if payload.get("type") != "job_status_update":
                    continue
                    
                user_id = payload.get("user_id")
                job_id = payload.get("job_id")
                status = payload.get("status")
                session_id = payload.get("session_id")
                message = payload.get("message")
                
                if not (user_id and job_id and status):
                    logger.debug("[RedisNotificationSubscriber] missing fields in payload=%s", payload)
                    continue
                    
                try:
                    await notify_job_status_update(
                        user_id=user_id,
                        job_id=job_id,
                        status=status,
                        message=message,
                        session_id=session_id,
                    )
                    logger.info("[RedisNotificationSubscriber] forwarded notification: user_id=%s, job_id=%s, status=%s", 
                               user_id, job_id, status)
                except Exception:
                    logger.exception(
                        "[RedisNotificationSubscriber] notify failed user_id=%s job_id=%s status=%s",
                        user_id, job_id, status,
                    )
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("[RedisNotificationSubscriber] subscriber error")
        finally:
            try:
                await pubsub.unsubscribe(JOB_NOTIFICATION_CHANNEL)
                await pubsub.close()
            except Exception:
                pass

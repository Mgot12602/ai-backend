from __future__ import annotations

import json
import logging
from typing import Optional
import asyncio

from redis.asyncio import Redis
from src.config.settings import settings

# Channel used for job status update events across processes
JOB_STATUS_CHANNEL = "job_status_updates"

_logger = logging.getLogger(__name__)

_redis_client: Optional[Redis] = None
_redis_loop_id: Optional[int] = None


def _get_redis() -> Redis:
    """Return a Redis client bound to the current running event loop.
    We avoid reusing a client created on a different loop to prevent
    'Task ... got Future attached to a different loop' errors.
    """
    global _redis_client, _redis_loop_id
    loop = asyncio.get_running_loop()
    current_loop_id = id(loop)
    if _redis_client is None or _redis_loop_id != current_loop_id:
        # Create a new client bound to this loop. We intentionally do not
        # attempt to close an old client here to keep this helper sync-only.
        # Old connections (if any) will be GC'ed or explicitly closed on failure/retry paths.
        _redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
        _redis_loop_id = current_loop_id
    return _redis_client


async def publish_job_status_event(
    *,
    user_id: str,
    job_id: str,
    status: str,
    session_id: Optional[str] = None,
    message: Optional[str] = None,
) -> None:
    """Publish a job status update event to Redis so the API process can fan out via WebSocket.

    This is safe to call from both API and worker processes.
    """
    payload = {
        "type": "job_status_update",
        "user_id": user_id,
        "job_id": job_id,
        "status": status,
        "session_id": session_id,
        "message": message,
    }
    try:
        r = _get_redis()
        await r.publish(JOB_STATUS_CHANNEL, json.dumps(payload))
        _logger.debug("[job_events.publish] published channel=%s job_id=%s status=%s", JOB_STATUS_CHANNEL, job_id, status)
    except Exception:
        # On event loop mismatch or transient connection errors, rebuild client and retry once
        _logger.exception("[job_events.publish] failed job_id=%s status=%s", job_id, status)
        try:
            # Force a new client bound to current loop
            global _redis_client, _redis_loop_id
            old_client = _redis_client
            _redis_client = None
            _redis_loop_id = None
            # Best-effort close of previous client if it exists
            if old_client is not None:
                try:
                    await old_client.aclose()
                except Exception:
                    pass
            r = _get_redis()
            await r.publish(JOB_STATUS_CHANNEL, json.dumps(payload))
            _logger.debug("[job_events.publish] published (retry) channel=%s job_id=%s status=%s", JOB_STATUS_CHANNEL, job_id, status)
        except Exception:
            _logger.exception("[job_events.publish] retry failed job_id=%s status=%s", job_id, status)

#!/usr/bin/env python3
"""
Celery worker script for processing AI jobs
"""
import os
import sys
import asyncio
from src.infrastructure.queue.celery_queue_service import celery_app
from src.infrastructure.database.mongodb import MongoDB
from src.config.settings import settings
import logging

# Add src to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))


async def init_database():
    """Initialize database connection for worker"""
    await MongoDB.ensure_connection(settings.mongodb_url, settings.database_name)


if __name__ == '__main__':
    # Configure logging
    if settings.debug:
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
        logging.debug("[celery_worker] Debug logging configured")

    # Initialize database connection
    asyncio.run(init_database())

    # Prepare Celery worker argv (no explicit -Q; use app config)
    argv = [
        "worker",
        "-l", "INFO" if not settings.debug else "DEBUG",
        "--concurrency", os.getenv("CELERY_CONCURRENCY", "1"),
        # Explicitly bind worker to the configured queue
        "-Q", getattr(celery_app.conf, "task_default_queue", settings.celery_queue_name),
        # Fair scheduling across queues (when multiple)
        "-O", "fair",
    ]
    try:
        configured_queues = [q.name for q in (celery_app.conf.task_queues or [])]
    except Exception:
        configured_queues = []
    logging.info(
        "[celery_worker] Starting Celery worker argv=%s default_queue=%s queues=%s broker=%s",
        argv,
        getattr(celery_app.conf, "task_default_queue", None),
        configured_queues,
        getattr(celery_app.conf, "broker_url", None),
    )
    # Use Celery's Python API entrypoint (no 'celery' program name in argv)
    celery_app.worker_main(argv)

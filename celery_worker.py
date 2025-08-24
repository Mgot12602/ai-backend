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
    await MongoDB.connect_to_mongo(settings.mongodb_url, settings.database_name)


if __name__ == '__main__':
    # Configure logging
    if settings.debug:
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
        logging.debug("[celery_worker] Debug logging configured")

    # Initialize database connection
    asyncio.run(init_database())

    # Prepare Celery worker argv and start
    argv = [
        "celery",
        "-A", "src.infrastructure.queue.celery_queue_service",
        "worker",
        "-Q", "ai_jobs",
        "-l", "INFO" if not settings.debug else "DEBUG",
        "--concurrency", os.getenv("CELERY_CONCURRENCY", "1"),
    ]
    logging.info("[celery_worker] Starting Celery worker with argv=%s", argv)
    sys.argv = argv
    celery_app.start()

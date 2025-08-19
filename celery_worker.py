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

# Add src to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))


async def init_database():
    """Initialize database connection for worker"""
    await MongoDB.connect_to_mongo(settings.mongodb_url, settings.database_name)


if __name__ == '__main__':
    # Initialize database connection
    asyncio.run(init_database())
    
    # Start Celery worker
    celery_app.start()

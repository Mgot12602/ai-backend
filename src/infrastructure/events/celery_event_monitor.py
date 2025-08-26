"""
Celery Event Monitor - Uses Celery's built-in event system instead of manual Redis pub/sub
"""
import asyncio
import json
import logging
from typing import Optional
from celery import Celery
from celery.events.state import State

from src.config.settings import settings
from src.presentation.websocket.websocket_routes import notify_job_status_update

logger = logging.getLogger(__name__)


class CeleryEventMonitor:
    """Monitor Celery events and forward job status updates to WebSockets"""
    
    def __init__(self, celery_app: Celery):
        self.celery_app = celery_app
        self._task: Optional[asyncio.Task] = None
        self._stopping = asyncio.Event()
        self.state = State()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def start(self) -> None:
        """Start monitoring Celery events"""
        if self._task and not self._task.done():
            return
        self._stopping.clear()
        self._loop = asyncio.get_event_loop()
        self._task = asyncio.create_task(self._run(), name="celery_event_monitor")
        logger.info("[CeleryEventMonitor] started")

    async def stop(self) -> None:
        """Stop monitoring Celery events"""
        self._stopping.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[CeleryEventMonitor] stopped")

    async def _run(self) -> None:
        """Main event monitoring loop - simplified approach using asyncio"""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        def _sync_event_capture():
            """Synchronous event capture that runs in thread pool"""
            try:
                logger.info("[CeleryEventMonitor] starting event capture thread")
                with self.celery_app.connection() as connection:
                    recv = self.celery_app.events.Receiver(connection, handlers={
                        'task-started': self._handle_task_started,
                        'task-succeeded': self._handle_task_succeeded,
                        'task-failed': self._handle_task_failed,
                        'task-retried': self._handle_task_retried,
                        '*': self.state.event,  # Update state for all events
                    })
                    
                    logger.info("[CeleryEventMonitor] receiver created, starting capture")
                    recv.capture(limit=None, timeout=None, wakeup=True)
                    
            except Exception:
                logger.exception("[CeleryEventMonitor] event monitoring error")
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as executor:
            try:
                await loop.run_in_executor(executor, _sync_event_capture)
            except asyncio.CancelledError:
                logger.info("[CeleryEventMonitor] event capture cancelled")
                raise

    def _handle_task_started(self, event):
        """Handle task-started event"""
        logger.info("[CeleryEventMonitor] task-started event received: %s", event.get('uuid'))
        self.state.event(event)
        task = self.state.tasks.get(event['uuid'])
        if task:
            logger.info("[CeleryEventMonitor] task found: name=%s, args=%s", task.name, task.args)
            if self._is_job_task(task):
                logger.info("[CeleryEventMonitor] processing job task started")
                # Schedule the coroutine in the main event loop
                if self._loop:
                    asyncio.run_coroutine_threadsafe(
                        self._notify_job_status(task, 'PROCESSING'),
                        self._loop
                    )
            else:
                logger.info("[CeleryEventMonitor] not a job task: %s", task.name)
        else:
            logger.warning("[CeleryEventMonitor] task not found in state for uuid=%s", event.get('uuid'))

    def _handle_task_succeeded(self, event):
        """Handle task-succeeded event"""
        logger.info("[CeleryEventMonitor] task-succeeded event received: %s", event.get('uuid'))
        self.state.event(event)
        task = self.state.tasks.get(event['uuid'])
        if task and self._is_job_task(task):
            logger.info("[CeleryEventMonitor] processing job task succeeded")
            if self._loop:
                asyncio.run_coroutine_threadsafe(
                    self._notify_job_status(task, 'COMPLETED'),
                    self._loop
                )
        elif task:
            logger.info("[CeleryEventMonitor] not a job task succeeded: %s", task.name)

    def _handle_task_failed(self, event):
        """Handle task-failed event"""
        logger.info("[CeleryEventMonitor] task-failed event received: %s", event.get('uuid'))
        self.state.event(event)
        task = self.state.tasks.get(event['uuid'])
        if task and self._is_job_task(task):
            error_msg = event.get('exception', 'Task failed')
            if self._loop:
                asyncio.run_coroutine_threadsafe(
                    self._notify_job_status(task, 'FAILED', error_msg),
                    self._loop
                )

    def _handle_task_retried(self, event):
        """Handle task-retried event"""
        logger.info("[CeleryEventMonitor] task-retried event received: %s", event.get('uuid'))
        self.state.event(event)
        task = self.state.tasks.get(event['uuid'])
        if task and self._is_job_task(task):
            retry_msg = f"Retrying: {event.get('exception', 'Unknown error')}"
            if self._loop:
                asyncio.run_coroutine_threadsafe(
                    self._notify_job_status(task, 'PENDING', retry_msg),
                    self._loop
                )

    def _is_job_task(self, task) -> bool:
        """Check if this is a job processing task"""
        return task.name == 'src.infrastructure.queue.tasks.process_job'

    async def _notify_job_status(self, task, status: str, message: str = None):
        """Extract job info from task and notify via WebSocket"""
        try:
            logger.info("[CeleryEventMonitor] _notify_job_status called: status=%s, task.args=%s", status, task.args)
            
            # Extract job_id and user info from task args
            if not task.args or len(task.args) < 2:
                logger.warning("[CeleryEventMonitor] insufficient task args: %s", task.args)
                return
                
            job_id = task.args[0]
            job_data = task.args[1]
            
            logger.info("[CeleryEventMonitor] extracted job_id=%s, job_data=%s", job_id, job_data)
            
            # Get user_id and session_id from job_data
            user_id = job_data.get('user_id')
            session_id = job_data.get('session_id')
            
            if not user_id:
                logger.warning("[CeleryEventMonitor] no user_id in task args for job_id=%s", job_id)
                return
                
            logger.info("[CeleryEventMonitor] notifying WebSocket: user_id=%s, job_id=%s, status=%s, session_id=%s", 
                       user_id, job_id, status, session_id)
                
            await notify_job_status_update(
                user_id=user_id,
                job_id=job_id,
                status=status,
                message=message,
                session_id=session_id
            )
            
            logger.info("[CeleryEventMonitor] WebSocket notification sent successfully")
            
        except Exception:
            logger.exception("[CeleryEventMonitor] failed to notify job status")

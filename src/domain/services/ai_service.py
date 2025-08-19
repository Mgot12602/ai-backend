from abc import ABC, abstractmethod
from typing import Dict, Any
from ..entities import JobType


class AIService(ABC):
    @abstractmethod
    async def generate(self, job_type: JobType, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI content based on job type and input data"""
        pass


class StorageService(ABC):
    @abstractmethod
    async def upload_artifact(self, file_content: bytes, file_name: str, content_type: str) -> str:
        """Upload artifact to storage and return URL"""
        pass

    @abstractmethod
    async def delete_artifact(self, artifact_url: str) -> bool:
        """Delete artifact from storage"""
        pass


class QueueService(ABC):
    @abstractmethod
    async def enqueue_job(self, job_id: str, job_data: Dict[str, Any]) -> bool:
        """Add job to processing queue"""
        pass

    @abstractmethod
    async def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        pass

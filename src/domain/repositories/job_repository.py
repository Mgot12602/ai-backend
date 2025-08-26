from abc import ABC, abstractmethod
from typing import Optional, List
from ..entities import Job, JobCreate, JobUpdate, JobStatus


class JobRepository(ABC):
    @abstractmethod
    async def create(self, job_data: JobCreate) -> Job:
        pass

    @abstractmethod
    async def get_by_id(self, job_id: str) -> Optional[Job]:
        pass

    @abstractmethod
    async def get_by_user_id(self, user_id: str, skip: int = 0, limit: int = 100) -> List[Job]:
        pass

    @abstractmethod
    async def get_active_by_user_session(self, user_id: str, session_id: str) -> Optional[Job]:
        """Return the most recent active (pending/processing) job for a user session if any."""
        pass

    @abstractmethod
    async def get_by_status(self, status: JobStatus, skip: int = 0, limit: int = 100) -> List[Job]:
        pass

    @abstractmethod
    async def update(self, job_id: str, job_data: JobUpdate) -> Optional[Job]:
        pass

    @abstractmethod
    async def delete(self, job_id: str) -> bool:
        pass

    @abstractmethod
    async def list_jobs(self, skip: int = 0, limit: int = 100) -> List[Job]:
        pass

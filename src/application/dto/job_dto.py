from typing import Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
from src.domain.entities import JobType, JobStatus


class JobCreateRequest(BaseModel):
    session_id: str | None = None
    job_type: JobType
    input_data: Dict[str, Any]


class JobResponse(BaseModel):
    id: str
    user_id: str
    session_id: str | None = None
    job_type: JobType
    status: JobStatus
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    artifact_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class JobStatusUpdate(BaseModel):
    job_id: str
    status: JobStatus
    session_id: str | None = None
    message: Optional[str] = None
    progress: Optional[int] = None

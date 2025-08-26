from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from bson import ObjectId
from .user import PyObjectId


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobType(str, Enum):
    AUDIO_GENERATION = "audio_generation"
    TEXT_GENERATION = "text_generation"
    IMAGE_GENERATION = "image_generation"


class Job(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: str = Field(..., description="User ID who created the job")
    session_id: Optional[str] = Field(None, description="Client session identifier")
    job_type: JobType = Field(..., description="Type of AI job")
    status: JobStatus = Field(default=JobStatus.PENDING)
    input_data: Dict[str, Any] = Field(..., description="Input parameters for the job")
    output_data: Optional[Dict[str, Any]] = Field(None, description="Job results")
    artifact_url: Optional[str] = Field(None, description="URL to generated artifact")
    error_message: Optional[str] = Field(None, description="Error message if job failed")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(None)
    completed_at: Optional[datetime] = Field(None)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class JobCreate(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    job_type: JobType
    input_data: Dict[str, Any]


class JobUpdate(BaseModel):
    status: Optional[JobStatus] = None
    output_data: Optional[Dict[str, Any]] = None
    artifact_url: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

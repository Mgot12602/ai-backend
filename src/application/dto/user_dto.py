from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class UserResponse(BaseModel):
    id: str
    clerk_id: str
    email: str
    name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool


class UserCreateRequest(BaseModel):
    clerk_id: str
    email: str
    name: Optional[str] = None


class UserUpdateRequest(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic_core import core_schema
from bson import ObjectId


class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler: GetCoreSchemaHandler):
        """Pydantic v2 core schema for validating ObjectId from str or ObjectId."""
        def validate_objid(v):
            if isinstance(v, ObjectId):
                return v
            if ObjectId.is_valid(v):
                return ObjectId(v)
            raise ValueError("Invalid objectid")

        return core_schema.no_info_after_validator_function(
            validate_objid,
            core_schema.union_schema([
                core_schema.is_instance_schema(ObjectId),
                core_schema.str_schema(),
            ]),
        )

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema_obj, handler: GetJsonSchemaHandler):
        json_schema = handler(core_schema_obj)
        json_schema.update(type="string")
        return json_schema


class User(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    clerk_id: str = Field(..., description="Clerk user ID")
    email: str = Field(..., description="User email")
    name: Optional[str] = Field(None, description="User full name")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class UserCreate(BaseModel):
    clerk_id: str
    email: str
    name: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None

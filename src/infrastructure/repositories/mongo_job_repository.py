from typing import Optional, List
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.domain.repositories import JobRepository
from src.domain.entities import Job, JobCreate, JobUpdate, JobStatus
from src.infrastructure.database.mongodb import MongoDB


class MongoJobRepository(JobRepository):
    def __init__(self):
        self.database = MongoDB.get_database()
        self.collection = self.database.jobs

    async def create(self, job_data: JobCreate) -> Job:
        job_dict = job_data.dict()
        job_dict["status"] = JobStatus.PENDING
        job_dict["created_at"] = datetime.utcnow()
        job_dict["updated_at"] = datetime.utcnow()
        
        result = await self.collection.insert_one(job_dict)
        job_dict["_id"] = result.inserted_id
        
        return Job(**job_dict)

    async def get_by_id(self, job_id: str) -> Optional[Job]:
        from bson import ObjectId
        try:
            job_doc = await self.collection.find_one({"_id": ObjectId(job_id)})
            return Job(**job_doc) if job_doc else None
        except:
            return None

    async def get_by_user_id(self, user_id: str, skip: int = 0, limit: int = 100) -> List[Job]:
        cursor = self.collection.find({"user_id": user_id}).skip(skip).limit(limit).sort("created_at", -1)
        jobs = []
        async for job_doc in cursor:
            jobs.append(Job(**job_doc))
        return jobs

    async def get_by_status(self, status: JobStatus, skip: int = 0, limit: int = 100) -> List[Job]:
        cursor = self.collection.find({"status": status}).skip(skip).limit(limit).sort("created_at", -1)
        jobs = []
        async for job_doc in cursor:
            jobs.append(Job(**job_doc))
        return jobs

    async def update(self, job_id: str, job_data: JobUpdate) -> Optional[Job]:
        from bson import ObjectId
        try:
            update_dict = {k: v for k, v in job_data.dict().items() if v is not None}
            update_dict["updated_at"] = datetime.utcnow()
            
            result = await self.collection.update_one(
                {"_id": ObjectId(job_id)},
                {"$set": update_dict}
            )
            
            if result.modified_count:
                return await self.get_by_id(job_id)
            return None
        except:
            return None

    async def delete(self, job_id: str) -> bool:
        from bson import ObjectId
        try:
            result = await self.collection.delete_one({"_id": ObjectId(job_id)})
            return result.deleted_count > 0
        except:
            return False

    async def list_jobs(self, skip: int = 0, limit: int = 100) -> List[Job]:
        cursor = self.collection.find().skip(skip).limit(limit).sort("created_at", -1)
        jobs = []
        async for job_doc in cursor:
            jobs.append(Job(**job_doc))
        return jobs

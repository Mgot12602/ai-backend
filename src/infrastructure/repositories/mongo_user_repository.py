from typing import Optional, List
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.domain.repositories import UserRepository
from src.domain.entities import User, UserCreate, UserUpdate
from src.infrastructure.database.mongodb import MongoDB


class MongoUserRepository(UserRepository):
    def __init__(self):
        self.database = MongoDB.get_database()
        self.collection = self.database.users

    async def create(self, user_data: UserCreate) -> User:
        user_dict = user_data.dict()
        user_dict["created_at"] = datetime.now(timezone.utc)
        user_dict["updated_at"] = datetime.now(timezone.utc)
        user_dict["is_active"] = True
        
        result = await self.collection.insert_one(user_dict)
        user_dict["_id"] = result.inserted_id
        
        return User(**user_dict)

    async def get_by_id(self, user_id: str) -> Optional[User]:
        from bson import ObjectId
        try:
            user_doc = await self.collection.find_one({"_id": ObjectId(user_id)})
            return User(**user_doc) if user_doc else None
        except:
            return None

    async def get_by_clerk_id(self, clerk_id: str) -> Optional[User]:
        user_doc = await self.collection.find_one({"clerk_id": clerk_id})
        return User(**user_doc) if user_doc else None

    async def get_by_email(self, email: str) -> Optional[User]:
        user_doc = await self.collection.find_one({"email": email})
        return User(**user_doc) if user_doc else None

    async def update(self, user_id: str, user_data: UserUpdate) -> Optional[User]:
        from bson import ObjectId
        try:
            update_dict = {k: v for k, v in user_data.dict().items() if v is not None}
            update_dict["updated_at"] = datetime.now(timezone.utc)
            
            result = await self.collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_dict}
            )
            
            if result.modified_count:
                return await self.get_by_id(user_id)
            return None
        except:
            return None

    async def delete(self, user_id: str) -> bool:
        from bson import ObjectId
        try:
            result = await self.collection.delete_one({"_id": ObjectId(user_id)})
            return result.deleted_count > 0
        except:
            return False

    async def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        cursor = self.collection.find().skip(skip).limit(limit)
        users = []
        async for user_doc in cursor:
            users.append(User(**user_doc))
        return users

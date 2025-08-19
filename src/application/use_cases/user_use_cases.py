from typing import Optional, List
from src.domain.repositories import UserRepository
from src.domain.entities import User, UserCreate, UserUpdate
from src.application.dto import UserResponse, UserCreateRequest, UserUpdateRequest


class UserUseCases:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def create_user(self, user_request: UserCreateRequest) -> UserResponse:
        # Check if user already exists
        existing_user = await self.user_repository.get_by_clerk_id(user_request.clerk_id)
        if existing_user:
            raise ValueError("User with this Clerk ID already exists")

        user_data = UserCreate(
            clerk_id=user_request.clerk_id,
            email=user_request.email,
            name=user_request.name
        )
        
        user = await self.user_repository.create(user_data)
        return self._to_response(user)

    async def get_user_by_clerk_id(self, clerk_id: str) -> Optional[UserResponse]:
        user = await self.user_repository.get_by_clerk_id(clerk_id)
        return self._to_response(user) if user else None

    async def get_user_by_id(self, user_id: str) -> Optional[UserResponse]:
        user = await self.user_repository.get_by_id(user_id)
        return self._to_response(user) if user else None

    async def update_user(self, user_id: str, user_request: UserUpdateRequest) -> Optional[UserResponse]:
        user_data = UserUpdate(
            email=user_request.email,
            name=user_request.name,
            is_active=user_request.is_active
        )
        
        user = await self.user_repository.update(user_id, user_data)
        return self._to_response(user) if user else None

    async def list_users(self, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        users = await self.user_repository.list_users(skip, limit)
        return [self._to_response(user) for user in users]

    def _to_response(self, user: User) -> UserResponse:
        return UserResponse(
            id=str(user.id),
            clerk_id=user.clerk_id,
            email=user.email,
            name=user.name,
            created_at=user.created_at,
            updated_at=user.updated_at,
            is_active=user.is_active
        )

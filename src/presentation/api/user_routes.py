from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from src.application.use_cases import UserUseCases
from src.application.dto import UserResponse, UserCreateRequest, UserUpdateRequest
from src.infrastructure.repositories import MongoUserRepository
from src.config.auth import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


def get_user_use_cases() -> UserUseCases:
    user_repository = MongoUserRepository()
    return UserUseCases(user_repository)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_request: UserCreateRequest,
    use_cases: UserUseCases = Depends(get_user_use_cases)
):
    """Create a new user"""
    try:
        return await use_cases.create_user(user_request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user),
    use_cases: UserUseCases = Depends(get_user_use_cases)
):
    """Get current user profile"""
    user = await use_cases.get_user_by_clerk_id(current_user["user_id"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: dict = Depends(get_current_user),
    use_cases: UserUseCases = Depends(get_user_use_cases)
):
    """Get user by ID"""
    user = await use_cases.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_request: UserUpdateRequest,
    current_user: dict = Depends(get_current_user),
    use_cases: UserUseCases = Depends(get_user_use_cases)
):
    """Update user"""
    user = await use_cases.update_user(user_id, user_request)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
    use_cases: UserUseCases = Depends(get_user_use_cases)
):
    """List users"""
    return await use_cases.list_users(skip, limit)

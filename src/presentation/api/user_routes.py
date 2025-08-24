from fastapi import APIRouter, Depends, HTTPException, Security, status, Response
from typing import List
from fastapi.security import HTTPAuthorizationCredentials
import logging
from src.application.use_cases import UserUseCases
from src.application.dto import UserResponse, UserCreateRequest, UserUpdateRequest
from src.infrastructure.repositories import MongoUserRepository
from src.config.auth import get_current_user, security

router = APIRouter(prefix="/users", tags=["users"]) 
logger = logging.getLogger(__name__)


def get_user_use_cases() -> UserUseCases:
    user_repository = MongoUserRepository()
    return UserUseCases(user_repository)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_request: UserCreateRequest,
    response: Response,
    current_user: dict = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    use_cases: UserUseCases = Depends(get_user_use_cases)
):
    """Create a new user.
    - Requires a valid Clerk token.
    - Derives clerk_id from the validated token, ignoring client-provided clerk_id.
    """
    logger.info("[POST /users] Attempting user creation")
    logger.debug(
        "Create user request received | token_present=%s",
        bool(credentials and credentials.credentials),
    )

    # Derive clerk_id from token claims; do not trust client input for clerk_id
    derived_request = UserCreateRequest(
        clerk_id=current_user.get("user_id"),
        email=user_request.email,
        name=user_request.name,
    )

    # Idempotent behavior: if the user already exists, return it with 200 OK
    existing = await use_cases.get_user_by_clerk_id(derived_request.clerk_id)
    if existing:
        logger.info("User already exists | clerk_id=%s", derived_request.clerk_id)
        response.status_code = status.HTTP_200_OK
        return existing

    try:
        created = await use_cases.create_user(derived_request)
        logger.info("User created successfully | clerk_id=%s", created.clerk_id)
        response.status_code = status.HTTP_201_CREATED
        return created
    except ValueError as e:
        msg = str(e)
        logger.warning("User creation failed: %s", msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


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

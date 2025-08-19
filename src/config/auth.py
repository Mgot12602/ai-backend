from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Optional
import httpx
from .settings import settings


security = HTTPBearer()


class ClerkAuth:
    def __init__(self):
        self.clerk_secret_key = settings.clerk_secret_key
        self.clerk_api_url = "https://api.clerk.dev/v1"

    async def verify_clerk_token(self, token: str) -> dict:
        """Verify Clerk JWT token"""
        try:
            # For development, we'll use a simple verification
            # In production, you should verify against Clerk's public keys
            headers = {
                "Authorization": f"Bearer {self.clerk_secret_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.clerk_api_url}/sessions/verify",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid authentication token"
                    )
        except Exception as e:
            # For development, we'll create a mock verification
            # This should be replaced with proper Clerk verification
            if token.startswith("clerk_"):
                return {
                    "user_id": "user_mock_123",
                    "email": "test@example.com",
                    "name": "Test User"
                }
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )


clerk_auth = ClerkAuth()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get current user from Clerk token"""
    try:
        token = credentials.credentials
        user_data = await clerk_auth.verify_clerk_token(token)
        return user_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[dict]:
    """Get current user from Clerk token (optional)"""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except:
        return None

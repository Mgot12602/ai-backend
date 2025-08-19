from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    mongodb_url: str = "mongodb://localhost:27017"
    database_name: str = "ai_backend"
    
    # Redis/Queue
    redis_url: str = "redis://localhost:6379/0"
    
    # Storage
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    s3_bucket_name: str = "ai-backend-artifacts"
    s3_region: str = "us-east-1"
    s3_endpoint_url: Optional[str] = None  # For MinIO
    
    # Authentication
    clerk_secret_key: str = ""
    jwt_secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True
    
    # WebSocket
    websocket_host: str = "0.0.0.0"
    websocket_port: int = 8001
    
    class Config:
        env_file = ".env"


settings = Settings()

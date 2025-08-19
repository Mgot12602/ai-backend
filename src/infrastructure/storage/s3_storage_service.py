import boto3
from botocore.exceptions import ClientError
from typing import Optional
from src.domain.services import StorageService
import uuid
import os


class S3StorageService(StorageService):
    def __init__(
        self,
        bucket_name: str,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1",
        endpoint_url: Optional[str] = None  # For MinIO or other S3-compatible services
    ):
        self.bucket_name = bucket_name
        
        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id or os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=aws_secret_access_key or os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=region_name,
            endpoint_url=endpoint_url
        )
        
        # Create bucket if it doesn't exist
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                try:
                    self.s3_client.create_bucket(Bucket=self.bucket_name)
                except ClientError:
                    pass  # Bucket might have been created by another process

    async def upload_artifact(self, file_content: bytes, file_name: str, content_type: str) -> str:
        """Upload artifact to S3 and return URL"""
        try:
            # Generate unique key
            file_extension = file_name.split('.')[-1] if '.' in file_name else ''
            unique_key = f"artifacts/{uuid.uuid4()}.{file_extension}"
            
            # Upload file
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=unique_key,
                Body=file_content,
                ContentType=content_type
            )
            
            # Generate URL
            url = f"https://{self.bucket_name}.s3.amazonaws.com/{unique_key}"
            return url
            
        except ClientError as e:
            raise Exception(f"Failed to upload artifact: {str(e)}")

    async def delete_artifact(self, artifact_url: str) -> bool:
        """Delete artifact from S3"""
        try:
            # Extract key from URL
            key = artifact_url.split(f"{self.bucket_name}.s3.amazonaws.com/")[-1]
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
            
        except ClientError:
            return False


class FakeStorageService(StorageService):
    """Fake storage service for development"""
    
    async def upload_artifact(self, file_content: bytes, file_name: str, content_type: str) -> str:
        """Simulate artifact upload"""
        file_id = str(uuid.uuid4())
        return f"https://fake-storage.com/artifacts/{file_id}/{file_name}"
    
    async def delete_artifact(self, artifact_url: str) -> bool:
        """Simulate artifact deletion"""
        return True

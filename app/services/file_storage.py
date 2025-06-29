import os
import boto3
import io
from typing import BinaryIO, Optional, List, Dict, Any
from botocore.exceptions import ClientError
from app.core.config import settings
import structlog

logger = structlog.get_logger()

class FileStorageService:
    """Service for handling file storage operations"""
    
    def __init__(self):
        self.storage_provider = settings.STORAGE_PROVIDER
        
        if self.storage_provider == "s3":
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            self.bucket_name = settings.AWS_S3_BUCKET
        else:
            # Local storage
            self.local_storage_path = settings.UPLOAD_PATH
            os.makedirs(self.local_storage_path, exist_ok=True)

    async def upload_file(
        self,
        file_content: bytes,
        file_key: str,
        content_type: str,
        metadata: Dict[str, str] = None
    ) -> str:
        """Upload file to storage"""
        if self.storage_provider == "s3":
            return await self._upload_to_s3(file_content, file_key, content_type, metadata)
        else:
            return await self._upload_to_local(file_content, file_key)

    async def _upload_to_s3(
        self,
        file_content: bytes,
        file_key: str,
        content_type: str,
        metadata: Dict[str, str] = None
    ) -> str:
        """Upload file to S3"""
        try:
            upload_args = {
                'Bucket': self.bucket_name,
                'Key': file_key,
                'Body': file_content,
                'ContentType': content_type,
                'ServerSideEncryption': 'AES256'
            }
            
            if metadata:
                upload_args['Metadata'] = metadata
            
            self.s3_client.put_object(**upload_args)
            
            logger.info("File uploaded to S3", 
                       file_key=file_key, 
                       size=len(file_content))
            return file_key
            
        except ClientError as e:
            logger.error("Failed to upload file to S3", 
                        error=str(e), 
                        file_key=file_key)
            raise Exception(f"Failed to upload file: {str(e)}")

    async def _upload_to_local(self, file_content: bytes, file_key: str) -> str:
        """Upload file to local storage"""
        try:
            file_path = os.path.join(self.local_storage_path, file_key)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            logger.info("File uploaded to local storage", 
                       file_key=file_key, 
                       size=len(file_content))
            return file_key
            
        except Exception as e:
            logger.error("Failed to upload file to local storage", 
                        error=str(e), 
                        file_key=file_key)
            raise Exception(f"Failed to upload file: {str(e)}")

    async def download_file(self, file_key: str) -> BinaryIO:
        """Download file from storage"""
        if self.storage_provider == "s3":
            return await self._download_from_s3(file_key)
        else:
            return await self._download_from_local(file_key)

    async def _download_from_s3(self, file_key: str) -> BinaryIO:
        """Download file from S3"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=file_key
            )
            return io.BytesIO(response['Body'].read())
            
        except ClientError as e:
            logger.error("Failed to download file from S3", 
                        error=str(e), 
                        file_key=file_key)
            raise Exception(f"Failed to download file: {str(e)}")

    async def _download_from_local(self, file_key: str) -> BinaryIO:
        """Download file from local storage"""
        try:
            file_path = os.path.join(self.local_storage_path, file_key)
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_key}")
            
            with open(file_path, 'rb') as f:
                return io.BytesIO(f.read())
                
        except Exception as e:
            logger.error("Failed to download file from local storage", 
                        error=str(e), 
                        file_key=file_key)
            raise Exception(f"Failed to download file: {str(e)}")

    async def get_file_stream(self, file_key: str) -> BinaryIO:
        """Get file stream for streaming responses"""
        if self.storage_provider == "s3":
            try:
                response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=file_key
                )
                return response['Body']
            except ClientError as e:
                logger.error("Failed to get file stream from S3", 
                            error=str(e), 
                            file_key=file_key)
                raise Exception(f"Failed to get file stream: {str(e)}")
        else:
            return await self._download_from_local(file_key)

    async def delete_file(self, file_key: str) -> bool:
        """Delete file from storage"""
        if self.storage_provider == "s3":
            return await self._delete_from_s3(file_key)
        else:
            return await self._delete_from_local(file_key)

    async def _delete_from_s3(self, file_key: str) -> bool:
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=file_key
            )
            logger.info("File deleted from S3", file_key=file_key)
            return True
            
        except ClientError as e:
            logger.error("Failed to delete file from S3", 
                        error=str(e), 
                        file_key=file_key)
            return False

    async def _delete_from_local(self, file_key: str) -> bool:
        """Delete file from local storage"""
        try:
            file_path = os.path.join(self.local_storage_path, file_key)
            
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info("File deleted from local storage", file_key=file_key)
                return True
            else:
                logger.warning("File not found for deletion", file_key=file_key)
                return False
                
        except Exception as e:
            logger.error("Failed to delete file from local storage", 
                        error=str(e), 
                        file_key=file_key)
            return False

    async def file_exists(self, file_key: str) -> bool:
        """Check if file exists in storage"""
        if self.storage_provider == "s3":
            try:
                self.s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=file_key
                )
                return True
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    return False
                else:
                    logger.error("Error checking file existence", 
                                error=str(e), 
                                file_key=file_key)
                    raise Exception(f"Error checking file existence: {str(e)}")
        else:
            file_path = os.path.join(self.local_storage_path, file_key)
            return os.path.exists(file_path)

    async def get_file_metadata(self, file_key: str) -> Dict[str, Any]:
        """Get file metadata from storage"""
        if self.storage_provider == "s3":
            try:
                response = self.s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=file_key
                )
                return {
                    'size': response.get('ContentLength'),
                    'content_type': response.get('ContentType'),
                    'last_modified': response.get('LastModified'),
                    'etag': response.get('ETag'),
                    'metadata': response.get('Metadata', {})
                }
            except ClientError as e:
                logger.error("Failed to get file metadata", 
                            error=str(e), 
                            file_key=file_key)
                raise Exception(f"Failed to get file metadata: {str(e)}")
        else:
            file_path = os.path.join(self.local_storage_path, file_key)
            if os.path.exists(file_path):
                stat = os.stat(file_path)
                return {
                    'size': stat.st_size,
                    'last_modified': stat.st_mtime,
                    'content_type': 'application/octet-stream'  # Default
                }
            else:
                raise FileNotFoundError(f"File not found: {file_key}")

    async def get_presigned_url(
        self,
        file_key: str,
        expiration: int = 3600,
        method: str = 'get_object'
    ) -> str:
        """Generate presigned URL for file access (S3 only)"""
        if self.storage_provider != "s3":
            raise NotImplementedError("Presigned URLs only available for S3 storage")
        
        try:
            url = self.s3_client.generate_presigned_url(
                method,
                Params={'Bucket': self.bucket_name, 'Key': file_key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error("Failed to generate presigned URL", 
                        error=str(e), 
                        file_key=file_key)
            raise Exception(f"Failed to generate presigned URL: {str(e)}")

    async def list_files(self, prefix: str = "", max_keys: int = 1000) -> List[Dict[str, Any]]:
        """List files in storage with optional prefix"""
        if self.storage_provider == "s3":
            try:
                response = self.s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=prefix,
                    MaxKeys=max_keys
                )
                
                files = []
                for obj in response.get('Contents', []):
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'],
                        'etag': obj['ETag']
                    })
                return files
                
            except ClientError as e:
                logger.error("Failed to list files", 
                            error=str(e), 
                            prefix=prefix)
                raise Exception(f"Failed to list files: {str(e)}")
        else:
            # List local files
            files = []
            search_path = os.path.join(self.local_storage_path, prefix)
            
            if os.path.exists(search_path):
                for root, dirs, filenames in os.walk(search_path):
                    for filename in filenames:
                        file_path = os.path.join(root, filename)
                        relative_path = os.path.relpath(file_path, self.local_storage_path)
                        stat = os.stat(file_path)
                        
                        files.append({
                            'key': relative_path.replace('\\', '/'),  # Normalize path separators
                            'size': stat.st_size,
                            'last_modified': stat.st_mtime
                        })
                        
                        if len(files) >= max_keys:
                            break
            
            return files

    async def get_storage_usage(self, prefix: str = "") -> Dict[str, Any]:
        """Get storage usage statistics"""
        files = await self.list_files(prefix=prefix)
        
        total_size = sum(file['size'] for file in files)
        file_count = len(files)
        
        return {
            'total_files': file_count,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'total_size_gb': round(total_size / (1024 * 1024 * 1024), 2)
        }
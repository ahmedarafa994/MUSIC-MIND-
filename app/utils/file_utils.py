import os
import hashlib
import shutil
import uuid
from typing import Optional, Dict, Any, List
from pathlib import Path
import magic # type: ignore
import logging
from fastapi.concurrency import run_in_threadpool
import aioboto3 # For async S3
import botocore # For S3 client errors
from app.core.config import settings # For S3 settings

logger = logging.getLogger(__name__)

class FileManager:
    """File management utilities"""
    
    @staticmethod
    def _calculate_file_hash_sync(file_path: str, algorithm: str = "sha256") -> str:
        hash_func = getattr(hashlib, algorithm)()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        return hash_func.hexdigest()

    @staticmethod
    async def calculate_file_hash_async(file_path: str, algorithm: str = "sha256") -> str:
        """Calculate file hash asynchronously"""
        return await run_in_threadpool(FileManager._calculate_file_hash_sync, file_path, algorithm)
    
    @staticmethod
    def _get_file_mime_type_sync(file_path: str) -> str:
        try:
            mime = magic.Magic(mime=True)
            return mime.from_file(file_path)
        except Exception as e: # Catching generic Exception as python-magic can raise various errors
            logger.warning(f"python-magic failed for {file_path}: {e}, falling back to extension.")
            ext = Path(file_path).suffix.lower()
            mime_map = {
                '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.flac': 'audio/flac',
                '.aac': 'audio/aac', '.ogg': 'audio/ogg', '.m4a': 'audio/mp4'
            }
            return mime_map.get(ext, 'application/octet-stream')

    @staticmethod
    async def get_file_mime_type_async(file_path: str) -> str:
        """Get file MIME type asynchronously"""
        return await run_in_threadpool(FileManager._get_file_mime_type_sync, file_path)
    
    @staticmethod
    async def ensure_directory_async(directory: str) -> bool:
        """Ensure directory exists asynchronously"""
        try:
            await run_in_threadpool(os.makedirs, directory, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Error creating directory {directory}: {e}")
            return False
    
    @staticmethod
    async def generate_unique_filename_async(original_filename: str, directory: str = None) -> str:
        """Generate unique filename asynchronously"""
        file_id = uuid.uuid4()
        extension = Path(original_filename).suffix
        unique_filename = f"{file_id}{extension}"
        
        if directory:
            full_path = os.path.join(directory, unique_filename)
            counter = 1
            while await run_in_threadpool(os.path.exists, full_path):
                unique_filename = f"{file_id}_{counter}{extension}"
                full_path = os.path.join(directory, unique_filename)
                counter += 1
        return unique_filename
    
    @staticmethod
    async def safe_delete_file_async(file_path: str) -> bool:
        """Safely delete file asynchronously"""
        try:
            if await run_in_threadpool(os.path.exists, file_path):
                await run_in_threadpool(os.remove, file_path)
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return False
    
    @staticmethod
    async def copy_file_async(source: str, destination: str) -> bool:
        """Copy file safely asynchronously"""
        try:
            dest_dir = os.path.dirname(destination)
            await FileManager.ensure_directory_async(dest_dir)
            await run_in_threadpool(shutil.copy2, source, destination)
            return True
        except Exception as e:
            logger.error(f"Error copying file from {source} to {destination}: {e}")
            return False
    
    @staticmethod
    async def move_file_async(source: str, destination: str) -> bool:
        """Move file safely asynchronously"""
        try:
            dest_dir = os.path.dirname(destination)
            await FileManager.ensure_directory_async(dest_dir)
            await run_in_threadpool(shutil.move, source, destination)
            return True
        except Exception as e:
            logger.error(f"Error moving file from {source} to {destination}: {e}")
            return False
    
    @staticmethod
    async def get_file_size_async(file_path: str) -> int:
        """Get file size in bytes asynchronously"""
        try:
            return await run_in_threadpool(os.path.getsize, file_path)
        except Exception as e:
            logger.error(f"Error getting file size for {file_path}: {e}")
            return 0
    
    @staticmethod
    def _validate_audio_file_sync(file_path: str, max_size: Optional[int]) -> Dict[str, Any]:
        result: Dict[str, Any] = {"valid": False, "errors": [], "warnings": [], "info": {}}
        if not os.path.exists(file_path):
            result["errors"].append("File does not exist")
            return result
        
        file_size = os.path.getsize(file_path)
        result["info"]["file_size"] = file_size
        if max_size and file_size > max_size:
            result["errors"].append(f"File size ({file_size} bytes) exceeds maximum ({max_size} bytes)")
            return result
            
        mime_type = FileManager._get_file_mime_type_sync(file_path) # Use sync version internally
        result["info"]["mime_type"] = mime_type
        allowed_types = ['audio/mpeg', 'audio/wav', 'audio/flac', 'audio/aac', 'audio/ogg', 'audio/mp4']
        if mime_type not in allowed_types:
            result["errors"].append(f"Unsupported file type: {mime_type}")
            return result
            
        try:
            import librosa # Keep import local to threadpool function if heavy
            y, sr = librosa.load(file_path, sr=None, duration=1.0)
            result["info"]["sample_rate"] = sr
            result["info"]["channels"] = 1 if len(y.shape) == 1 else y.shape[0]
        except Exception as e:
            result["errors"].append(f"Invalid audio file: {str(e)}")
            return result

        result["valid"] = True
        return result

    @staticmethod
    async def validate_audio_file_async(file_path: str, max_size: Optional[int] = None) -> Dict[str, Any]:
        """Validate audio file asynchronously"""
        try:
            return await run_in_threadpool(FileManager._validate_audio_file_sync, file_path, max_size)
        except Exception as e:
            return {"valid": False, "errors": [f"Validation error: {str(e)}"], "warnings": [], "info": {}}

    @staticmethod
    def _cleanup_temp_files_sync(temp_dir: str, max_age_hours: int) -> int:
        cleaned_count = 0
        import time
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        for filename in os.listdir(temp_dir): # os.listdir is blocking
            file_path = os.path.join(temp_dir, filename)
            if os.path.isfile(file_path): # os.path.isfile is blocking
                try:
                    file_age = current_time - os.path.getmtime(file_path) # os.path.getmtime is blocking
                    if file_age > max_age_seconds:
                        if os.path.exists(file_path): # Check before attempting delete
                           os.remove(file_path) # os.remove is blocking
                           cleaned_count += 1
                           logger.info(f"Cleaned up temp file: {filename}")
                except Exception as e_file:
                    logger.error(f"Error processing file {file_path} during cleanup: {e_file}")
        return cleaned_count

    @staticmethod
    async def cleanup_temp_files_async(temp_dir: str, max_age_hours: int = 24) -> int:
        """Clean up temporary files older than max_age_hours asynchronously"""
        try:
            return await run_in_threadpool(FileManager._cleanup_temp_files_sync, temp_dir, max_age_hours)
        except Exception as e:
            logger.error(f"Error during temp file cleanup: {e}")
            return 0

class StorageManager:
    """Storage management for different providers"""
    
    def __init__(self, provider: str = "local"):
        self.provider = provider
        if self.provider == "s3":
            # Initialize aioboto3 session here for reuse
            self.s3_session = aioboto3.Session(
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
        else:
            self.s3_session = None

    async def upload_file(self, local_path: str, remote_key: str) -> Dict[str, Any]:
        """Upload file to storage provider asynchronously"""
        if self.provider == "local":
            # For local, remote_key is the full destination path
            return await self._upload_local(local_path, remote_key)
        elif self.provider == "s3":
            return await self._upload_s3(local_path, remote_key)
        else:
            return {"success": False, "error": f"Unsupported provider: {self.provider}"}
    
    async def _upload_local(self, local_path: str, destination_path: str) -> Dict[str, Any]:
        """Upload to local storage asynchronously"""
        try:
            if await FileManager.copy_file_async(local_path, destination_path):
                return {"success": True, "url": destination_path, "provider": "local"}
            else:
                return {"success": False, "error": "Failed to copy file"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _upload_s3(self, local_path: str, s3_key: str) -> Dict[str, Any]:
        """Upload to AWS S3 asynchronously"""
        if not self.s3_session:
             return {"success": False, "error": "S3 session not initialized"}
        try:
            async with self.s3_session.client("s3") as s3_client:
                await s3_client.upload_file(local_path, settings.AWS_S3_BUCKET, s3_key)
            url = f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
            return {"success": True, "url": url, "provider": "s3"}
        except botocore.exceptions.ClientError as e:
            logger.error(f"S3 ClientError during upload: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"General error during S3 upload: {e}")
            return {"success": False, "error": str(e)}
    
    async def delete_file(self, remote_key: str) -> bool:
        """Delete file from storage provider asynchronously"""
        if self.provider == "local":
            # remote_key is the full path for local
            return await FileManager.safe_delete_file_async(remote_key)
        elif self.provider == "s3":
            return await self._delete_s3(remote_key)
        return False
    
    async def _delete_s3(self, s3_key: str) -> bool:
        """Delete from AWS S3 asynchronously"""
        if not self.s3_session: return False
        try:
            async with self.s3_session.client("s3") as s3_client:
                await s3_client.delete_object(Bucket=settings.AWS_S3_BUCKET, Key=s3_key)
            return True
        except botocore.exceptions.ClientError as e:
            logger.error(f"S3 ClientError during delete: {e}")
            return False
        except Exception as e:
            logger.error(f"General error during S3 delete: {e}")
            return False
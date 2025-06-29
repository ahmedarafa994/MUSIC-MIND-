import os
import hashlib
import shutil
import uuid
from typing import Optional, Dict, Any
from pathlib import Path
import magic
import logging

logger = logging.getLogger(__name__)

class FileManager:
    """File management utilities"""
    
    @staticmethod
    def calculate_file_hash(file_path: str, algorithm: str = "sha256") -> str:
        """Calculate file hash"""
        hash_func = getattr(hashlib, algorithm)()
        
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_func.update(chunk)
        
        return hash_func.hexdigest()
    
    @staticmethod
    def get_file_mime_type(file_path: str) -> str:
        """Get file MIME type"""
        try:
            mime = magic.Magic(mime=True)
            return mime.from_file(file_path)
        except:
            # Fallback to extension-based detection
            ext = Path(file_path).suffix.lower()
            mime_map = {
                '.mp3': 'audio/mpeg',
                '.wav': 'audio/wav',
                '.flac': 'audio/flac',
                '.aac': 'audio/aac',
                '.ogg': 'audio/ogg',
                '.m4a': 'audio/mp4'
            }
            return mime_map.get(ext, 'application/octet-stream')
    
    @staticmethod
    def ensure_directory(directory: str) -> bool:
        """Ensure directory exists"""
        try:
            os.makedirs(directory, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Error creating directory {directory}: {e}")
            return False
    
    @staticmethod
    def generate_unique_filename(original_filename: str, directory: str = None) -> str:
        """Generate unique filename"""
        file_id = uuid.uuid4()
        extension = Path(original_filename).suffix
        unique_filename = f"{file_id}{extension}"
        
        if directory:
            full_path = os.path.join(directory, unique_filename)
            # Ensure uniqueness
            counter = 1
            while os.path.exists(full_path):
                unique_filename = f"{file_id}_{counter}{extension}"
                full_path = os.path.join(directory, unique_filename)
                counter += 1
        
        return unique_filename
    
    @staticmethod
    def safe_delete_file(file_path: str) -> bool:
        """Safely delete file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return False
    
    @staticmethod
    def copy_file(source: str, destination: str) -> bool:
        """Copy file safely"""
        try:
            # Ensure destination directory exists
            dest_dir = os.path.dirname(destination)
            FileManager.ensure_directory(dest_dir)
            
            shutil.copy2(source, destination)
            return True
        except Exception as e:
            logger.error(f"Error copying file from {source} to {destination}: {e}")
            return False
    
    @staticmethod
    def move_file(source: str, destination: str) -> bool:
        """Move file safely"""
        try:
            # Ensure destination directory exists
            dest_dir = os.path.dirname(destination)
            FileManager.ensure_directory(dest_dir)
            
            shutil.move(source, destination)
            return True
        except Exception as e:
            logger.error(f"Error moving file from {source} to {destination}: {e}")
            return False
    
    @staticmethod
    def get_file_size(file_path: str) -> int:
        """Get file size in bytes"""
        try:
            return os.path.getsize(file_path)
        except Exception as e:
            logger.error(f"Error getting file size for {file_path}: {e}")
            return 0
    
    @staticmethod
    def validate_audio_file(file_path: str, max_size: int = None) -> Dict[str, Any]:
        """Validate audio file"""
        result = {
            "valid": False,
            "errors": [],
            "warnings": [],
            "info": {}
        }
        
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                result["errors"].append("File does not exist")
                return result
            
            # Check file size
            file_size = FileManager.get_file_size(file_path)
            result["info"]["file_size"] = file_size
            
            if max_size and file_size > max_size:
                result["errors"].append(f"File size ({file_size} bytes) exceeds maximum ({max_size} bytes)")
                return result
            
            # Check MIME type
            mime_type = FileManager.get_file_mime_type(file_path)
            result["info"]["mime_type"] = mime_type
            
            allowed_types = [
                'audio/mpeg', 'audio/wav', 'audio/flac', 
                'audio/aac', 'audio/ogg', 'audio/mp4'
            ]
            
            if mime_type not in allowed_types:
                result["errors"].append(f"Unsupported file type: {mime_type}")
                return result
            
            # Try to load with librosa for validation
            try:
                import librosa
                y, sr = librosa.load(file_path, sr=None, duration=1.0)  # Load first second
                result["info"]["sample_rate"] = sr
                result["info"]["channels"] = 1 if len(y.shape) == 1 else y.shape[0]
            except Exception as e:
                result["errors"].append(f"Invalid audio file: {str(e)}")
                return result
            
            result["valid"] = True
            
        except Exception as e:
            result["errors"].append(f"Validation error: {str(e)}")
        
        return result
    
    @staticmethod
    def cleanup_temp_files(temp_dir: str, max_age_hours: int = 24) -> int:
        """Clean up temporary files older than max_age_hours"""
        cleaned_count = 0
        
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for filename in os.listdir(temp_dir):
                file_path = os.path.join(temp_dir, filename)
                
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getmtime(file_path)
                    
                    if file_age > max_age_seconds:
                        if FileManager.safe_delete_file(file_path):
                            cleaned_count += 1
                            logger.info(f"Cleaned up temp file: {filename}")
        
        except Exception as e:
            logger.error(f"Error during temp file cleanup: {e}")
        
        return cleaned_count

class StorageManager:
    """Storage management for different providers"""
    
    def __init__(self, provider: str = "local"):
        self.provider = provider
    
    def upload_file(self, local_path: str, remote_path: str) -> Dict[str, Any]:
        """Upload file to storage provider"""
        if self.provider == "local":
            return self._upload_local(local_path, remote_path)
        elif self.provider == "s3":
            return self._upload_s3(local_path, remote_path)
        else:
            return {"success": False, "error": f"Unsupported provider: {self.provider}"}
    
    def _upload_local(self, local_path: str, remote_path: str) -> Dict[str, Any]:
        """Upload to local storage"""
        try:
            if FileManager.copy_file(local_path, remote_path):
                return {
                    "success": True,
                    "url": remote_path,
                    "provider": "local"
                }
            else:
                return {"success": False, "error": "Failed to copy file"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _upload_s3(self, local_path: str, remote_path: str) -> Dict[str, Any]:
        """Upload to AWS S3"""
        try:
            import boto3
            from app.core.config import settings
            
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            
            s3_client.upload_file(local_path, settings.AWS_S3_BUCKET, remote_path)
            
            url = f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{remote_path}"
            
            return {
                "success": True,
                "url": url,
                "provider": "s3"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def delete_file(self, remote_path: str) -> bool:
        """Delete file from storage provider"""
        if self.provider == "local":
            return FileManager.safe_delete_file(remote_path)
        elif self.provider == "s3":
            return self._delete_s3(remote_path)
        return False
    
    def _delete_s3(self, remote_path: str) -> bool:
        """Delete from AWS S3"""
        try:
            import boto3
            from app.core.config import settings
            
            s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            
            s3_client.delete_object(Bucket=settings.AWS_S3_BUCKET, Key=remote_path)
            return True
        except Exception as e:
            logger.error(f"Error deleting S3 file: {e}")
            return False
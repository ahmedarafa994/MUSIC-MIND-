from typing import Any, Dict, List, Optional
import re
import uuid
from datetime import datetime
from pydantic import validator
import logging

logger = logging.getLogger(__name__)

class ValidationUtils:
    """Validation utility functions"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_password(password: str) -> Dict[str, Any]:
        """Validate password strength"""
        result = {
            "valid": True,
            "errors": [],
            "score": 0
        }
        
        # Length check
        if len(password) < 8:
            result["errors"].append("Password must be at least 8 characters long")
            result["valid"] = False
        else:
            result["score"] += 1
        
        # Uppercase check
        if not re.search(r'[A-Z]', password):
            result["errors"].append("Password must contain at least one uppercase letter")
            result["valid"] = False
        else:
            result["score"] += 1
        
        # Lowercase check
        if not re.search(r'[a-z]', password):
            result["errors"].append("Password must contain at least one lowercase letter")
            result["valid"] = False
        else:
            result["score"] += 1
        
        # Digit check
        if not re.search(r'\d', password):
            result["errors"].append("Password must contain at least one digit")
            result["valid"] = False
        else:
            result["score"] += 1
        
        # Special character check (optional but recommended)
        if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            result["score"] += 1
        
        # Length bonus
        if len(password) >= 12:
            result["score"] += 1
        
        return result
    
    @staticmethod
    def validate_username(username: str) -> Dict[str, Any]:
        """Validate username"""
        result = {
            "valid": True,
            "errors": []
        }
        
        # Length check
        if len(username) < 3 or len(username) > 50:
            result["errors"].append("Username must be between 3 and 50 characters")
            result["valid"] = False
        
        # Character check
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            result["errors"].append("Username can only contain letters, numbers, underscores, and hyphens")
            result["valid"] = False
        
        # Reserved usernames
        reserved = ['admin', 'root', 'api', 'www', 'mail', 'ftp', 'test', 'user']
        if username.lower() in reserved:
            result["errors"].append("Username is reserved")
            result["valid"] = False
        
        return result
    
    @staticmethod
    def validate_uuid(uuid_string: str) -> bool:
        """Validate UUID format"""
        try:
            uuid.UUID(uuid_string)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_audio_parameters(params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate audio processing parameters"""
        result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Tempo validation
        if "tempo" in params:
            tempo = params["tempo"]
            if not isinstance(tempo, (int, float)) or tempo < 60 or tempo > 200:
                result["errors"].append("Tempo must be between 60 and 200 BPM")
                result["valid"] = False
        
        # Duration validation
        if "duration" in params:
            duration = params["duration"]
            if not isinstance(duration, (int, float)) or duration < 10 or duration > 300:
                result["errors"].append("Duration must be between 10 and 300 seconds")
                result["valid"] = False
        
        # Key validation
        if "key" in params:
            key = params["key"]
            valid_keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            if key not in valid_keys:
                result["errors"].append(f"Key must be one of: {', '.join(valid_keys)}")
                result["valid"] = False
        
        # Loudness validation
        if "target_loudness" in params:
            loudness = params["target_loudness"]
            if not isinstance(loudness, (int, float)) or loudness < -30 or loudness > 0:
                result["errors"].append("Target loudness must be between -30 and 0 LUFS")
                result["valid"] = False
        
        # Dynamic range validation
        if "dynamic_range" in params:
            dr = params["dynamic_range"]
            if not isinstance(dr, (int, float)) or dr < 1 or dr > 20:
                result["errors"].append("Dynamic range must be between 1 and 20 dB")
                result["valid"] = False
        
        # Stereo width validation
        if "stereo_width" in params:
            width = params["stereo_width"]
            if not isinstance(width, (int, float)) or width < 0 or width > 2:
                result["errors"].append("Stereo width must be between 0.0 and 2.0")
                result["valid"] = False
        
        return result
    
    @staticmethod
    def validate_file_upload(filename: str, file_size: int, mime_type: str, max_size: int) -> Dict[str, Any]:
        """Validate file upload parameters"""
        result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Filename validation
        if not filename or len(filename.strip()) == 0:
            result["errors"].append("Filename cannot be empty")
            result["valid"] = False
        
        # File extension validation
        allowed_extensions = ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a']
        file_ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        
        if file_ext not in allowed_extensions:
            result["errors"].append(f"File extension {file_ext} not allowed. Allowed: {', '.join(allowed_extensions)}")
            result["valid"] = False
        
        # File size validation
        if file_size <= 0:
            result["errors"].append("File size must be greater than 0")
            result["valid"] = False
        elif file_size > max_size:
            result["errors"].append(f"File size ({file_size} bytes) exceeds maximum ({max_size} bytes)")
            result["valid"] = False
        
        # MIME type validation
        allowed_mimes = [
            'audio/mpeg', 'audio/wav', 'audio/flac', 
            'audio/aac', 'audio/ogg', 'audio/mp4'
        ]
        
        if mime_type not in allowed_mimes:
            result["errors"].append(f"MIME type {mime_type} not allowed")
            result["valid"] = False
        
        # Warnings for large files
        if file_size > 50 * 1024 * 1024:  # 50MB
            result["warnings"].append("Large file size may result in longer processing times")
        
        return result
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe storage"""
        # Remove or replace dangerous characters
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Remove leading/trailing spaces and dots
        filename = filename.strip(' .')
        
        # Limit length
        if len(filename) > 255:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            max_name_length = 255 - len(ext) - 1 if ext else 255
            filename = name[:max_name_length] + ('.' + ext if ext else '')
        
        return filename
    
    @staticmethod
    def validate_api_key_name(name: str) -> Dict[str, Any]:
        """Validate API key name"""
        result = {
            "valid": True,
            "errors": []
        }
        
        if not name or len(name.strip()) == 0:
            result["errors"].append("API key name cannot be empty")
            result["valid"] = False
        
        if len(name) > 100:
            result["errors"].append("API key name cannot exceed 100 characters")
            result["valid"] = False
        
        # Check for valid characters
        if not re.match(r'^[a-zA-Z0-9\s\-_\.]+$', name):
            result["errors"].append("API key name can only contain letters, numbers, spaces, hyphens, underscores, and dots")
            result["valid"] = False
        
        return result
    
    @staticmethod
    def validate_scopes(scopes: str) -> Dict[str, Any]:
        """Validate API key scopes"""
        result = {
            "valid": True,
            "errors": [],
            "parsed_scopes": []
        }
        
        if not scopes:
            result["errors"].append("Scopes cannot be empty")
            result["valid"] = False
            return result
        
        valid_scopes = ['read', 'write', 'admin', 'files', 'sessions', 'users']
        scope_list = [scope.strip() for scope in scopes.split(',')]
        
        for scope in scope_list:
            if scope not in valid_scopes:
                result["errors"].append(f"Invalid scope: {scope}. Valid scopes: {', '.join(valid_scopes)}")
                result["valid"] = False
            else:
                result["parsed_scopes"].append(scope)
        
        return result

class DataSanitizer:
    """Data sanitization utilities"""
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = None, allow_html: bool = False) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            return str(value)
        
        # Strip whitespace
        value = value.strip()
        
        # Remove HTML if not allowed
        if not allow_html:
            value = re.sub(r'<[^>]+>', '', value)
        
        # Limit length
        if max_length and len(value) > max_length:
            value = value[:max_length]
        
        return value
    
    @staticmethod
    def sanitize_dict(data: Dict[str, Any], allowed_keys: List[str] = None) -> Dict[str, Any]:
        """Sanitize dictionary data"""
        if not isinstance(data, dict):
            return {}
        
        sanitized = {}
        
        for key, value in data.items():
            # Check if key is allowed
            if allowed_keys and key not in allowed_keys:
                continue
            
            # Sanitize key
            clean_key = DataSanitizer.sanitize_string(str(key), max_length=100)
            
            # Sanitize value based on type
            if isinstance(value, str):
                clean_value = DataSanitizer.sanitize_string(value, max_length=1000)
            elif isinstance(value, (int, float, bool)):
                clean_value = value
            elif isinstance(value, dict):
                clean_value = DataSanitizer.sanitize_dict(value)
            elif isinstance(value, list):
                clean_value = [DataSanitizer.sanitize_string(str(item), max_length=500) for item in value[:10]]  # Limit list size
            else:
                clean_value = DataSanitizer.sanitize_string(str(value), max_length=500)
            
            sanitized[clean_key] = clean_value
        
        return sanitized
import time
import asyncio
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, limits: Dict[str, int]):
        self.limits = limits  # e.g., {"requests_per_minute": 60}
        self.requests = {}
    
    async def can_proceed(self, identifier: str = "default") -> bool:
        """Check if request can proceed based on rate limits"""
        current_time = int(time.time())
        
        # Clean old entries
        self._cleanup_old_entries(current_time)
        
        # Check limits
        for limit_type, limit_value in self.limits.items():
            if "per_minute" in limit_type:
                window = 60
            elif "per_hour" in limit_type:
                window = 3600
            else:
                continue
            
            window_start = current_time - window
            key = f"{identifier}_{limit_type}"
            
            if key not in self.requests:
                self.requests[key] = []
            
            # Count requests in current window
            recent_requests = [
                req_time for req_time in self.requests[key]
                if req_time > window_start
            ]
            
            if len(recent_requests) >= limit_value:
                return False
        
        return True
    
    async def record_request(self, identifier: str = "default"):
        """Record a request"""
        current_time = int(time.time())
        
        for limit_type in self.limits.keys():
            key = f"{identifier}_{limit_type}"
            if key not in self.requests:
                self.requests[key] = []
            self.requests[key].append(current_time)
    
    def _cleanup_old_entries(self, current_time: int):
        """Clean up old entries to prevent memory leaks"""
        for key in list(self.requests.keys()):
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if current_time - req_time < 3600  # Keep last hour
            ]
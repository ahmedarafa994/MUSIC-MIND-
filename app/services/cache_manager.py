import json
import hashlib
from typing import Any, Optional, Dict
import redis.asyncio as redis
from app.core.config import settings
import structlog

logger = structlog.get_logger()

class CacheManager:
    """Redis-based caching for AI model results and metadata"""
    
    def __init__(self):
        self.redis_client = None
        self.default_ttl = 3600  # 1 hour
        self.model_result_ttl = 7200  # 2 hours for model results
        
    async def get_redis_client(self):
        """Get Redis client with connection pooling"""
        if not self.redis_client:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20
            )
        return self.redis_client
    
    def _generate_cache_key(self, prefix: str, data: Dict[str, Any]) -> str:
        """Generate deterministic cache key from data"""
        # Sort and serialize data for consistent hashing
        serialized = json.dumps(data, sort_keys=True)
        hash_obj = hashlib.md5(serialized.encode())
        return f"{prefix}:{hash_obj.hexdigest()}"
    
    async def get_model_result(self, model_name: str, input_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cached model result"""
        try:
            redis_client = await self.get_redis_client()
            cache_key = self._generate_cache_key(f"model_result:{model_name}", input_data)
            
            cached_result = await redis_client.get(cache_key)
            if cached_result:
                logger.info("Cache hit for model result", model=model_name, key=cache_key[:16])
                return json.loads(cached_result)
            
            return None
            
        except Exception as e:
            logger.warning("Cache get failed", error=str(e))
            return None
    
    async def set_model_result(self, model_name: str, input_data: Dict[str, Any], result: Dict[str, Any]):
        """Cache model result"""
        try:
            redis_client = await self.get_redis_client()
            cache_key = self._generate_cache_key(f"model_result:{model_name}", input_data)
            
            await redis_client.setex(
                cache_key,
                self.model_result_ttl,
                json.dumps(result)
            )
            
            logger.info("Cached model result", model=model_name, key=cache_key[:16])
            
        except Exception as e:
            logger.warning("Cache set failed", error=str(e))
    
    async def get_audio_analysis(self, audio_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached audio analysis"""
        try:
            redis_client = await self.get_redis_client()
            cache_key = f"audio_analysis:{audio_hash}"
            
            cached_analysis = await redis_client.get(cache_key)
            if cached_analysis:
                logger.info("Cache hit for audio analysis", hash=audio_hash[:16])
                return json.loads(cached_analysis)
            
            return None
            
        except Exception as e:
            logger.warning("Cache get failed", error=str(e))
            return None
    
    async def set_audio_analysis(self, audio_hash: str, analysis: Dict[str, Any]):
        """Cache audio analysis"""
        try:
            redis_client = await self.get_redis_client()
            cache_key = f"audio_analysis:{audio_hash}"
            
            await redis_client.setex(
                cache_key,
                self.default_ttl * 24,  # Cache for 24 hours
                json.dumps(analysis)
            )
            
            logger.info("Cached audio analysis", hash=audio_hash[:16])
            
        except Exception as e:
            logger.warning("Cache set failed", error=str(e))
    
    async def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a user"""
        try:
            redis_client = await self.get_redis_client()
            pattern = f"user:{user_id}:*"
            
            keys = await redis_client.keys(pattern)
            if keys:
                await redis_client.delete(*keys)
                logger.info("Invalidated user cache", user_id=user_id, keys_count=len(keys))
                
        except Exception as e:
            logger.warning("Cache invalidation failed", error=str(e))
    
    async def get_workflow_result(self, workflow_hash: str) -> Optional[Dict[str, Any]]:
        """Get cached workflow result"""
        try:
            redis_client = await self.get_redis_client()
            cache_key = f"workflow_result:{workflow_hash}"
            
            cached_result = await redis_client.get(cache_key)
            if cached_result:
                logger.info("Cache hit for workflow result", hash=workflow_hash[:16])
                return json.loads(cached_result)
            
            return None
            
        except Exception as e:
            logger.warning("Cache get failed", error=str(e))
            return None
    
    async def set_workflow_result(self, workflow_hash: str, result: Dict[str, Any]):
        """Cache workflow result"""
        try:
            redis_client = await self.get_redis_client()
            cache_key = f"workflow_result:{workflow_hash}"
            
            await redis_client.setex(
                cache_key,
                self.model_result_ttl * 2,  # Cache for 4 hours
                json.dumps(result)
            )
            
            logger.info("Cached workflow result", hash=workflow_hash[:16])
            
        except Exception as e:
            logger.warning("Cache set failed", error=str(e))

# Global cache manager
cache_manager = CacheManager()
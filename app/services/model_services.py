import asyncio
import httpx
from typing import Dict, List, Any, Optional
import structlog
from datetime import datetime

logger = structlog.get_logger()

class ModelServiceManager:
    """Manages communication with AI model microservices"""
    
    def __init__(self):
        self.service_endpoints = {
            "music_gen": "http://music-gen-service:8000",
            "stable_audio": "http://stable-audio-service:8000",
            "music_lm": "http://music-lm-service:8000",
            "audiocraft": "http://audiocraft-service:8000",
            "jukebox": "http://jukebox-service:8000",
            "melody_rnn": "http://melody-rnn-service:8000",
            "music_vae": "http://music-vae-service:8000",
            "aces": "http://aces-service:8000",
            "tepand_diff_rhythm": "http://rhythm-service:8000",
            "suni": "http://suni-service:8000",
            "beethoven_ai": "http://beethoven-service:8000",
            "mureka": "http://mureka-service:8000"
        }
        self.client = httpx.AsyncClient(timeout=300.0)  # 5 minute timeout
        
    async def is_model_available(self, model_name: str) -> bool:
        """Check if a model service is available"""
        endpoint = self.service_endpoints.get(model_name)
        if not endpoint:
            return False
            
        try:
            response = await self.client.get(f"{endpoint}/health")
            return response.status_code == 200
        except Exception as e:
            logger.warning("Model health check failed", model=model_name, error=str(e))
            return False
    
    async def execute_model(self, model_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a model with given input data"""
        endpoint = self.service_endpoints.get(model_name)
        if not endpoint:
            raise ValueError(f"Unknown model: {model_name}")
        
        try:
            response = await self.client.post(
                f"{endpoint}/process",
                json=input_data,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Model execution failed", model=model_name, error=str(e))
            raise
    
    async def get_resource_availability(self) -> Dict[str, Any]:
        """Get current resource availability across all services"""
        availability = {}
        
        for model_name, endpoint in self.service_endpoints.items():
            try:
                response = await self.client.get(f"{endpoint}/resources")
                if response.status_code == 200:
                    availability[model_name] = response.json()
                else:
                    availability[model_name] = {"available": False}
            except Exception:
                availability[model_name] = {"available": False}
        
        return availability
    
    async def get_model_capabilities(self, model_name: str) -> Dict[str, Any]:
        """Get capabilities and parameters for a specific model"""
        endpoint = self.service_endpoints.get(model_name)
        if not endpoint:
            return {}
        
        try:
            response = await self.client.get(f"{endpoint}/capabilities")
            return response.json() if response.status_code == 200 else {}
        except Exception:
            return {}
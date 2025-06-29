import os
import time
import asyncio
import random
from typing import Dict, Any, Optional, List
import httpx
import structlog
from app.core.config import settings
from app.services.rate_limiter import RateLimiter
from app.services.cost_tracker import cost_tracker
from app.services.fallback_manager import fallback_manager
from app.core.exceptions import (
    ServiceUnavailableError,
    RateLimitExceededError,
    APIExecutionError
)

logger = structlog.get_logger()

class GenericAPIClient:
    """Generic API client for all external AI services"""
    
    def __init__(self, endpoint: str, api_key: str, timeout: int, provider: str, model: str = None):
        self.endpoint = endpoint
        self.api_key = api_key
        self.timeout = timeout
        self.provider = provider
        self.model = model
        self.client = httpx.AsyncClient(timeout=timeout)

    async def execute_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute API request based on provider type"""
        
        if self.provider == "huggingface":
            return await self._execute_huggingface_request(request_data)
        elif self.provider == "stability_ai":
            return await self._execute_stability_request(request_data)
        elif self.provider == "google_ai":
            return await self._execute_google_request(request_data)
        elif self.provider == "replicate":
            return await self._execute_replicate_request(request_data)
        elif self.provider == "magenta":
            return await self._execute_magenta_request(request_data)
        elif self.provider == "landr":
            return await self._execute_landr_request(request_data)
        else:
            return await self._execute_generic_request(request_data)

    async def _execute_huggingface_request(self, request_data: Dict) -> Dict:
        """Execute Hugging Face API request"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": request_data.get("prompt", ""),
            "parameters": {
                "duration": request_data.get("duration", 30),
                "temperature": request_data.get("temperature", 0.8),
                "top_k": request_data.get("top_k", 250),
                "top_p": request_data.get("top_p", 0.0),
                "max_new_tokens": request_data.get("max_tokens", 256)
            }
        }
        
        response = await self.client.post(self.endpoint, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    async def _execute_stability_request(self, request_data: Dict) -> Dict:
        """Execute Stability AI API request"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "prompt": request_data.get("prompt", ""),
            "duration": request_data.get("duration", 30),
            "cfg_scale": request_data.get("cfg_scale", 7),
            "seed": request_data.get("seed", random.randint(0, 2**32-1))
        }
        
        response = await self.client.post(self.endpoint, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    async def _execute_google_request(self, request_data: Dict) -> Dict:
        """Execute Google AI API request"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": request_data.get("prompt", "")
                }]
            }],
            "generationConfig": {
                "temperature": request_data.get("temperature", 0.8),
                "maxOutputTokens": request_data.get("max_tokens", 1024)
            }
        }
        
        response = await self.client.post(self.endpoint, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    async def _execute_replicate_request(self, request_data: Dict) -> Dict:
        """Execute Replicate API request"""
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "version": request_data.get("version", "latest"),
            "input": {
                "prompt": request_data.get("prompt", ""),
                "duration": request_data.get("duration", 30),
                **request_data.get("parameters", {})
            }
        }
        
        # Create prediction
        response = await self.client.post(self.endpoint, json=payload, headers=headers)
        response.raise_for_status()
        prediction = response.json()
        
        # Poll for completion
        prediction_url = prediction["urls"]["get"]
        while prediction["status"] in ["starting", "processing"]:
            await asyncio.sleep(2)
            response = await self.client.get(prediction_url, headers=headers)
            prediction = response.json()
        
        return prediction

    async def _execute_magenta_request(self, request_data: Dict) -> Dict:
        """Execute Magenta API request"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "instances": [{
                "input": request_data.get("input_sequence", []),
                "temperature": request_data.get("temperature", 1.0),
                "steps": request_data.get("steps", 128)
            }]
        }
        
        response = await self.client.post(self.endpoint, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    async def _execute_landr_request(self, request_data: Dict) -> Dict:
        """Execute LANDR mastering API request"""
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "landr-mastering.p.rapidapi.com"
        }
        
        # LANDR expects multipart form data for audio files
        files = None
        data = {}
        
        if "audio_file" in request_data:
            files = {
                "audio": request_data["audio_file"]
            }
            data = {
                "intensity": request_data.get("intensity", "medium"),
                "style": request_data.get("style", "balanced"),
                "loudness": request_data.get("loudness", -14),
                "stereo_width": request_data.get("stereo_width", "normal")
            }
        else:
            # For status checks and other operations
            data = request_data
        
        if files:
            response = await self.client.post(self.endpoint, headers=headers, files=files, data=data)
        else:
            headers["Content-Type"] = "application/json"
            response = await self.client.post(self.endpoint, headers=headers, json=data)
        
        response.raise_for_status()
        return response.json()

    async def _execute_generic_request(self, request_data: Dict) -> Dict:
        """Execute generic API request"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        response = await self.client.post(self.endpoint, json=request_data, headers=headers)
        response.raise_for_status()
        return response.json()

class APIIntegrationManager:
    """Manages all external AI API integrations"""
    
    def __init__(self):
        self.api_clients = {}
        self.api_configs = self._load_api_configurations()
        self.rate_limiters = {}
    
    def _load_api_configurations(self) -> Dict[str, Any]:
        """Load comprehensive API configurations for all AI services"""
        return {
            # Text-to-Music Generation Services
            "musicgen": {
                "provider": "huggingface",
                "endpoint": "https://api-inference.huggingface.co/models/facebook/musicgen-medium",
                "api_key_env": "HUGGINGFACE_API_KEY",
                "rate_limit": {"requests_per_minute": 60},
                "cost_per_request": 0.001,
                "timeout": 300,
                "retry_attempts": 3,
                "capabilities": ["text_to_music", "melody_conditioning"],
                "max_duration": 300,
                "fallbacks": ["beethoven_ai", "mureka_ai"]
            },
            "stable_audio": {
                "provider": "stability_ai",
                "endpoint": "https://api.stability.ai/v2beta/stable-audio/generate/music",
                "api_key_env": "STABILITY_API_KEY",
                "rate_limit": {"requests_per_minute": 30},
                "cost_per_second": 0.01,
                "timeout": 600,
                "retry_attempts": 2,
                "capabilities": ["text_to_audio", "high_fidelity"],
                "max_duration": 90,
                "fallbacks": ["musicgen"]
            },
            "google_musiclm": {
                "provider": "google_ai",
                "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/musiclm:generateContent",
                "api_key_env": "GOOGLE_AI_API_KEY",
                "rate_limit": {"requests_per_minute": 100},
                "cost_per_request": 0.002,
                "timeout": 300,
                "retry_attempts": 3,
                "capabilities": ["text_to_music", "semantic_understanding"],
                "max_duration": 300,
                "fallbacks": ["musicgen", "stable_audio"]
            },
            
            # Audio Enhancement & Processing Services
            "audiocraft": {
                "provider": "replicate",
                "endpoint": "https://api.replicate.com/v1/predictions",
                "model": "meta/audiocraft",
                "api_key_env": "REPLICATE_API_TOKEN",
                "rate_limit": {"requests_per_minute": 20},
                "cost_per_prediction": 0.03,
                "timeout": 900,
                "retry_attempts": 2,
                "capabilities": ["audio_enhancement", "compression", "effects"],
                "max_duration": 600,
                "fallbacks": ["aces_audio"]
            },
            "jukebox": {
                "provider": "replicate",
                "endpoint": "https://api.replicate.com/v1/predictions",
                "model": "openai/jukebox",
                "api_key_env": "REPLICATE_API_TOKEN",
                "rate_limit": {"requests_per_minute": 5},
                "cost_per_prediction": 0.15,
                "timeout": 1800,
                "retry_attempts": 1,
                "capabilities": ["style_transfer", "genre_conversion"],
                "max_duration": 240,
                "fallbacks": []
            },
            "aces_audio": {
                "provider": "custom",
                "endpoint": "https://api.aces-audio.com/v1/enhance",
                "api_key_env": "ACES_API_KEY",
                "rate_limit": {"requests_per_minute": 40},
                "cost_per_minute": 0.05,
                "timeout": 600,
                "retry_attempts": 3,
                "capabilities": ["professional_mastering", "noise_reduction"],
                "max_duration": 1200,
                "fallbacks": ["suni_ai"]
            },
            
            # Melody & Composition Services
            "melody_rnn": {
                "provider": "magenta",
                "endpoint": "https://api.magenta.tensorflow.org/v1/models/melody_rnn:predict",
                "api_key_env": "MAGENTA_API_KEY",
                "rate_limit": {"requests_per_minute": 100},
                "cost_per_request": 0.001,
                "timeout": 120,
                "retry_attempts": 3,
                "capabilities": ["melody_generation", "continuation"],
                "max_duration": 60,
                "fallbacks": ["music_vae"]
            },
            "music_vae": {
                "provider": "magenta",
                "endpoint": "https://api.magenta.tensorflow.org/v1/models/music_vae:predict",
                "api_key_env": "MAGENTA_API_KEY",
                "rate_limit": {"requests_per_minute": 80},
                "cost_per_request": 0.002,
                "timeout": 180,
                "retry_attempts": 3,
                "capabilities": ["interpolation", "variation_generation"],
                "max_duration": 120,
                "fallbacks": ["melody_rnn"]
            },
            
            # Rhythm & Beat Services
            "tepand_diff_rhythm": {
                "provider": "custom",
                "endpoint": "https://api.tepand.ai/v1/rhythm/generate",
                "api_key_env": "TEPAND_API_KEY",
                "rate_limit": {"requests_per_minute": 50},
                "cost_per_request": 0.01,
                "timeout": 300,
                "retry_attempts": 2,
                "capabilities": ["rhythm_generation", "beat_analysis"],
                "max_duration": 300,
                "fallbacks": []
            },
            
            # Specialized AI Services
            "suni_ai": {
                "provider": "suni",
                "endpoint": "https://api.suni.ai/v1/process",
                "api_key_env": "SUNI_API_KEY",
                "rate_limit": {"requests_per_minute": 25},
                "cost_per_request": 0.03,
                "timeout": 400,
                "retry_attempts": 2,
                "capabilities": ["audio_analysis", "feature_extraction"],
                "max_duration": 600,
                "fallbacks": ["aces_audio"]
            },
            "beethoven_ai": {
                "provider": "beethoven",
                "endpoint": "https://api.beethoven.ai/v1/compose",
                "api_key_env": "BEETHOVEN_API_KEY",
                "rate_limit": {"requests_per_minute": 15},
                "cost_per_composition": 0.08,
                "timeout": 600,
                "retry_attempts": 2,
                "capabilities": ["classical_composition", "orchestration"],
                "max_duration": 480,
                "fallbacks": ["musicgen"]
            },
            "mureka_ai": {
                "provider": "mureka",
                "endpoint": "https://api.mureka.ai/v1/generate",
                "api_key_env": "MUREKA_API_KEY",
                "rate_limit": {"requests_per_minute": 30},
                "cost_per_request": 0.02,
                "timeout": 300,
                "retry_attempts": 2,
                "capabilities": ["creative_generation", "style_mixing"],
                "max_duration": 240,
                "fallbacks": ["musicgen", "beethoven_ai"]
            },
            
            # Professional Mastering Services
            "landr_mastering": {
                "provider": "landr",
                "endpoint": "https://landr-mastering.p.rapidapi.com/v1/master",
                "api_key_env": "LANDR_API_KEY",
                "rate_limit": {"requests_per_minute": 10},
                "cost_per_master": 0.50,
                "timeout": 600,
                "retry_attempts": 2,
                "capabilities": ["professional_mastering", "loudness_optimization", "stereo_enhancement"],
                "max_duration": 600,
                "fallbacks": ["aces_audio"]
            }
        }

    async def initialize_clients(self):
        """Initialize all API clients"""
        for service_name, config in self.api_configs.items():
            try:
                api_key = getattr(settings, config["api_key_env"], None)
                if not api_key:
                    logger.warning(f"No API key found for {service_name}")
                    continue

                client = GenericAPIClient(
                    endpoint=config["endpoint"],
                    api_key=api_key,
                    timeout=config["timeout"],
                    provider=config["provider"],
                    model=config.get("model")
                )
                
                self.api_clients[service_name] = client
                self.rate_limiters[service_name] = RateLimiter(config["rate_limit"])
                
                logger.info(f"Initialized API client for {service_name}")
                
            except Exception as e:
                logger.error(f"Failed to initialize {service_name}: {e}")

    async def execute_api_request(self, service_name: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute API request with comprehensive error handling"""
        if service_name not in self.api_clients:
            raise ServiceUnavailableError(f"API client for {service_name} not available")

        # Check rate limits
        rate_limiter = self.rate_limiters.get(service_name)
        if rate_limiter and not await rate_limiter.can_proceed():
            raise RateLimitExceededError(f"Rate limit exceeded for {service_name}")

        client = self.api_clients[service_name]
        config = self.api_configs[service_name]

        # Execute with retries and exponential backoff
        for attempt in range(config["retry_attempts"]):
            try:
                start_time = time.time()
                response = await client.execute_request(request_data)
                execution_time = time.time() - start_time

                # Track usage and costs
                await rate_limiter.record_request()
                await cost_tracker.track_usage(service_name, request_data, execution_time)

                return {
                    "status": "success",
                    "response": response,
                    "execution_time": execution_time,
                    "service": service_name,
                    "attempt": attempt + 1,
                    "cost": self._calculate_cost(service_name, request_data, execution_time)
                }

            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {service_name}: {e}")
                
                if attempt == config["retry_attempts"] - 1:
                    # Try fallback services
                    fallback_result = await fallback_manager.try_fallback(
                        service_name, request_data, str(e)
                    )
                    if fallback_result:
                        return fallback_result
                    
                    raise APIExecutionError(f"All attempts failed for {service_name}: {e}")

                # Exponential backoff with jitter
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                await asyncio.sleep(wait_time)

    def _calculate_cost(self, service_name: str, request_data: Dict, execution_time: float) -> float:
        """Calculate cost based on service pricing model"""
        config = self.api_configs[service_name]
        
        if "cost_per_request" in config:
            return config["cost_per_request"]
        elif "cost_per_second" in config:
            duration = request_data.get("duration", 30)
            return config["cost_per_second"] * duration
        elif "cost_per_minute" in config:
            duration = request_data.get("duration", 30)
            return config["cost_per_minute"] * (duration / 60)
        elif "cost_per_prediction" in config:
            return config["cost_per_prediction"]
        elif "cost_per_composition" in config:
            return config["cost_per_composition"]
        else:
            return 0.01  # Default cost

    async def get_service_capabilities(self, service_name: str) -> List[str]:
        """Get capabilities of a specific service"""
        if service_name in self.api_configs:
            return self.api_configs[service_name].get("capabilities", [])
        return []

    async def get_available_services(self) -> Dict[str, Dict]:
        """Get all available services and their status"""
        services = {}
        for service_name, config in self.api_configs.items():
            services[service_name] = {
                "available": service_name in self.api_clients,
                "capabilities": config.get("capabilities", []),
                "max_duration": config.get("max_duration", 300),
                "cost_model": {
                    k: v for k, v in config.items() 
                    if k.startswith("cost_")
                }
            }
        return services

# Global API integration manag
api_integration_manager = APIIntegrationManager()
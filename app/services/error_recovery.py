import asyncio
from typing import Dict, Any, Optional, List
from enum import Enum
import structlog
from datetime import datetime, timedelta

logger = structlog.get_logger()

class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RecoveryStrategy(Enum):
    RETRY = "retry"
    FALLBACK = "fallback"
    SKIP = "skip"
    ABORT = "abort"

class ErrorRecoveryManager:
    """Manages error recovery strategies for the AI processing pipeline"""
    
    def __init__(self):
        self.error_patterns = self._load_error_patterns()
        self.recovery_strategies = self._load_recovery_strategies()
        self.circuit_breakers = {}
        
    def _load_error_patterns(self) -> Dict[str, Dict]:
        """Load known error patterns and their classifications"""
        return {
            "rate_limit_exceeded": {
                "severity": ErrorSeverity.MEDIUM,
                "retry_delay": 60,
                "max_retries": 3,
                "strategy": RecoveryStrategy.RETRY
            },
            "model_unavailable": {
                "severity": ErrorSeverity.HIGH,
                "retry_delay": 30,
                "max_retries": 2,
                "strategy": RecoveryStrategy.FALLBACK
            },
            "insufficient_resources": {
                "severity": ErrorSeverity.HIGH,
                "retry_delay": 120,
                "max_retries": 2,
                "strategy": RecoveryStrategy.RETRY
            },
            "invalid_input_format": {
                "severity": ErrorSeverity.LOW,
                "retry_delay": 0,
                "max_retries": 0,
                "strategy": RecoveryStrategy.SKIP
            },
            "timeout": {
                "severity": ErrorSeverity.MEDIUM,
                "retry_delay": 30,
                "max_retries": 2,
                "strategy": RecoveryStrategy.RETRY
            },
            "authentication_failed": {
                "severity": ErrorSeverity.CRITICAL,
                "retry_delay": 0,
                "max_retries": 0,
                "strategy": RecoveryStrategy.ABORT
            }
        }
    
    def _load_recovery_strategies(self) -> Dict[str, Dict]:
        """Load recovery strategies for different model types"""
        return {
            "generation": {
                "fallback_models": ["music_gen", "beethoven_ai", "mureka"],
                "degraded_mode": True,
                "skip_allowed": False
            },
            "enhancement": {
                "fallback_models": ["aces", "suni", "audiocraft"],
                "degraded_mode": True,
                "skip_allowed": True
            },
            "analysis": {
                "fallback_models": ["music_lm"],
                "degraded_mode": False,
                "skip_allowed": False
            }
        }
    
    async def handle_error(
        self, 
        error: Exception, 
        model_name: str, 
        attempt: int,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle error and determine recovery strategy"""
        
        error_type = self._classify_error(error)
        error_config = self.error_patterns.get(error_type, {})
        
        recovery_decision = {
            "error_type": error_type,
            "severity": error_config.get("severity", ErrorSeverity.MEDIUM),
            "strategy": error_config.get("strategy", RecoveryStrategy.RETRY),
            "retry_delay": error_config.get("retry_delay", 30),
            "max_retries": error_config.get("max_retries", 2),
            "should_retry": attempt < error_config.get("max_retries", 2),
            "fallback_models": self._get_fallback_models(model_name),
            "circuit_breaker_triggered": await self._check_circuit_breaker(model_name)
        }
        
        # Log error with context
        logger.error(
            "Error occurred in model execution",
            model=model_name,
            error_type=error_type,
            attempt=attempt,
            recovery_strategy=recovery_decision["strategy"].value,
            error=str(error)
        )
        
        # Update circuit breaker
        await self._update_circuit_breaker(model_name, success=False)
        
        return recovery_decision
    
    def _classify_error(self, error: Exception) -> str:
        """Classify error based on error message and type"""
        error_message = str(error).lower()
        
        if "rate limit" in error_message or "too many requests" in error_message:
            return "rate_limit_exceeded"
        elif "unavailable" in error_message or "service not found" in error_message:
            return "model_unavailable"
        elif "timeout" in error_message or "timed out" in error_message:
            return "timeout"
        elif "insufficient" in error_message and "resource" in error_message:
            return "insufficient_resources"
        elif "invalid" in error_message and ("format" in error_message or "input" in error_message):
            return "invalid_input_format"
        elif "authentication" in error_message or "unauthorized" in error_message:
            return "authentication_failed"
        else:
            return "unknown_error"
    
    def _get_fallback_models(self, model_name: str) -> List[str]:
        """Get fallback models for a given model"""
        # This would be integrated with your model configuration
        model_fallbacks = {
            "music_gen": ["beethoven_ai", "mureka"],
            "stable_audio": ["audiocraft", "aces"],
            "aces": ["suni", "audiocraft"],
            "jukebox": ["stable_audio", "audiocraft"],
            # Add more fallback mappings
        }
        return model_fallbacks.get(model_name, [])
    
    async def _check_circuit_breaker(self, model_name: str) -> bool:
        """Check if circuit breaker is triggered for a model"""
        if model_name not in self.circuit_breakers:
            self.circuit_breakers[model_name] = {
                "failure_count": 0,
                "last_failure": None,
                "state": "closed"  # closed, open, half_open
            }
        
        breaker = self.circuit_breakers[model_name]
        
        # If circuit is open, check if enough time has passed to try again
        if breaker["state"] == "open":
            if breaker["last_failure"]:
                time_since_failure = datetime.utcnow() - breaker["last_failure"]
                if time_since_failure > timedelta(minutes=5):  # 5 minute cooldown
                    breaker["state"] = "half_open"
                    logger.info("Circuit breaker half-open", model=model_name)
                    return False
            return True
        
        return False
    
    async def _update_circuit_breaker(self, model_name: str, success: bool):
        """Update circuit breaker state based on success/failure"""
        if model_name not in self.circuit_breakers:
            self.circuit_breakers[model_name] = {
                "failure_count": 0,
                "last_failure": None,
                "state": "closed"
            }
        
        breaker = self.circuit_breakers[model_name]
        
        if success:
            # Reset on success
            breaker["failure_count"] = 0
            breaker["state"] = "closed"
            logger.debug("Circuit breaker reset", model=model_name)
        else:
            # Increment failure count
            breaker["failure_count"] += 1
            breaker["last_failure"] = datetime.utcnow()
            
            # Open circuit if too many failures
            if breaker["failure_count"] >= 5:  # 5 failures trigger circuit breaker
                breaker["state"] = "open"
                logger.warning("Circuit breaker opened", model=model_name, failures=breaker["failure_count"])
    
    async def execute_recovery_strategy(
        self, 
        strategy: RecoveryStrategy, 
        model_name: str, 
        input_data: Dict[str, Any],
        fallback_models: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Execute the determined recovery strategy"""
        
        if strategy == RecoveryStrategy.RETRY:
            # Handled by the calling function
            return None
            
        elif strategy == RecoveryStrategy.FALLBACK:
            for fallback_model in fallback_models:
                try:
                    # Check if fallback model is available
                    if not await self._check_circuit_breaker(fallback_model):
                        logger.info("Attempting fallback model", 
                                   original=model_name, 
                                   fallback=fallback_model)
                        
                        # This would integrate with your model manager
                        # result = await model_manager.execute_model(fallback_model, input_data)
                        # return result
                        
                        # For now, return a placeholder
                        return {"fallback_used": fallback_model, "success": True}
                        
                except Exception as e:
                    logger.warning("Fallback model also failed", 
                                 fallback=fallback_model, 
                                 error=str(e))
                    continue
            
            return None
            
        elif strategy == RecoveryStrategy.SKIP:
            logger.info("Skipping failed step", model=model_name)
            return {"skipped": True, "reason": "recoverable_error"}
            
        elif strategy == RecoveryStrategy.ABORT:
            logger.error("Aborting processing due to critical error", model=model_name)
            raise Exception(f"Critical error in {model_name}, aborting processing")
        
        return None

# Global error recovery manager
error_recovery_manager = ErrorRecoveryManager()
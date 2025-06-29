from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class AgentStatus(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskType(str, Enum):
    ANALYSIS = "analysis"
    GENERATION = "generation"
    PROCESSING = "processing"
    MASTERING = "mastering"
    CONVERSION = "conversion"

class BaseAgent(ABC):
    """Base class for all AI music agents"""
    
    def __init__(self, agent_id: str = None):
        self.agent_id = agent_id or str(uuid.uuid4())
        self.status = AgentStatus.IDLE
        self.current_task = None
        self.task_history = []
        self.capabilities = []
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        
    @abstractmethod
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a user request"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Get agent capabilities"""
        pass
    
    @abstractmethod
    def estimate_cost(self, request: Dict[str, Any]) -> float:
        """Estimate processing cost"""
        pass
    
    @abstractmethod
    def estimate_time(self, request: Dict[str, Any]) -> int:
        """Estimate processing time in seconds"""
        pass
    
    def update_status(self, status: AgentStatus, message: str = None):
        """Update agent status"""
        self.status = status
        self.last_activity = datetime.utcnow()
        
        if message:
            logger.info(f"Agent {self.agent_id} status: {status} - {message}")
    
    def add_task_to_history(self, task: Dict[str, Any]):
        """Add completed task to history"""
        task["completed_at"] = datetime.utcnow()
        self.task_history.append(task)
        
        # Keep only last 100 tasks
        if len(self.task_history) > 100:
            self.task_history = self.task_history[-100:]
    
    def get_status_info(self) -> Dict[str, Any]:
        """Get current status information"""
        return {
            "agent_id": self.agent_id,
            "status": self.status,
            "current_task": self.current_task,
            "capabilities": self.capabilities,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "tasks_completed": len(self.task_history)
        }
    
    async def validate_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Validate incoming request"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Basic validation
        if not isinstance(request, dict):
            validation_result["valid"] = False
            validation_result["errors"].append("Request must be a dictionary")
            return validation_result
        
        # Check required fields
        required_fields = ["type", "user_id"]
        for field in required_fields:
            if field not in request:
                validation_result["valid"] = False
                validation_result["errors"].append(f"Missing required field: {field}")
        
        return validation_result
    
    async def prepare_execution_plan(self, request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prepare execution plan for request"""
        plan = []
        
        # This is a basic implementation - subclasses should override
        plan.append({
            "step": 1,
            "type": "validation",
            "description": "Validate input parameters",
            "estimated_time": 5
        })
        
        plan.append({
            "step": 2,
            "type": "processing",
            "description": "Process request",
            "estimated_time": 60
        })
        
        plan.append({
            "step": 3,
            "type": "finalization",
            "description": "Finalize and save results",
            "estimated_time": 10
        })
        
        return plan
    
    def calculate_quality_score(self, results: Dict[str, Any]) -> float:
        """Calculate quality score for results"""
        # Basic quality scoring - subclasses should implement specific logic
        base_score = 0.8
        
        # Adjust based on processing success
        if results.get("success", False):
            base_score += 0.1
        else:
            base_score -= 0.3
        
        # Adjust based on error count
        error_count = len(results.get("errors", []))
        base_score -= error_count * 0.05
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, base_score))

class AgentTask:
    """Represents a task being executed by an agent"""
    
    def __init__(self, task_type: TaskType, parameters: Dict[str, Any]):
        self.id = str(uuid.uuid4())
        self.type = task_type
        self.parameters = parameters
        self.status = "pending"
        self.created_at = datetime.utcnow()
        self.started_at = None
        self.completed_at = None
        self.results = None
        self.errors = []
        self.progress = 0
        
    def start(self):
        """Mark task as started"""
        self.status = "running"
        self.started_at = datetime.utcnow()
        
    def complete(self, results: Dict[str, Any]):
        """Mark task as completed"""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        self.results = results
        self.progress = 100
        
    def fail(self, error: str):
        """Mark task as failed"""
        self.status = "failed"
        self.completed_at = datetime.utcnow()
        self.errors.append(error)
        
    def update_progress(self, progress: int):
        """Update task progress"""
        self.progress = max(0, min(100, progress))
        
    def get_execution_time(self) -> float:
        """Get task execution time in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary"""
        return {
            "id": self.id,
            "type": self.type,
            "status": self.status,
            "progress": self.progress,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "execution_time": self.get_execution_time(),
            "results": self.results,
            "errors": self.errors
        }

class AgentRegistry:
    """Registry for managing available agents"""
    
    def __init__(self):
        self.agents = {}
        self.agent_types = {}
        
    def register_agent(self, agent_class, agent_type: str):
        """Register an agent class"""
        self.agent_types[agent_type] = agent_class
        logger.info(f"Registered agent type: {agent_type}")
        
    def create_agent(self, agent_type: str, **kwargs) -> BaseAgent:
        """Create an agent instance"""
        if agent_type not in self.agent_types:
            raise ValueError(f"Unknown agent type: {agent_type}")
            
        agent_class = self.agent_types[agent_type]
        agent = agent_class(**kwargs)
        self.agents[agent.agent_id] = agent
        
        logger.info(f"Created agent {agent.agent_id} of type {agent_type}")
        return agent
        
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get agent by ID"""
        return self.agents.get(agent_id)
        
    def remove_agent(self, agent_id: str):
        """Remove agent from registry"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            logger.info(f"Removed agent {agent_id}")
            
    def get_available_agents(self, task_type: str = None) -> List[BaseAgent]:
        """Get available agents, optionally filtered by task type"""
        available = []
        
        for agent in self.agents.values():
            if agent.status == AgentStatus.IDLE:
                if task_type is None or task_type in agent.get_capabilities():
                    available.append(agent)
                    
        return available
        
    def get_agent_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        total_agents = len(self.agents)
        status_counts = {}
        
        for agent in self.agents.values():
            status = agent.status
            status_counts[status] = status_counts.get(status, 0) + 1
            
        return {
            "total_agents": total_agents,
            "status_distribution": status_counts,
            "available_types": list(self.agent_types.keys())
        }

# Global agent registry
agent_registry = AgentRegistry()
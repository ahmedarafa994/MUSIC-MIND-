import asyncio
import json
from typing import Dict, Any, List, Optional
import structlog
from app.services.api_integration_manager import api_integration_manager
from app.services.task_planner import TaskPlanner
from app.services.tool_selector import ToolSelector
from app.services.task_executor import TaskExecutor
from app.services.format_standardizer import FormatStandardizer
from app.services.response_generator import ResponseGenerator

logger = structlog.get_logger()

class MusicAgent:
    """Intelligent music processing agent that orchestrates AI workflows"""
    
    def __init__(self):
        self.task_planner = TaskPlanner()
        self.tool_selector = ToolSelector()
        self.task_executor = TaskExecutor(api_integration_manager)
        self.format_standardizer = FormatStandardizer()
        self.response_generator = ResponseGenerator()
        
    async def process_request(self, user_request: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process a user request through the complete AI workflow"""
        
        if context is None:
            context = {}
            
        logger.info("Processing user request", request=user_request[:100])
        
        try:
            # Step 1: Get available tools
            available_tools = await self._get_available_tools()
            
            # Step 2: Decompose request into tasks
            task_list = await self.task_planner.decompose_request(
                user_request, context, available_tools
            )
            
            if not task_list:
                return {
                    "success": False,
                    "error": "Could not create execution plan for request",
                    "message": "The request could not be processed. Please try rephrasing or providing more details."
                }
            
            # Step 3: Select optimal tools for each task
            execution_plan = await self.tool_selector.select_tools_for_tasks(
                task_list, api_integration_manager
            )
            
            # Step 4: Execute the plan
            execution_results = await self.task_executor.execute_plan(
                execution_plan, self.format_standardizer
            )
            
            # Step 5: Generate comprehensive response
            final_response = await self.response_generator.synthesize_response(
                user_request, execution_results, task_list
            )
            
            logger.info("Request processing completed", 
                       success_rate=final_response.get("success_rate", 0),
                       total_cost=execution_results["execution_metadata"].get("total_cost", 0))
            
            return final_response
            
        except Exception as e:
            logger.error("Error processing request", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "message": "An error occurred while processing your request. Please try again."
            }
    
    async def _get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available AI tools and their capabilities"""
        
        available_services = await api_integration_manager.get_available_services()
        tools = []
        
        for service_name, service_info in available_services.items():
            if service_info["available"]:
                tools.append({
                    "name": service_name,
                    "capabilities": service_info["capabilities"],
                    "max_duration": service_info["max_duration"],
                    "cost_model": service_info["cost_model"]
                })
        
        return tools
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """Get current agent status and capabilities"""
        
        available_services = await api_integration_manager.get_available_services()
        
        total_services = len(available_services)
        available_count = sum(1 for s in available_services.values() if s["available"])
        
        return {
            "status": "operational" if available_count > 0 else "degraded",
            "available_services": available_count,
            "total_services": total_services,
            "availability_percentage": round((available_count / total_services) * 100, 1),
            "capabilities": {
                "text_to_music": any("text_to_music" in s.get("capabilities", []) 
                                   for s in available_services.values() if s["available"]),
                "audio_enhancement": any("audio_enhancement" in s.get("capabilities", []) 
                                       for s in available_services.values() if s["available"]),
                "style_transfer": any("style_transfer" in s.get("capabilities", []) 
                                    for s in available_services.values() if s["available"]),
                "melody_generation": any("melody_generation" in s.get("capabilities", []) 
                                       for s in available_services.values() if s["available"])
            }
        }

# Global music agent instance
music_agent = MusicAgent()
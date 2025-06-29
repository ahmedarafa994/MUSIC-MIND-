import asyncio
import time
from typing import Dict, Any, List
import structlog
from app.services.api_integration_manager import APIIntegrationManager
from app.services.format_standardizer import FormatStandardizer

logger = structlog.get_logger()

class TaskExecutor:
    def __init__(self, api_manager: APIIntegrationManager):
        self.api_manager = api_manager
        self.progress_tracker = ProgressTracker()
    
    async def execute_plan(self, execution_plan: Dict, 
                          format_standardizer: FormatStandardizer) -> Dict[str, Any]:
        """Execute the planned tasks"""
        
        results = {
            "task_results": {},
            "execution_metadata": {
                "start_time": time.time(),
                "total_tasks": len(execution_plan["tasks"]),
                "completed_tasks": 0,
                "failed_tasks": 0,
                "total_cost": 0.0
            },
            "intermediate_files": {},
            "final_outputs": {}
        }
        
        # Execute parallel groups
        for group_index, parallel_group in enumerate(execution_plan["parallel_groups"]):
            logger.info(f"Executing parallel group {group_index + 1}")
            
            # Execute tasks in parallel
            parallel_tasks = [
                self._execute_single_task(task, results, format_standardizer)
                for task in parallel_group
            ]
            
            parallel_results = await asyncio.gather(
                *parallel_tasks, return_exceptions=True
            )
            
            # Process results
            for i, result in enumerate(parallel_results):
                task = parallel_group[i]
                task_id = task["task_id"]
                
                if isinstance(result, Exception):
                    await self._handle_task_failure(task, result, results)
                    results["execution_metadata"]["failed_tasks"] += 1
                else:
                    results["task_results"][task_id] = result
                    results["execution_metadata"]["completed_tasks"] += 1
                    results["execution_metadata"]["total_cost"] += result.get("cost", 0)
        
        results["execution_metadata"]["end_time"] = time.time()
        results["execution_metadata"]["total_duration"] = (
            results["execution_metadata"]["end_time"] - 
            results["execution_metadata"]["start_time"]
        )
        
        return results
    
    async def _execute_single_task(self, task: Dict, results: Dict, 
                                  format_standardizer: FormatStandardizer) -> Dict[str, Any]:
        """Execute a single task"""
        
        task_id = task["task_id"]
        primary_tool = task["primary_tool"]["tool_name"]
        task_details = task["task_details"]
        
        logger.info(f"Executing task {task_id} with tool {primary_tool}")
        
        try:
            # Prepare input data
            input_data = await self._prepare_task_input(task, results, format_standardizer)
            
            # Execute primary tool
            result = await self.api_manager.execute_api_request(
                primary_tool, 
                input_data
            )
            
            # Process and standardize output
            processed_result = await self._process_task_output(
                result, task_details, format_standardizer
            )
            
            logger.info(f"Task {task_id} completed successfully")
            
            return {
                "task_id": task_id,
                "status": "success",
                "tool_used": primary_tool,
                "result": processed_result,
                "execution_time": result.get("execution_time", 0),
                "cost": task.get("estimated_cost", 0)
            }
            
        except Exception as e:
            logger.error(f"Task {task_id} failed with primary tool", error=str(e))
            
            # Try fallback tools
            for fallback in task.get("fallback_tools", []):
                try:
                    logger.info(f"Retrying task {task_id} with fallback {fallback['tool_name']}")
                    
                    result = await self.api_manager.execute_api_request(
                        fallback["tool_name"], 
                        input_data
                    )
                    
                    processed_result = await self._process_task_output(
                        result, task_details, format_standardizer
                    )
                    
                    return {
                        "task_id": task_id,
                        "status": "success_fallback",
                        "tool_used": fallback["tool_name"],
                        "result": processed_result,
                        "primary_tool_error": str(e),
                        "execution_time": result.get("execution_time", 0),
                        "cost": fallback.get("estimated_cost", 0)
                    }
                    
                except Exception as fallback_error:
                    logger.warning(f"Fallback {fallback['tool_name']} also failed", 
                                 error=str(fallback_error))
                    continue
            
            # All tools failed
            raise Exception(f"All tools failed for task {task_id}: {str(e)}")
    
    async def _prepare_task_input(self, task: Dict, results: Dict, 
                                format_standardizer: FormatStandardizer) -> Dict[str, Any]:
        """Prepare input data for task execution"""
        
        task_details = task["task_details"]
        input_requirements = task_details.get("input_requirements", {})
        parameters = task_details.get("parameters", {})
        
        input_data = parameters.copy()
        
        # Handle dependencies
        dependencies = task_details.get("dependencies", [])
        for dep_id in dependencies:
            if dep_id in results["task_results"]:
                dep_result = results["task_results"][dep_id]["result"]
                # Use the output of dependency as input
                input_data.update(dep_result)
        
        # Apply format conversion if needed
        source_format = input_requirements.get("format")
        if source_format and "output" in input_data:
            converted_data = await format_standardizer.prepare_input(
                input_data["output"], 
                source_format, 
                source_format,  # Target format same as source for now
                {}
            )
            input_data["output"] = converted_data
        
        return input_data
    
    async def _process_task_output(self, result: Dict, task_details: Dict, 
                                 format_standardizer: FormatStandardizer) -> Dict[str, Any]:
        """Process and standardize task output"""
        
        output_format = task_details.get("output_format", "")
        
        # Extract the actual result from API response
        if "response" in result:
            output_data = result["response"]
        else:
            output_data = result
        
        # Apply format standardization
        standardized_output = await format_standardizer.standardize_output(
            output_data, output_format
        )
        
        return standardized_output
    
    async def _handle_task_failure(self, task: Dict, error: Exception, results: Dict):
        """Handle task failure"""
        task_id = task["task_id"]
        
        logger.error(f"Task {task_id} failed permanently", error=str(error))
        
        results["task_results"][task_id] = {
            "status": "failed",
            "error": str(error),
            "task_id": task_id
        }

class ProgressTracker:
    def __init__(self):
        self.task_progress = {}
    
    async def update_task_status(self, task_id: str, status: str):
        """Update task status"""
        self.task_progress[task_id] = {
            "status": status,
            "updated_at": time.time()
        }
        logger.info(f"Task {task_id} status updated to {status}")
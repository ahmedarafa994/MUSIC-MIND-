import json
from typing import Dict, Any, List
import structlog

logger = structlog.get_logger()

class ResponseGenerator:
    def __init__(self):
        pass
    
    async def synthesize_response(self, original_request: str, 
                                execution_results: Dict, task_list: List) -> Dict[str, Any]:
        """Generate comprehensive response"""
        
        # Assess overall success
        total_tasks = execution_results["execution_metadata"]["total_tasks"]
        completed_tasks = execution_results["execution_metadata"]["completed_tasks"]
        success_rate = completed_tasks / total_tasks if total_tasks > 0 else 0
        
        # Extract final outputs
        final_outputs = await self._extract_final_outputs(execution_results)
        
        # Generate summary
        summary = await self._generate_summary(
            original_request, execution_results, success_rate
        )
        
        # Create processing chain summary
        processing_chain = []
        for task in task_list:
            task_id = task["task_id"]
            if task_id in execution_results["task_results"]:
                result = execution_results["task_results"][task_id]
                processing_chain.append({
                    "task": task["task_name"],
                    "tool": result.get("tool_used", "unknown"),
                    "status": result.get("status", "unknown"),
                    "execution_time": result.get("execution_time", 0)
                })
        
        return {
            "status": "completed" if success_rate > 0.5 else "partially_failed",
            "original_request": original_request,
            "summary": summary,
            "results": final_outputs,
            "processing_chain": processing_chain,
            "execution_metadata": execution_results["execution_metadata"],
            "success_rate": success_rate
        }
    
    async def _extract_final_outputs(self, execution_results: Dict) -> Dict[str, Any]:
        """Extract final outputs from execution results"""
        
        final_outputs = {}
        
        for task_id, result in execution_results["task_results"].items():
            if result.get("status") == "success" or result.get("status") == "success_fallback":
                output_data = result.get("result", {})
                if "output" in output_data:
                    final_outputs[task_id] = {
                        "data": output_data["output"],
                        "format": output_data.get("format", "unknown"),
                        "metadata": output_data.get("metadata", {})
                    }
        
        return final_outputs
    
    async def _generate_summary(self, request: str, results: Dict, success_rate: float) -> str:
        """Generate natural language summary"""
        
        total_tasks = results["execution_metadata"]["total_tasks"]
        completed_tasks = results["execution_metadata"]["completed_tasks"]
        total_duration = results["execution_metadata"].get("total_duration", 0)
        total_cost = results["execution_metadata"].get("total_cost", 0)
        
        if success_rate == 1.0:
            status_text = "Successfully completed"
        elif success_rate > 0.5:
            status_text = "Partially completed"
        else:
            status_text = "Failed to complete"
        
        summary = f"{status_text} your request: '{request}'. "
        summary += f"Executed {completed_tasks} of {total_tasks} tasks in {total_duration:.1f} seconds. "
        
        if total_cost > 0:
            summary += f"Total cost: ${total_cost:.3f}. "
        
        if success_rate < 1.0:
            failed_tasks = total_tasks - completed_tasks
            summary += f"{failed_tasks} tasks failed but fallback strategies were applied where possible."
        
        return summary
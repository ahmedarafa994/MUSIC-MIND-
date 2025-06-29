import json
from typing import Dict, Any, List
import httpx
import structlog
from app.core.config import settings

logger = structlog.get_logger()

class TaskPlanner:
    def __init__(self):
        self.llm_client = self._initialize_llm_client()
    
    def _initialize_llm_client(self):
        """Initialize LLM client (Claude or OpenAI)"""
        if settings.ANTHROPIC_API_KEY:
            from anthropic import AsyncAnthropic
            return AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        elif settings.OPENAI_API_KEY:
            from openai import AsyncOpenAI
            return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        else:
            raise ValueError("No LLM API key configured")
    
    async def decompose_request(self, user_request: str, context: Dict[str, Any], 
                               available_tools: List[Dict]) -> List[Dict]:
        """Decompose user request into executable sub-tasks"""
        
        prompt = self._build_planning_prompt(user_request, context, available_tools)
        
        try:
            if hasattr(self.llm_client, 'messages'):  # Anthropic
                response = await self.llm_client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=2000,
                    temperature=0.1,
                    messages=[{"role": "user", "content": prompt}]
                )
                llm_response = response.content[0].text
            else:  # OpenAI
                response = await self.llm_client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=2000
                )
                llm_response = response.choices[0].message.content
            
            # Parse LLM response into structured task list
            task_list = self._parse_task_response(llm_response)
            
            # Validate and optimize task sequence
            optimized_tasks = await self._optimize_task_sequence(task_list)
            
            return optimized_tasks
            
        except Exception as e:
            logger.error("Task planning failed", error=str(e))
            # Fallback to simple task creation
            return self._create_fallback_tasks(user_request)
    
    def _build_planning_prompt(self, request: str, context: Dict, tools: List) -> str:
        return f"""
You are MusicAgent's Task Planner. Analyze the user request and decompose it into executable tasks.

User Request: "{request}"
Context: {json.dumps(context, indent=2)}

Available Tools:
{self._format_tool_descriptions(tools)}

Create a detailed execution plan as a JSON array of tasks:
[
  {{
    "task_id": "unique_id",
    "task_name": "descriptive_name", 
    "description": "what this task accomplishes",
    "tool_name": "specific_tool_to_use",
    "input_requirements": {{"format": "audio/text/midi", "source": "user_upload/previous_task"}},
    "output_format": "expected_output_format",
    "dependencies": ["task_id1", "task_id2"],
    "can_parallelize": true/false,
    "estimated_duration": 30,
    "parameters": {{"param1": "value1"}}
  }}
]

Focus on breaking complex requests into atomic, executable tasks while ensuring proper data flow.
"""
    
    def _format_tool_descriptions(self, tools: List[Dict]) -> str:
        """Format tool descriptions for prompt"""
        descriptions = []
        for tool in tools:
            desc = f"- {tool['name']}: {', '.join(tool['capabilities'])}"
            desc += f" (Max duration: {tool['max_duration']}s)"
            descriptions.append(desc)
        return "\n".join(descriptions)
    
    def _parse_task_response(self, response: str) -> List[Dict]:
        """Parse LLM response into task list"""
        try:
            # Extract JSON from response
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1
            json_str = response[start_idx:end_idx]
            
            tasks = json.loads(json_str)
            
            # Validate task structure
            validated_tasks = []
            for i, task in enumerate(tasks):
                if self._validate_task_structure(task):
                    validated_tasks.append(task)
                else:
                    logger.warning(f"Invalid task structure at index {i}")
            
            return validated_tasks
            
        except Exception as e:
            logger.error("Failed to parse task response", error=str(e))
            return []
    
    def _validate_task_structure(self, task: Dict) -> bool:
        """Validate task has required fields"""
        required_fields = ["task_id", "task_name", "tool_name", "output_format"]
        return all(field in task for field in required_fields)
    
    async def _optimize_task_sequence(self, tasks: List[Dict]) -> List[Dict]:
        """Optimize task execution order"""
        # Simple optimization - can be enhanced with graph algorithms
        optimized = []
        completed_tasks = set()
        
        while len(optimized) < len(tasks):
            for task in tasks:
                if task["task_id"] in completed_tasks:
                    continue
                
                # Check if dependencies are met
                dependencies = task.get("dependencies", [])
                if all(dep in completed_tasks for dep in dependencies):
                    optimized.append(task)
                    completed_tasks.add(task["task_id"])
                    break
        
        return optimized
    
    def _create_fallback_tasks(self, request: str) -> List[Dict]:
        """Create simple fallback tasks"""
        return [{
            "task_id": "fallback_generation",
            "task_name": "Generate Music",
            "tool_name": "musicgen",
            "input_requirements": {"format": "text"},
            "output_format": "audio/wav",
            "dependencies": [],
            "parameters": {"text": request, "duration": 30}
        }]
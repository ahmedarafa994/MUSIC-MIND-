from typing import Dict, Any, List
import structlog

logger = structlog.get_logger()

class ToolSelector:
    def __init__(self):
        self.tool_capabilities = self._load_tool_capabilities()
    
    def _load_tool_capabilities(self) -> Dict[str, Dict]:
        """Load tool capabilities and specifications"""
        return {
            "musicgen": {
                "category": "generation",
                "input_formats": ["text", "text+melody"],
                "output_formats": ["audio/wav"],
                "capabilities": ["text_to_music", "melody_conditioning"],
                "max_duration": 300,
                "cost_factor": 1.0,
                "reliability": 0.9
            },
            "stable_audio": {
                "category": "generation",
                "input_formats": ["text"],
                "output_formats": ["audio/wav"],
                "capabilities": ["text_to_audio", "high_fidelity"],
                "max_duration": 90,
                "cost_factor": 2.0,
                "reliability": 0.85
            },
            "google_musiclm": {
                "category": "generation",
                "input_formats": ["text"],
                "output_formats": ["audio/wav"],
                "capabilities": ["text_to_music", "semantic_understanding"],
                "max_duration": 300,
                "cost_factor": 1.5,
                "reliability": 0.8
            },
            "beethoven_ai": {
                "category": "generation",
                "input_formats": ["text"],
                "output_formats": ["audio/wav"],
                "capabilities": ["classical_composition", "orchestration"],
                "max_duration": 480,
                "cost_factor": 3.0,
                "reliability": 0.75
            },
            "mureka_ai": {
                "category": "generation",
                "input_formats": ["text"],
                "output_formats": ["audio/wav"],
                "capabilities": ["creative_generation", "style_mixing"],
                "max_duration": 240,
                "cost_factor": 2.5,
                "reliability": 0.7
            },
            "audiocraft": {
                "category": "enhancement",
                "input_formats": ["audio/wav", "audio/mp3"],
                "output_formats": ["audio/wav"],
                "capabilities": ["audio_enhancement", "compression", "effects"],
                "max_duration": 600,
                "cost_factor": 1.5,
                "reliability": 0.85
            },
            "jukebox": {
                "category": "style_transfer",
                "input_formats": ["audio/wav", "audio/mp3"],
                "output_formats": ["audio/wav"],
                "capabilities": ["style_transfer", "genre_conversion"],
                "max_duration": 240,
                "cost_factor": 3.0,
                "reliability": 0.7
            },
            "aces_audio": {
                "category": "mastering",
                "input_formats": ["audio/wav", "audio/mp3"],
                "output_formats": ["audio/wav"],
                "capabilities": ["professional_mastering", "noise_reduction"],
                "max_duration": 1200,
                "cost_factor": 2.0,
                "reliability": 0.9
            },
            "melody_rnn": {
                "category": "melody",
                "input_formats": ["midi", "text"],
                "output_formats": ["midi", "audio/wav"],
                "capabilities": ["melody_generation", "continuation"],
                "max_duration": 60,
                "cost_factor": 0.8,
                "reliability": 0.85
            },
            "music_vae": {
                "category": "melody",
                "input_formats": ["midi", "audio/wav"],
                "output_formats": ["midi", "audio/wav"],
                "capabilities": ["interpolation", "variation_generation"],
                "max_duration": 120,
                "cost_factor": 1.0,
                "reliability": 0.8
            },
            "tepand_diff_rhythm": {
                "category": "rhythm",
                "input_formats": ["midi", "audio/wav"],
                "output_formats": ["midi", "audio/wav"],
                "capabilities": ["rhythm_generation", "beat_analysis"],
                "max_duration": 300,
                "cost_factor": 1.2,
                "reliability": 0.75
            },
            "suni_ai": {
                "category": "analysis",
                "input_formats": ["audio/wav", "audio/mp3"],
                "output_formats": ["application/json", "audio/wav"],
                "capabilities": ["audio_analysis", "feature_extraction"],
                "max_duration": 600,
                "cost_factor": 1.5,
                "reliability": 0.85
            }
        }
    
    async def select_tools_for_tasks(self, task_list: List[Dict], 
                                   api_manager) -> Dict[str, Any]:
        """Select optimal tools for each task"""
        
        execution_plan = {
            "tasks": [],
            "parallel_groups": [],
            "total_estimated_time": 0,
            "total_estimated_cost": 0.0
        }
        
        for task in task_list:
            # Find candidate tools
            candidates = self._find_candidate_tools(task)
            
            # Score and rank candidates
            scored_candidates = await self._score_candidates(candidates, task)
            
            if not scored_candidates:
                logger.warning(f"No suitable tools found for task {task['task_id']}")
                continue
            
            # Select primary tool and fallbacks
            primary_tool = scored_candidates[0]
            fallback_tools = scored_candidates[1:3]
            
            execution_plan["tasks"].append({
                "task_id": task["task_id"],
                "primary_tool": primary_tool,
                "fallback_tools": fallback_tools,
                "task_details": task,
                "estimated_cost": primary_tool["estimated_cost"],
                "estimated_time": primary_tool["estimated_time"]
            })
            
            execution_plan["total_estimated_cost"] += primary_tool["estimated_cost"]
            execution_plan["total_estimated_time"] += primary_tool["estimated_time"]
        
        # Identify parallel execution opportunities
        execution_plan["parallel_groups"] = self._identify_parallel_groups(
            execution_plan["tasks"]
        )
        
        return execution_plan
    
    def _find_candidate_tools(self, task: Dict) -> List[str]:
        """Find tools that can handle the task"""
        candidates = []
        
        required_input = task.get("input_requirements", {}).get("format", "")
        required_output = task.get("output_format", "")
        tool_name = task.get("tool_name", "")
        
        # If specific tool requested, prioritize it
        if tool_name in self.tool_capabilities:
            candidates.append(tool_name)
        
        # Find compatible tools
        for tool, capabilities in self.tool_capabilities.items():
            if tool == tool_name:
                continue
                
            # Check input/output compatibility
            if (required_input in capabilities["input_formats"] and 
                required_output in capabilities["output_formats"]):
                candidates.append(tool)
        
        return candidates
    
    async def _score_candidates(self, candidates: List[str], task: Dict) -> List[Dict]:
        """Score tool candidates"""
        scored_tools = []
        
        for tool_name in candidates:
            capabilities = self.tool_capabilities[tool_name]
            
            score = 0.0
            
            # Capability match score (40%)
            if task.get("tool_name") == tool_name:
                score += 0.4
            else:
                score += 0.2
            
            # Reliability score (30%)
            score += capabilities["reliability"] * 0.3
            
            # Cost efficiency score (20%)
            cost_score = 1.0 / capabilities["cost_factor"]
            score += cost_score * 0.2
            
            # Duration compatibility (10%)
            duration = task.get("parameters", {}).get("duration", 30)
            if duration <= capabilities["max_duration"]:
                score += 0.1
            
            estimated_cost = self._estimate_tool_cost(tool_name, task)
            estimated_time = self._estimate_processing_time(tool_name, task)
            
            scored_tools.append({
                "tool_name": tool_name,
                "score": score,
                "estimated_cost": estimated_cost,
                "estimated_time": estimated_time,
                "capabilities": capabilities
            })
        
        return sorted(scored_tools, key=lambda x: x["score"], reverse=True)
    
    def _estimate_tool_cost(self, tool_name: str, task: Dict) -> float:
        """Estimate cost for using tool"""
        capabilities = self.tool_capabilities[tool_name]
        base_cost = 0.01
        duration = task.get("parameters", {}).get("duration", 30)
        
        return base_cost * capabilities["cost_factor"] * (duration / 30)
    
    def _estimate_processing_time(self, tool_name: str, task: Dict) -> float:
        """Estimate processing time"""
        duration = task.get("parameters", {}).get("duration", 30)
        base_time = 10  # Base processing time in seconds
        
        if tool_name in ["stable_audio", "beethoven_ai"]:
            return base_time + (duration * 2)
        elif tool_name in ["mureka_ai", "google_musiclm"]:
            return base_time + (duration * 1.5)
        else:
            return base_time + duration
    
    def _identify_parallel_groups(self, tasks: List[Dict]) -> List[List[Dict]]:
        """Identify tasks that can run in parallel"""
        parallel_groups = []
        
        # Simple implementation - can be enhanced with dependency graph analysis
        independent_tasks = []
        dependent_tasks = []
        
        for task in tasks:
            dependencies = task["task_details"].get("dependencies", [])
            if not dependencies:
                independent_tasks.append(task)
            else:
                dependent_tasks.append(task)
        
        if independent_tasks:
            parallel_groups.append(independent_tasks)
        
        # Group dependent tasks by their dependencies
        for task in dependent_tasks:
            parallel_groups.append([task])
        
        return parallel_groups
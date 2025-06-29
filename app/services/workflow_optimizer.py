from typing import Dict, List, Any
import structlog

logger = structlog.get_logger()

class WorkflowOptimizer:
    """Optimizes processing workflows based on audio characteristics and resources"""
    
    def __init__(self):
        self.preset_workflows = {
            "standard_mastering": {
                "name": "Standard Mastering",
                "description": "Professional mastering workflow",
                "steps": [
                    {"model_name": "music_lm", "parameters": {"analysis_depth": "full"}},
                    {"model_name": "aces", "parameters": {"enhancement_level": "moderate"}},
                    {"model_name": "audiocraft", "parameters": {"mastering_preset": "balanced"}}
                ]
            },
            "creative_enhancement": {
                "name": "Creative Enhancement",
                "description": "Creative processing with style transfer",
                "steps": [
                    {"model_name": "music_lm", "parameters": {"analysis_depth": "full"}},
                    {"model_name": "jukebox", "parameters": {"style_strength": 0.7}},
                    {"model_name": "melody_rnn", "parameters": {"variation_level": "medium"}},
                    {"model_name": "aces", "parameters": {"enhancement_level": "high"}}
                ]
            },
            "generation_from_scratch": {
                "name": "Generate from Scratch",
                "description": "Complete music generation workflow",
                "steps": [
                    {"model_name": "music_gen", "parameters": {"length": 180, "style": "auto"}},
                    {"model_name": "melody_rnn", "parameters": {"enhance_melody": True}},
                    {"model_name": "tepand_diff_rhythm", "parameters": {"rhythm_enhancement": True}},
                    {"model_name": "stable_audio", "parameters": {"quality": "high"}},
                    {"model_name": "aces", "parameters": {"final_master": True}}
                ]
            },
            "vocal_enhancement": {
                "name": "Vocal Enhancement",
                "description": "Specialized vocal processing",
                "steps": [
                    {"model_name": "music_lm", "parameters": {"focus": "vocals"}},
                    {"model_name": "suni", "parameters": {"vocal_enhancement": True}},
                    {"model_name": "aces", "parameters": {"vocal_clarity": True}}
                ]
            }
        }
    
    async def create_auto_workflow(
        self, 
        audio_analysis: Dict[str, Any], 
        user_preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create an optimized workflow based on audio analysis"""
        
        genre = audio_analysis.get("genre", "unknown")
        quality_metrics = audio_analysis.get("quality_metrics", {})
        duration = audio_analysis.get("duration", 120)
        
        workflow_steps = []
        
        # Always start with analysis
        workflow_steps.append({
            "model_name": "music_lm",
            "parameters": {"analysis_depth": "full"}
        })
        
        # Determine processing based on audio characteristics
        noise_level = quality_metrics.get("noise_level", 0.1)
        if noise_level > 0.3:
            workflow_steps.append({
                "model_name": "suni",
                "parameters": {"noise_reduction": True}
            })
        
        # Genre-specific processing
        if genre in ["electronic", "edm", "techno"]:
            workflow_steps.extend([
                {"model_name": "tepand_diff_rhythm", "parameters": {"electronic_enhancement": True}},
                {"model_name": "stable_audio", "parameters": {"electronic_mastering": True}}
            ])
        elif genre in ["classical", "orchestral"]:
            workflow_steps.extend([
                {"model_name": "beethoven_ai", "parameters": {"classical_enhancement": True}},
                {"model_name": "aces", "parameters": {"orchestral_mastering": True}}
            ])
        elif genre in ["rock", "metal"]:
            workflow_steps.extend([
                {"model_name": "audiocraft", "parameters": {"rock_processing": True}},
                {"model_name": "aces", "parameters": {"rock_mastering": True}}
            ])
        else:
            # Default processing
            workflow_steps.extend([
                {"model_name": "audiocraft", "parameters": {"general_enhancement": True}},
                {"model_name": "aces", "parameters": {"balanced_mastering": True}}
            ])
        
        # User preference adjustments
        creativity_level = user_preferences.get("creativity", "medium")
        if creativity_level == "high":
            workflow_steps.insert(-1, {
                "model_name": "jukebox",
                "parameters": {"creative_processing": True}
            })
        
        return {
            "type": "auto",
            "name": f"Auto-optimized for {genre}",
            "description": f"Automatically optimized workflow for {genre} music",
            "steps": workflow_steps,
            "estimated_duration": len(workflow_steps) * 30,  # 30 seconds per step estimate
            "optimization_factors": {
                "genre": genre,
                "quality_metrics": quality_metrics,
                "user_preferences": user_preferences
            }
        }
    
    async def create_custom_workflow(self, custom_steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create workflow from user-defined steps"""
        
        return {
            "type": "custom",
            "name": "Custom Workflow",
            "description": "User-defined processing workflow",
            "steps": custom_steps,
            "estimated_duration": len(custom_steps) * 45,  # Longer estimate for custom
            "optimization_factors": {"user_defined": True}
        }
    
    async def get_preset_workflow(self, preset_name: str) -> Dict[str, Any]:
        """Get a predefined workflow preset"""
        
        preset = self.preset_workflows.get(preset_name)
        if not preset:
            # Return default preset
            preset = self.preset_workflows["standard_mastering"]
        
        return {
            "type": "preset",
            "name": preset["name"],
            "description": preset["description"],
            "steps": preset["steps"],
            "estimated_duration": len(preset["steps"]) * 35,
            "optimization_factors": {"preset": preset_name}
        }
    
    async def optimize_for_resources(
        self, 
        workflow_plan: Dict[str, Any], 
        resource_availability: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimize workflow based on current resource availability"""
        
        optimized_steps = []
        
        for step in workflow_plan["steps"]:
            model_name = step["model_name"]
            model_resources = resource_availability.get(model_name, {})
            
            if model_resources.get("available", True):
                # Model is available, keep the step
                optimized_steps.append(step)
            else:
                # Model unavailable, try to find alternative
                logger.warning("Model unavailable, skipping step", model=model_name)
                # In a real implementation, we'd find suitable alternatives
        
        workflow_plan["steps"] = optimized_steps
        workflow_plan["resource_optimized"] = True
        
        return workflow_plan
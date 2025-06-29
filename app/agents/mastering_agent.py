from typing import Dict, Any, List, Optional
import asyncio
import logging
from datetime import datetime
import uuid
import os

from app.agents.base_agent import BaseAgent, AgentStatus, TaskType, AgentTask
from app.utils.audio_processing import AudioProcessor, MasteringProcessor
from app.utils.file_utils import FileManager
from app.core.config import settings

logger = logging.getLogger(__name__)

class MasteringAgent(BaseAgent):
    """Agent specialized in audio mastering"""
    
    def __init__(self, agent_id: str = None):
        super().__init__(agent_id)
        self.capabilities = [
            "audio_mastering",
            "loudness_normalization", 
            "dynamic_range_control",
            "eq_processing",
            "stereo_enhancement",
            "limiting",
            "compression"
        ]
        self.mastering_presets = {
            "balanced": {
                "target_loudness": -14.0,
                "compression_ratio": 4.0,
                "compression_threshold": -20.0,
                "eq_bass_gain": 0.0,
                "eq_treble_gain": 0.0,
                "stereo_width": 1.0
            },
            "loud": {
                "target_loudness": -9.0,
                "compression_ratio": 6.0,
                "compression_threshold": -18.0,
                "eq_bass_gain": 1.0,
                "eq_treble_gain": 2.0,
                "stereo_width": 1.1
            },
            "dynamic": {
                "target_loudness": -18.0,
                "compression_ratio": 2.0,
                "compression_threshold": -24.0,
                "eq_bass_gain": 0.0,
                "eq_treble_gain": 0.0,
                "stereo_width": 1.0
            },
            "vintage": {
                "target_loudness": -16.0,
                "compression_ratio": 3.0,
                "compression_threshold": -22.0,
                "eq_bass_gain": 2.0,
                "eq_treble_gain": -1.0,
                "stereo_width": 0.9
            }
        }
        
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process mastering request"""
        self.update_status(AgentStatus.THINKING, "Analyzing mastering request")
        
        # Validate request
        validation = await self.validate_request(request)
        if not validation["valid"]:
            return {
                "success": False,
                "errors": validation["errors"],
                "agent_id": self.agent_id
            }
        
        try:
            # Create task
            task = AgentTask(TaskType.MASTERING, request)
            self.current_task = task
            task.start()
            
            self.update_status(AgentStatus.PLANNING, "Creating mastering plan")
            
            # Prepare execution plan
            execution_plan = await self.prepare_execution_plan(request)
            
            self.update_status(AgentStatus.EXECUTING, "Mastering audio")
            
            # Execute mastering
            results = await self._execute_mastering(request, task)
            
            # Complete task
            task.complete(results)
            self.add_task_to_history(task.to_dict())
            
            self.update_status(AgentStatus.COMPLETED, "Mastering completed")
            self.current_task = None
            
            return results
            
        except Exception as e:
            logger.error(f"Error in mastering: {e}")
            if self.current_task:
                self.current_task.fail(str(e))
            
            self.update_status(AgentStatus.FAILED, f"Mastering failed: {str(e)}")
            
            return {
                "success": False,
                "error": str(e),
                "agent_id": self.agent_id
            }
    
    async def _execute_mastering(self, request: Dict[str, Any], task: AgentTask) -> Dict[str, Any]:
        """Execute the actual mastering process"""
        input_file_path = request.get("input_file_path")
        preset = request.get("preset", "balanced")
        target_loudness = request.get("target_loudness")
        enhance_bass = request.get("enhance_bass", False)
        enhance_treble = request.get("enhance_treble", False)
        stereo_width = request.get("stereo_width", 1.0)
        
        # Update progress
        task.update_progress(10)
        
        # Validate input file
        if not os.path.exists(input_file_path):
            raise Exception(f"Input file not found: {input_file_path}")
        
        # Analyze input audio
        self.update_status(AgentStatus.EXECUTING, "Analyzing input audio")
        input_metadata = AudioProcessor.extract_metadata(input_file_path)
        task.update_progress(20)
        
        # Generate output file path
        output_filename = f"mastered_{uuid.uuid4()}.wav"
        output_path = os.path.join(settings.UPLOAD_PATH, output_filename)
        
        # Get mastering parameters
        mastering_params = self._get_mastering_parameters(
            preset, target_loudness, enhance_bass, enhance_treble, stereo_width
        )
        
        task.update_progress(30)
        
        # Apply mastering chain
        self.update_status(AgentStatus.EXECUTING, "Applying mastering chain")
        mastering_results = MasteringProcessor.master_audio(
            input_file_path,
            output_path,
            preset=preset,
            target_loudness=mastering_params["target_loudness"],
            enhance_bass=enhance_bass,
            enhance_treble=enhance_treble,
            stereo_width=stereo_width
        )
        
        task.update_progress(80)
        
        if not mastering_results["success"]:
            raise Exception(f"Mastering failed: {mastering_results.get('error', 'Unknown error')}")
        
        # Analyze output audio
        self.update_status(AgentStatus.EXECUTING, "Analyzing mastered audio")
        output_metadata = AudioProcessor.extract_metadata(output_path)
        task.update_progress(90)
        
        # Calculate quality improvements
        quality_analysis = self._analyze_mastering_quality(
            input_metadata, output_metadata, mastering_params
        )
        
        task.update_progress(100)
        
        return {
            "success": True,
            "output_file_path": output_path,
            "filename": output_filename,
            "input_metadata": input_metadata,
            "output_metadata": output_metadata,
            "mastering_parameters": mastering_params,
            "quality_analysis": quality_analysis,
            "processing_results": mastering_results,
            "agent_id": self.agent_id,
            "processing_time": task.get_execution_time()
        }
    
    def _get_mastering_parameters(
        self, preset: str, target_loudness: float = None,
        enhance_bass: bool = False, enhance_treble: bool = False,
        stereo_width: float = 1.0
    ) -> Dict[str, Any]:
        """Get mastering parameters based on preset and overrides"""
        
        # Start with preset parameters
        if preset in self.mastering_presets:
            params = self.mastering_presets[preset].copy()
        else:
            params = self.mastering_presets["balanced"].copy()
        
        # Apply overrides
        if target_loudness is not None:
            params["target_loudness"] = target_loudness
        
        if enhance_bass:
            params["eq_bass_gain"] = max(params["eq_bass_gain"], 2.0)
        
        if enhance_treble:
            params["eq_treble_gain"] = max(params["eq_treble_gain"], 1.5)
        
        params["stereo_width"] = stereo_width
        
        return params
    
    def _analyze_mastering_quality(
        self, input_metadata: Dict[str, Any], 
        output_metadata: Dict[str, Any],
        mastering_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze the quality of mastering results"""
        
        analysis = {
            "loudness_improvement": 0.0,
            "dynamic_range_change": 0.0,
            "peak_reduction": 0.0,
            "overall_quality_score": 0.0,
            "recommendations": []
        }
        
        # Loudness analysis
        input_loudness = input_metadata.get("loudness_lufs", -23.0)
        output_loudness = output_metadata.get("loudness_lufs", -23.0)
        target_loudness = mastering_params.get("target_loudness", -14.0)
        
        analysis["loudness_improvement"] = output_loudness - input_loudness
        
        # Check if target loudness was achieved
        loudness_accuracy = 1 - abs(target_loudness - output_loudness) / abs(target_loudness)
        
        # Dynamic range analysis
        input_dr = input_metadata.get("dynamic_range", 0.0)
        output_dr = output_metadata.get("dynamic_range", 0.0)
        analysis["dynamic_range_change"] = output_dr - input_dr
        
        # Peak analysis
        input_peak = input_metadata.get("peak_db", 0.0)
        output_peak = output_metadata.get("peak_db", 0.0)
        analysis["peak_reduction"] = input_peak - output_peak
        
        # Calculate overall quality score
        quality_score = 0.7  # Base score
        
        # Loudness accuracy bonus
        quality_score += loudness_accuracy * 0.2
        
        # Dynamic range preservation bonus
        if analysis["dynamic_range_change"] > -3.0:  # Less than 3dB reduction
            quality_score += 0.1
        
        # Peak control bonus
        if -1.0 <= output_peak <= 0.0:  # Good peak level
            quality_score += 0.1
        
        analysis["overall_quality_score"] = min(1.0, max(0.0, quality_score))
        
        # Generate recommendations
        if output_loudness < target_loudness - 2.0:
            analysis["recommendations"].append("Consider increasing compression ratio for higher loudness")
        
        if analysis["dynamic_range_change"] < -5.0:
            analysis["recommendations"].append("Dynamic range significantly reduced - consider gentler compression")
        
        if output_peak > -0.1:
            analysis["recommendations"].append("Peak levels very high - consider more limiting")
        
        return analysis
    
    def get_capabilities(self) -> List[str]:
        """Get agent capabilities"""
        return self.capabilities
    
    def estimate_cost(self, request: Dict[str, Any]) -> float:
        """Estimate processing cost"""
        base_cost = 0.05  # $0.05 base cost
        
        # Cost based on file duration (estimated from file size)
        file_size = request.get("file_size", 0)
        duration_estimate = file_size / (44100 * 2 * 2)  # Rough estimate for 16-bit stereo
        duration_cost = duration_estimate * 0.005  # $0.005 per second
        
        # Complexity multiplier
        complexity_multiplier = 1.0
        
        preset = request.get("preset", "balanced")
        if preset == "loud":
            complexity_multiplier += 0.3
        
        if request.get("enhance_bass") or request.get("enhance_treble"):
            complexity_multiplier += 0.2
        
        total_cost = (base_cost + duration_cost) * complexity_multiplier
        return round(total_cost, 2)
    
    def estimate_time(self, request: Dict[str, Any]) -> int:
        """Estimate processing time in seconds"""
        base_time = 15  # 15 seconds base time
        
        # Time based on file size
        file_size = request.get("file_size", 0)
        duration_estimate = file_size / (44100 * 2 * 2)
        processing_time = duration_estimate * 1.5  # 1.5 seconds per second of audio
        
        # Additional time for complex processing
        if request.get("enhance_bass") or request.get("enhance_treble"):
            processing_time += 10
        
        return int(base_time + processing_time)
    
    async def validate_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Validate mastering request"""
        validation = await super().validate_request(request)
        
        if not validation["valid"]:
            return validation
        
        # Check input file path
        input_file_path = request.get("input_file_path")
        if not input_file_path:
            validation["valid"] = False
            validation["errors"].append("Input file path is required")
        elif not os.path.exists(input_file_path):
            validation["valid"] = False
            validation["errors"].append("Input file does not exist")
        
        # Check target loudness
        target_loudness = request.get("target_loudness")
        if target_loudness is not None:
            if not isinstance(target_loudness, (int, float)) or target_loudness < -30 or target_loudness > 0:
                validation["valid"] = False
                validation["errors"].append("Target loudness must be between -30 and 0 LUFS")
        
        # Check stereo width
        stereo_width = request.get("stereo_width", 1.0)
        if not isinstance(stereo_width, (int, float)) or stereo_width < 0 or stereo_width > 2:
            validation["valid"] = False
            validation["errors"].append("Stereo width must be between 0.0 and 2.0")
        
        # Check preset
        preset = request.get("preset", "balanced")
        if preset not in self.mastering_presets:
            validation["warnings"].append(f"Unknown preset '{preset}', using 'balanced'")
        
        return validation
    
    async def prepare_execution_plan(self, request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prepare execution plan for mastering"""
        plan = []
        
        plan.append({
            "step": 1,
            "type": "analysis",
            "description": "Analyze input audio characteristics",
            "estimated_time": 10
        })
        
        plan.append({
            "step": 2,
            "type": "eq_processing",
            "description": "Apply EQ adjustments",
            "estimated_time": 15
        })
        
        plan.append({
            "step": 3,
            "type": "compression",
            "description": "Apply dynamic range compression",
            "estimated_time": 20
        })
        
        plan.append({
            "step": 4,
            "type": "stereo_processing",
            "description": "Process stereo width and imaging",
            "estimated_time": 10
        })
        
        plan.append({
            "step": 5,
            "type": "limiting",
            "description": "Apply final limiting and loudness normalization",
            "estimated_time": 15
        })
        
        plan.append({
            "step": 6,
            "type": "quality_analysis",
            "description": "Analyze mastered audio quality",
            "estimated_time": 10
        })
        
        return plan
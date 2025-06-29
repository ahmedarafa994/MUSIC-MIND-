from typing import Dict, Any, List, Optional
import asyncio
import logging
from datetime import datetime
import uuid
import os

from app.agents.base_agent import BaseAgent, AgentStatus, TaskType, AgentTask
from app.utils.audio_processing import AudioProcessor
from app.utils.file_utils import FileManager
from app.core.config import settings
from app.services.landr_mastering import LANDRMasteringService
from app.services.matchering_mastering import MatcheringMasteringService

logger = logging.getLogger(__name__)

class MasteringAgent(BaseAgent):
    """Agent specialized in audio mastering, supporting multiple services."""
    
    def __init__(
        self,
        agent_id: str = None,
        landr_service: Optional[LANDRMasteringService] = None,
        matchering_service: Optional[MatcheringMasteringService] = None
    ):
        super().__init__(agent_id)
        self.landr_service = landr_service or LANDRMasteringService()
        self.matchering_service = matchering_service or MatcheringMasteringService()

        self.capabilities = [
            "audio_mastering",
            "loudness_normalization", 
            "dynamic_range_control",
            "eq_processing",
            "stereo_enhancement",
            "limiting",
            "compression",
            "landr_integration",
            "matchering_integration" # Added capability
        ]
        # Presets are now service-specific or handled by the services themselves.
        self.mastering_presets = { # This could store paths to reference files for Matchering
            "matchering_example_reference": "path/to/default_reference.wav"
        }
        
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process mastering request using specified service."""
        self.update_status(AgentStatus.THINKING, "Analyzing mastering request")
        
        mastering_service_type = request.get("mastering_service_type", "landr").lower()
        request["mastering_service_type"] = mastering_service_type # Ensure it's in the request for later use

        validation = await self.validate_request(request)
        if not validation["valid"]:
            return {
                "success": False,
                "errors": validation["errors"],
                "warnings": validation.get("warnings", []),
                "agent_id": self.agent_id
            }
        
        try:
            task = AgentTask(TaskType.MASTERING, request)
            self.current_task = task
            task.start()
            
            self.update_status(AgentStatus.PLANNING, f"Creating {mastering_service_type} mastering plan")
            
            # Pass the full request to prepare_execution_plan
            execution_plan = await self.prepare_execution_plan(request)
            task.set_metadata({"execution_plan": execution_plan}) # Store plan in task

            self.update_status(AgentStatus.EXECUTING, f"Mastering audio with {mastering_service_type}")
            
            # Pass the full request to _execute_mastering
            results = await self._execute_mastering(request, task)
            
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
        """Execute mastering using the specified service (LANDR or Matchering)."""
        input_file_path = request.get("input_file_path")
        mastering_service_type = request.get("mastering_service_type", "landr")

        task.update_progress(10, "Validating input file for mastering")
        if not input_file_path or not os.path.exists(input_file_path):
            raise Exception(f"Input file not found or not provided: {input_file_path}")

        filename = os.path.basename(input_file_path)
        self.update_status(AgentStatus.EXECUTING, f"Analyzing input audio for {mastering_service_type}")
        input_metadata = AudioProcessor.extract_metadata(input_file_path)
        task.update_progress(20, "Input audio analyzed")

        output_path = None
        output_filename = None
        service_specific_results = {}
        mastering_parameters_used = {}

        if mastering_service_type == "landr":
            mastering_options = request.get("mastering_options", {}) # LANDR specific options
            mastering_parameters_used = mastering_options

            if not self.landr_service.is_configured():
                raise Exception("LANDR Mastering Service is not configured (API key may be missing).")

            self.update_status(AgentStatus.EXECUTING, "Processing with LANDR")
            task.update_progress(30, "Starting LANDR workflow")
            try:
                with open(input_file_path, "rb") as audio_file:
                    landr_result = await self.landr_service.master_audio_complete_workflow(
                        audio_file=audio_file, filename=filename, mastering_options=mastering_options
                    )
            except Exception as e:
                logger.error(f"LANDR mastering workflow error: {e}", exc_info=True)
                raise Exception(f"LANDR mastering workflow failed: {str(e)}")

            task.update_progress(80, "LANDR processing finished")
            if not landr_result or not landr_result.get("success"):
                err_msg = landr_result.get("error", "Unknown LANDR API error")
                raise Exception(f"LANDR mastering failed: {err_msg}")

            output_filename = f"mastered_landr_{uuid.uuid4()}_{filename}"
            output_path = os.path.join(settings.UPLOAD_PATH, output_filename)
            os.makedirs(settings.UPLOAD_PATH, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(landr_result["audio_data"])

            mastering_parameters_used = landr_result.get("options_used", mastering_options)
            service_specific_results = {
                "job_id": landr_result.get("job_id"),
                "file_size": landr_result.get("file_size"),
                "content_type": landr_result.get("content_type"),
            }

        elif mastering_service_type == "matchering":
            reference_file_path = request.get("reference_file_path")
            matchering_output_options = request.get("matchering_output_options") # e.g., [{"type": "pcm16", "suffix": "_16bit.wav"}]
            mastering_parameters_used = {
                "reference_file_path": reference_file_path,
                "output_options": matchering_output_options
            }

            if not reference_file_path or not os.path.exists(reference_file_path):
                raise Exception(f"Reference file not found for Matchering: {reference_file_path}")

            self.update_status(AgentStatus.EXECUTING, "Processing with Matchering")
            task.update_progress(30, "Starting Matchering workflow")

            # Matchering's process is synchronous, run in executor if it's too slow for async context
            # For now, direct call as per service design
            matchering_result = await self.matchering_service.process_audio(
                target_file_path=input_file_path,
                reference_file_path=reference_file_path,
                output_dir=settings.UPLOAD_PATH,
                output_filename_prefix=f"mastered_matchering_{uuid.uuid4()}_",
                output_formats=matchering_output_options
            )
            task.update_progress(80, "Matchering processing finished")

            if not matchering_result or not matchering_result.get("success"):
                err_msg = matchering_result.get("error", "Unknown Matchering error")
                raise Exception(f"Matchering failed: {err_msg}")

            # Matchering can produce multiple files. We'll pick the first one as primary output for now.
            # The full list is in matchering_result["processed_files"]
            if not matchering_result["processed_files"]:
                raise Exception("Matchering processing succeeded but returned no files.")

            primary_output_file_info = matchering_result["processed_files"][0]
            output_path = primary_output_file_info["path"]
            output_filename = primary_output_file_info["filename"]
            service_specific_results = {"processed_files": matchering_result["processed_files"]}

        else:
            raise Exception(f"Unsupported mastering service type: {mastering_service_type}")

        if not output_path or not os.path.exists(output_path):
             raise Exception(f"Mastering completed but output file not found at: {output_path}")

        self.update_status(AgentStatus.EXECUTING, f"Analyzing mastered audio from {mastering_service_type}")
        output_metadata = AudioProcessor.extract_metadata(output_path)
        task.update_progress(90, "Mastered audio analyzed")

        quality_analysis = self._analyze_mastering_quality(
            input_metadata, output_metadata, mastering_parameters_used
        )
        task.update_progress(100, "Mastering quality analyzed")

        return {
            "success": True,
            "output_file_path": output_path,
            "filename": output_filename,
            "input_metadata": input_metadata,
            "output_metadata": output_metadata,
            "mastering_service_used": mastering_service_type,
            "mastering_parameters": mastering_parameters_used,
            "quality_analysis": quality_analysis,
            "processing_results": { # Common structure
                **service_specific_results, # service specific stuff like job_id or multiple files
                "final_loudness_lufs": output_metadata.get("loudness_lufs"),
                "final_peak_db": output_metadata.get("peak_db"),
            },
            "agent_id": self.agent_id,
            "processing_time": task.get_execution_time()
        }

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
        """Estimate processing cost based on the selected mastering service."""
        mastering_service_type = request.get("mastering_service_type", "landr")

        if mastering_service_type == "landr":
            # Placeholder: LANDR pricing might be per track or subscription-based.
            cost_per_track = 1.00  # Example: $1.00 per track via LANDR
            mastering_options = request.get("mastering_options", {})
            if mastering_options.get("intensity") == "high": # Fictional example
                cost_per_track += 0.50
            return round(cost_per_track, 2)

        elif mastering_service_type == "matchering":
            # Matchering is local, so direct cost is $0, but there's compute cost.
            # For simplicity, we can assign a nominal very low cost or $0.
            return 0.05 # Example: $0.05 representing compute resources
        
        else:
            logger.warning(f"Cost estimation for unsupported service: {mastering_service_type}")
            return 0.0

    def estimate_time(self, request: Dict[str, Any]) -> int:
        """Estimate processing time in seconds based on the selected service."""
        mastering_service_type = request.get("mastering_service_type", "landr")
        file_size_bytes = request.get("file_size", 0)
        file_size_mb = file_size_bytes / (1024 * 1024)

        if mastering_service_type == "landr":
            base_api_time = 30  # seconds for overhead
            transfer_time = file_size_mb * request.get("seconds_per_mb_transfer_estimate", 10) # Faster estimate
            landr_processing_time = request.get("estimated_landr_processing_time", 300) # From plan or default
            total_estimated_time = base_api_time + transfer_time + landr_processing_time
            return int(total_estimated_time)

        elif mastering_service_type == "matchering":
            # Matchering time depends on CPU and audio length/complexity.
            # Rough estimate: base time + time proportional to audio length (derived from size)
            base_local_processing_time = 15 # seconds for setup, analysis

            # Duration estimate: assuming 44.1kHz, 16-bit stereo (4 bytes/sample pair)
            # This is a very rough estimate. Actual duration if available would be better.
            bytes_per_second_approx = 44100 * 2 * 2
            duration_estimate_seconds = file_size_bytes / bytes_per_second_approx if bytes_per_second_approx > 0 else 0

            # Assume processing time is, e.g., 0.5x to 2x of audio duration for Matchering
            processing_factor = request.get("matchering_processing_factor", 1.0)
            matchering_processing_time = duration_estimate_seconds * processing_factor

            total_estimated_time = base_local_processing_time + matchering_processing_time
             # Use estimated_matchering_processing_time from plan if available and more accurate
            total_estimated_time = request.get("estimated_matchering_processing_time", total_estimated_time)
            return int(total_estimated_time)

        else:
            logger.warning(f"Time estimation for unsupported service: {mastering_service_type}")
            return 60 # Default fallback

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
        
        mastering_service_type = request.get("mastering_service_type", "landr")

        if mastering_service_type == "landr":
            mastering_options = request.get("mastering_options")
            if mastering_options is not None and not isinstance(mastering_options, dict):
                validation["valid"] = False
                validation["errors"].append("LANDR mastering_options must be a dictionary.")
            # Further LANDR-specific validation can be added here if needed
            # (e.g., checking values for 'intensity', 'style')
            # For now, LANDR service handles defaults and validation of its own options.

        elif mastering_service_type == "matchering":
            reference_file_path = request.get("reference_file_path")
            if not reference_file_path:
                validation["valid"] = False
                validation["errors"].append("Reference file path is required for Matchering.")
            elif not os.path.exists(reference_file_path):
                validation["valid"] = False
                validation["errors"].append(f"Reference file for Matchering not found at: {reference_file_path}")

            matchering_output_options = request.get("matchering_output_options")
            if matchering_output_options is not None:
                if not isinstance(matchering_output_options, list):
                    validation["valid"] = False
                    validation["errors"].append("Matchering output_options must be a list of dictionaries.")
                else:
                    for opt in matchering_output_options:
                        if not isinstance(opt, dict):
                            validation["valid"] = False
                            validation["errors"].append("Each item in Matchering output_options must be a dictionary.")
                            break
                        if not opt.get("type") or not opt.get("filename_suffix"):
                            validation["valid"] = False
                            validation["errors"].append("Each Matchering output option must have 'type' and 'filename_suffix'.")
                            break
        else:
            validation["valid"] = False
            validation["errors"].append(f"Unsupported mastering_service_type: {mastering_service_type}. Supported types: 'landr', 'matchering'.")

        return validation
    
    async def prepare_execution_plan(self, request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prepare execution plan based on the selected mastering service."""
        mastering_service_type = request.get("mastering_service_type", "landr")
        plan = []

        if mastering_service_type == "landr":
            plan = [
                {
                    "step": 1,
                    "type": "validation",
                    "description": "Validate input file and LANDR mastering options",
                    "estimated_time": 5
                },
                {
                    "step": 2,
                    "type": "landr_upload",
                    "description": "Upload audio to LANDR for mastering",
                    "estimated_time": request.get("estimated_upload_time", 60)
                },
                {
                    "step": 3,
                    "type": "landr_processing",
                    "description": "Wait for LANDR mastering to complete",
                    "estimated_time": request.get("estimated_landr_processing_time", 300)
                },
                {
                    "step": 4,
                    "type": "landr_download",
                    "description": "Download mastered audio from LANDR",
                    "estimated_time": request.get("estimated_download_time", 60)
                },
                {
                    "step": 5,
                    "type": "audio_analysis",
                    "description": "Analyze input and mastered audio characteristics",
                    "estimated_time": 15
                },
                {
                    "step": 6,
                    "type": "quality_assessment",
                    "description": "Assess LANDR mastering quality",
                    "estimated_time": 10
                }
            ]
        elif mastering_service_type == "matchering":
            plan = [
                {
                    "step": 1,
                    "type": "validation",
                    "description": "Validate input file, reference file, and Matchering options",
                    "estimated_time": 5
                },
                {
                    "step": 2,
                    "type": "matchering_processing",
                    "description": "Process audio with Matchering using target and reference",
                     # Estimate based on file size, could be passed in request
                    "estimated_time": request.get("estimated_matchering_processing_time", 120)
                },
                {
                    "step": 3,
                    "type": "audio_analysis",
                    "description": "Analyze input and mastered audio characteristics",
                    "estimated_time": 15
                },
                {
                    "step": 4,
                    "type": "quality_assessment",
                    "description": "Assess Matchering mastering quality",
                    "estimated_time": 10
                }
            ]
        else: # Should not happen if validate_request is called first
            logger.warning(f"Execution plan requested for unsupported service type: {mastering_service_type}")
            plan.append({
                "step": 1, "type": "error", "description": "Unsupported mastering service type.", "estimated_time": 1
            })

        return plan
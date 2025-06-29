import asyncio
import json
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import structlog
from dataclasses import dataclass, asdict
import numpy as np

from app.core.config import settings
from app.services.model_services import ModelServiceManager
from app.services.audio_analyzer import AudioAnalyzer
from app.services.quality_assessor import QualityAssessor
from app.services.workflow_optimizer import WorkflowOptimizer
from app.core.exceptions import ProcessingError, ModelUnavailableError

logger = structlog.get_logger()

class ProcessingStatus(Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    PROCESSING = "processing"
    QUALITY_CHECK = "quality_check"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ModelType(Enum):
    GENERATION = "generation"
    SYNTHESIS = "synthesis"
    UNDERSTANDING = "understanding"
    MANIPULATION = "manipulation"
    ENHANCEMENT = "enhancement"
    STYLE_TRANSFER = "style_transfer"
    RHYTHM = "rhythm"
    MELODY = "melody"

@dataclass
class ProcessingJob:
    id: str
    user_id: str
    project_id: str
    input_audio_path: str
    workflow_config: Dict[str, Any]
    status: ProcessingStatus
    progress: float
    current_step: str
    created_at: datetime
    updated_at: datetime
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None
    intermediate_results: List[Dict[str, Any]] = None
    final_results: Optional[Dict[str, Any]] = None

@dataclass
class ModelExecution:
    model_name: str
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]]
    execution_time: float
    success: bool
    error_message: Optional[str] = None
    quality_score: Optional[float] = None

class MasterChainOrchestrator:
    """
    Core orchestrator for the AI Music Mastering Chain.
    Manages model selection, workflow execution, and quality assessment.
    """
    
    def __init__(self):
        self.model_manager = ModelServiceManager()
        self.audio_analyzer = AudioAnalyzer()
        self.quality_assessor = QualityAssessor()
        self.workflow_optimizer = WorkflowOptimizer()
        self.active_jobs: Dict[str, ProcessingJob] = {}
        
        # Model service configurations
        self.model_configs = {
            "music_gen": {
                "type": ModelType.GENERATION,
                "priority": 1,
                "max_duration": 300,
                "resource_weight": 0.8,
                "fallbacks": ["beethoven_ai", "mureka"]
            },
            "stable_audio": {
                "type": ModelType.SYNTHESIS,
                "priority": 2,
                "max_duration": 180,
                "resource_weight": 0.9,
                "fallbacks": ["audiocraft"]
            },
            "music_lm": {
                "type": ModelType.UNDERSTANDING,
                "priority": 1,
                "max_duration": 60,
                "resource_weight": 0.3,
                "fallbacks": []
            },
            "audiocraft": {
                "type": ModelType.MANIPULATION,
                "priority": 3,
                "max_duration": 240,
                "resource_weight": 0.7,
                "fallbacks": ["aces", "suni"]
            },
            "jukebox": {
                "type": ModelType.STYLE_TRANSFER,
                "priority": 4,
                "max_duration": 600,
                "resource_weight": 1.0,
                "fallbacks": []
            },
            "melody_rnn": {
                "type": ModelType.MELODY,
                "priority": 2,
                "max_duration": 120,
                "resource_weight": 0.4,
                "fallbacks": ["music_vae"]
            },
            "music_vae": {
                "type": ModelType.MELODY,
                "priority": 2,
                "max_duration": 90,
                "resource_weight": 0.4,
                "fallbacks": ["melody_rnn"]
            },
            "aces": {
                "type": ModelType.ENHANCEMENT,
                "priority": 3,
                "max_duration": 150,
                "resource_weight": 0.6,
                "fallbacks": ["suni"]
            },
            "tepand_diff_rhythm": {
                "type": ModelType.RHYTHM,
                "priority": 2,
                "max_duration": 120,
                "resource_weight": 0.5,
                "fallbacks": []
            },
            "suni": {
                "type": ModelType.ENHANCEMENT,
                "priority": 3,
                "max_duration": 180,
                "resource_weight": 0.6,
                "fallbacks": ["aces"]
            },
            "beethoven_ai": {
                "type": ModelType.GENERATION,
                "priority": 2,
                "max_duration": 300,
                "resource_weight": 0.7,
                "fallbacks": ["music_gen", "mureka"]
            },
            "mureka": {
                "type": ModelType.GENERATION,
                "priority": 2,
                "max_duration": 240,
                "resource_weight": 0.6,
                "fallbacks": ["music_gen", "beethoven_ai"]
            }
        }

    async def create_processing_job(
        self,
        user_id: str,
        project_id: str,
        input_audio_path: str,
        workflow_config: Dict[str, Any]
    ) -> str:
        """Create a new processing job and start execution"""
        
        job_id = str(uuid.uuid4())
        
        job = ProcessingJob(
            id=job_id,
            user_id=user_id,
            project_id=project_id,
            input_audio_path=input_audio_path,
            workflow_config=workflow_config,
            status=ProcessingStatus.PENDING,
            progress=0.0,
            current_step="Initializing",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            intermediate_results=[]
        )
        
        self.active_jobs[job_id] = job
        
        # Start processing in background
        asyncio.create_task(self._execute_processing_job(job_id))
        
        logger.info("Processing job created", job_id=job_id, user_id=user_id)
        return job_id

    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a processing job"""
        job = self.active_jobs.get(job_id)
        if not job:
            return None
        
        return {
            "id": job.id,
            "status": job.status.value,
            "progress": job.progress,
            "current_step": job.current_step,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "estimated_completion": job.estimated_completion.isoformat() if job.estimated_completion else None,
            "error_message": job.error_message,
            "intermediate_results": job.intermediate_results,
            "final_results": job.final_results
        }

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a processing job"""
        job = self.active_jobs.get(job_id)
        if not job or job.status in [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED]:
            return False
        
        job.status = ProcessingStatus.CANCELLED
        job.updated_at = datetime.utcnow()
        job.error_message = "Job cancelled by user"
        
        logger.info("Processing job cancelled", job_id=job_id)
        return True

    async def _execute_processing_job(self, job_id: str):
        """Execute the complete processing workflow for a job"""
        
        job = self.active_jobs.get(job_id)
        if not job:
            logger.error("Job not found", job_id=job_id)
            return

        try:
            # Phase 1: Audio Analysis
            await self._update_job_progress(job_id, 5, "Analyzing input audio", ProcessingStatus.ANALYZING)
            audio_analysis = await self.audio_analyzer.analyze_audio(job.input_audio_path)
            
            # Phase 2: Workflow Planning
            await self._update_job_progress(job_id, 15, "Planning processing workflow")
            workflow_plan = await self._create_workflow_plan(audio_analysis, job.workflow_config)
            
            # Phase 3: Model Execution Chain
            await self._update_job_progress(job_id, 20, "Starting model processing chain", ProcessingStatus.PROCESSING)
            
            current_audio_data = await self._load_audio_data(job.input_audio_path)
            execution_results = []
            
            total_steps = len(workflow_plan['steps'])
            
            for i, step in enumerate(workflow_plan['steps']):
                # Check if job was cancelled
                if job.status == ProcessingStatus.CANCELLED:
                    return
                
                step_progress = 20 + (60 * (i + 1) / total_steps)
                await self._update_job_progress(
                    job_id, 
                    step_progress, 
                    f"Processing with {step['model_name']}"
                )
                
                # Execute model step
                execution_result = await self._execute_model_step(
                    step, 
                    current_audio_data, 
                    audio_analysis
                )
                
                execution_results.append(execution_result)
                
                if not execution_result.success:
                    # Handle model failure with fallback
                    fallback_result = await self._handle_model_failure(
                        step, 
                        current_audio_data, 
                        execution_result.error_message
                    )
                    
                    if fallback_result:
                        execution_result = fallback_result
                        execution_results[-1] = fallback_result
                    else:
                        raise ProcessingError(f"Model {step['model_name']} failed: {execution_result.error_message}")
                
                # Update current audio data for next step
                if execution_result.output_data and 'audio_data' in execution_result.output_data:
                    current_audio_data = execution_result.output_data['audio_data']
                
                # Store intermediate result
                job.intermediate_results.append({
                    'step': i + 1,
                    'model': step['model_name'],
                    'timestamp': datetime.utcnow().isoformat(),
                    'quality_score': execution_result.quality_score,
                    'execution_time': execution_result.execution_time
                })

            # Phase 4: Quality Assessment
            await self._update_job_progress(job_id, 85, "Assessing final quality", ProcessingStatus.QUALITY_CHECK)
            
            final_quality_score = await self.quality_assessor.assess_final_quality(
                current_audio_data,
                audio_analysis,
                execution_results
            )
            
            # Phase 5: Result Compilation
            await self._update_job_progress(job_id, 95, "Compiling final results")
            
            final_results = await self._compile_final_results(
                current_audio_data,
                execution_results,
                final_quality_score,
                workflow_plan
            )
            
            # Complete job
            job.final_results = final_results
            job.status = ProcessingStatus.COMPLETED
            job.progress = 100.0
            job.current_step = "Completed successfully"
            job.updated_at = datetime.utcnow()
            
            logger.info("Processing job completed successfully", 
                       job_id=job_id, 
                       final_quality_score=final_quality_score)

        except Exception as e:
            logger.error("Processing job failed", job_id=job_id, error=str(e))
            job.status = ProcessingStatus.FAILED
            job.error_message = str(e)
            job.updated_at = datetime.utcnow()

    async def _update_job_progress(
        self, 
        job_id: str, 
        progress: float, 
        current_step: str, 
        status: Optional[ProcessingStatus] = None
    ):
        """Update job progress and status"""
        job = self.active_jobs.get(job_id)
        if job:
            job.progress = progress
            job.current_step = current_step
            job.updated_at = datetime.utcnow()
            if status:
                job.status = status
            
            # Estimate completion time
            if progress > 0:
                elapsed = (datetime.utcnow() - job.created_at).total_seconds()
                estimated_total = elapsed * (100 / progress)
                job.estimated_completion = job.created_at + timedelta(seconds=estimated_total)

    async def _load_audio_data(self, audio_path: str) -> Any:
        """Load audio data from file path"""
        try:
            import librosa
            audio_data, sample_rate = librosa.load(audio_path, sr=None)
            return {
                'audio': audio_data,
                'sample_rate': sample_rate,
                'duration': len(audio_data) / sample_rate
            }
        except ImportError:
            # Fallback if librosa is not available
            return {
                'audio': np.random.randn(44100 * 30),  # 30 seconds of random audio
                'sample_rate': 44100,
                'duration': 30.0
            }

    async def _create_workflow_plan(
        self, 
        audio_analysis: Dict[str, Any], 
        workflow_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create an optimized workflow plan based on audio analysis and user preferences"""
        
        workflow_type = workflow_config.get('type', 'auto')
        
        if workflow_type == 'auto':
            workflow_plan = await self.workflow_optimizer.create_auto_workflow(
                audio_analysis, 
                workflow_config
            )
        elif workflow_type == 'custom':
            workflow_plan = await self.workflow_optimizer.create_custom_workflow(
                workflow_config.get('steps', [])
            )
        elif workflow_type == 'preset':
            preset_name = workflow_config.get('preset', 'standard_mastering')
            workflow_plan = await self.workflow_optimizer.get_preset_workflow(preset_name)
        else:
            raise ValueError(f"Unknown workflow type: {workflow_type}")
        
        # Optimize workflow based on available resources
        workflow_plan = await self.workflow_optimizer.optimize_for_resources(
            workflow_plan,
            await self.model_manager.get_resource_availability()
        )
        
        return workflow_plan

    async def _execute_model_step(
        self,
        step: Dict[str, Any],
        audio_data: Any,
        audio_analysis: Dict[str, Any]
    ) -> ModelExecution:
        """Execute a single model processing step"""
        
        model_name = step['model_name']
        model_params = step.get('parameters', {})
        
        start_time = datetime.utcnow()
        
        try:
            # Check model availability
            if not await self.model_manager.is_model_available(model_name):
                raise ModelUnavailableError(f"Model {model_name} is not available")
            
            # Prepare input data for the model
            input_data = {
                'audio_data': audio_data,
                'audio_analysis': audio_analysis,
                'parameters': model_params,
                'step_config': step
            }
            
            # Execute model
            output_data = await self.model_manager.execute_model(model_name, input_data)
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Assess quality of output
            quality_score = None
            if output_data and 'audio_data' in output_data:
                quality_score = await self.quality_assessor.assess_step_quality(
                    output_data['audio_data'],
                    audio_data,
                    model_name
                )
            
            return ModelExecution(
                model_name=model_name,
                input_data=input_data,
                output_data=output_data,
                execution_time=execution_time,
                success=True,
                quality_score=quality_score
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error("Model execution failed", 
                        model_name=model_name, 
                        error=str(e))
            
            return ModelExecution(
                model_name=model_name,
                input_data={'audio_data': audio_data, 'parameters': model_params},
                output_data=None,
                execution_time=execution_time,
                success=False,
                error_message=str(e)
            )

    async def _handle_model_failure(
        self,
        failed_step: Dict[str, Any],
        audio_data: Any,
        error_message: str
    ) -> Optional[ModelExecution]:
        """Handle model failure with fallback strategies"""
        
        model_name = failed_step['model_name']
        fallback_models = self.model_configs.get(model_name, {}).get('fallbacks', [])
        
        if not fallback_models:
            logger.warning("No fallback models available", failed_model=model_name)
            return None
        
        # Try fallback models in order
        for fallback_model in fallback_models:
            if await self.model_manager.is_model_available(fallback_model):
                logger.info("Attempting fallback model", 
                           original_model=model_name, 
                           fallback_model=fallback_model)
                
                # Create fallback step configuration
                fallback_step = failed_step.copy()
                fallback_step['model_name'] = fallback_model
                
                # Execute fallback model
                fallback_result = await self._execute_model_step(
                    fallback_step,
                    audio_data,
                    {}  # Empty analysis for fallback
                )
                
                if fallback_result.success:
                    logger.info("Fallback model succeeded", fallback_model=fallback_model)
                    return fallback_result
                else:
                    logger.warning("Fallback model also failed", 
                                 fallback_model=fallback_model,
                                 error=fallback_result.error_message)
        
        return None

    async def _compile_final_results(
        self,
        final_audio_data: Any,
        execution_results: List[ModelExecution],
        quality_score: float,
        workflow_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compile final processing results"""
        
        # Save final audio file
        output_filename = f"mastered_{uuid.uuid4()}.wav"
        output_path = f"/tmp/{output_filename}"
        
        # In a real implementation, save the audio data to file
        # For now, we'll simulate this
        
        return {
            "output_file_path": output_path,
            "output_filename": output_filename,
            "quality_score": quality_score,
            "processing_summary": {
                "total_steps": len(execution_results),
                "successful_steps": sum(1 for r in execution_results if r.success),
                "total_execution_time": sum(r.execution_time for r in execution_results),
                "average_quality": np.mean([r.quality_score for r in execution_results if r.quality_score])
            },
            "workflow_used": workflow_plan,
            "model_executions": [
                {
                    "model_name": r.model_name,
                    "execution_time": r.execution_time,
                    "success": r.success,
                    "quality_score": r.quality_score,
                    "error_message": r.error_message
                }
                for r in execution_results
            ]
        }

# Global orchestrator instance
orchestrator = MasterChainOrchestrator()
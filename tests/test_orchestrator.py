import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from app.services.master_chain_orchestrator import (
    MasterChainOrchestrator, 
    ProcessingJob, 
    ProcessingStatus,
    ModelExecution
)

@pytest.fixture
def orchestrator():
    return MasterChainOrchestrator()

@pytest.fixture
def sample_job():
    return ProcessingJob(
        id="test-job-123",
        user_id="user-123",
        project_id="project-123",
        input_audio_path="/tmp/test.wav",
        workflow_config={"type": "auto"},
        status=ProcessingStatus.PENDING,
        progress=0.0,
        current_step="Initializing",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        intermediate_results=[]
    )

class TestMasterChainOrchestrator:
    
    @pytest.mark.asyncio
    async def test_create_processing_job(self, orchestrator):
        """Test processing job creation"""
        with patch.object(orchestrator, '_execute_processing_job') as mock_execute:
            job_id = await orchestrator.create_processing_job(
                user_id="user-123",
                project_id="project-123",
                input_audio_path="/tmp/test.wav",
                workflow_config={"type": "auto"}
            )
            
            assert job_id in orchestrator.active_jobs
            job = orchestrator.active_jobs[job_id]
            assert job.user_id == "user-123"
            assert job.status == ProcessingStatus.PENDING
            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_job_status(self, orchestrator, sample_job):
        """Test job status retrieval"""
        orchestrator.active_jobs[sample_job.id] = sample_job
        
        status = await orchestrator.get_job_status(sample_job.id)
        
        assert status is not None
        assert status["id"] == sample_job.id
        assert status["status"] == ProcessingStatus.PENDING.value
        assert status["progress"] == 0.0

    @pytest.mark.asyncio
    async def test_cancel_job(self, orchestrator, sample_job):
        """Test job cancellation"""
        orchestrator.active_jobs[sample_job.id] = sample_job
        
        result = await orchestrator.cancel_job(sample_job.id)
        
        assert result is True
        assert sample_job.status == ProcessingStatus.CANCELLED
        assert sample_job.error_message == "Job cancelled by user"

    @pytest.mark.asyncio
    async def test_cancel_completed_job(self, orchestrator, sample_job):
        """Test cancelling already completed job"""
        sample_job.status = ProcessingStatus.COMPLETED
        orchestrator.active_jobs[sample_job.id] = sample_job
        
        result = await orchestrator.cancel_job(sample_job.id)
        
        assert result is False

    @pytest.mark.asyncio
    async def test_update_job_progress(self, orchestrator, sample_job):
        """Test job progress updates"""
        orchestrator.active_jobs[sample_job.id] = sample_job
        
        await orchestrator._update_job_progress(
            sample_job.id, 
            50.0, 
            "Processing audio", 
            ProcessingStatus.PROCESSING
        )
        
        assert sample_job.progress == 50.0
        assert sample_job.current_step == "Processing audio"
        assert sample_job.status == ProcessingStatus.PROCESSING
        assert sample_job.estimated_completion is not None

    @pytest.mark.asyncio
    async def test_load_audio_data(self, orchestrator):
        """Test audio data loading"""
        with patch('librosa.load') as mock_librosa:
            mock_librosa.return_value = ([1, 2, 3, 4], 44100)
            
            audio_data = await orchestrator._load_audio_data("/tmp/test.wav")
            
            assert audio_data["sample_rate"] == 44100
            assert audio_data["duration"] == len([1, 2, 3, 4]) / 44100
            assert "audio" in audio_data

    @pytest.mark.asyncio
    async def test_load_audio_data_fallback(self, orchestrator):
        """Test audio data loading fallback when librosa unavailable"""
        with patch('librosa.load', side_effect=ImportError()):
            audio_data = await orchestrator._load_audio_data("/tmp/test.wav")
            
            assert audio_data["sample_rate"] == 44100
            assert audio_data["duration"] == 30.0
            assert len(audio_data["audio"]) == 44100 * 30

    @pytest.mark.asyncio
    async def test_execute_model_step_success(self, orchestrator):
        """Test successful model step execution"""
        step = {
            "model_name": "test_model",
            "parameters": {"param1": "value1"}
        }
        audio_data = {"audio": [1, 2, 3], "sample_rate": 44100}
        audio_analysis = {"genre": "electronic"}
        
        with patch.object(orchestrator.model_manager, 'is_model_available', return_value=True):
            with patch.object(orchestrator.model_manager, 'execute_model') as mock_execute:
                mock_execute.return_value = {"audio_data": {"processed": True}}
                
                with patch.object(orchestrator.quality_assessor, 'assess_step_quality', return_value=0.85):
                    result = await orchestrator._execute_model_step(
                        step, audio_data, audio_analysis
                    )
                    
                    assert result.success is True
                    assert result.model_name == "test_model"
                    assert result.quality_score == 0.85
                    assert result.output_data == {"audio_data": {"processed": True}}

    @pytest.mark.asyncio
    async def test_execute_model_step_failure(self, orchestrator):
        """Test model step execution failure"""
        step = {
            "model_name": "test_model",
            "parameters": {"param1": "value1"}
        }
        audio_data = {"audio": [1, 2, 3], "sample_rate": 44100}
        audio_analysis = {"genre": "electronic"}
        
        with patch.object(orchestrator.model_manager, 'is_model_available', return_value=True):
            with patch.object(orchestrator.model_manager, 'execute_model', side_effect=Exception("Model failed")):
                result = await orchestrator._execute_model_step(
                    step, audio_data, audio_analysis
                )
                
                assert result.success is False
                assert result.error_message == "Model failed"
                assert result.output_data is None

    @pytest.mark.asyncio
    async def test_handle_model_failure_with_fallback(self, orchestrator):
        """Test model failure handling with successful fallback"""
        failed_step = {"model_name": "primary_model"}
        audio_data = {"audio": [1, 2, 3]}
        
        # Configure fallbacks
        orchestrator.model_configs["primary_model"] = {
            "fallbacks": ["fallback_model"]
        }
        
        with patch.object(orchestrator.model_manager, 'is_model_available', return_value=True):
            with patch.object(orchestrator, '_execute_model_step') as mock_execute:
                mock_execute.return_value = ModelExecution(
                    model_name="fallback_model",
                    input_data={},
                    output_data={"success": True},
                    execution_time=10.0,
                    success=True
                )
                
                result = await orchestrator._handle_model_failure(
                    failed_step, audio_data, "Original error"
                )
                
                assert result is not None
                assert result.success is True
                assert result.model_name == "fallback_model"

    @pytest.mark.asyncio
    async def test_handle_model_failure_no_fallbacks(self, orchestrator):
        """Test model failure handling with no fallbacks available"""
        failed_step = {"model_name": "primary_model"}
        audio_data = {"audio": [1, 2, 3]}
        
        # No fallbacks configured
        orchestrator.model_configs["primary_model"] = {
            "fallbacks": []
        }
        
        result = await orchestrator._handle_model_failure(
            failed_step, audio_data, "Original error"
        )
        
        assert result is None

    @pytest.mark.asyncio
    async def test_compile_final_results(self, orchestrator):
        """Test final results compilation"""
        final_audio_data = {"audio": [1, 2, 3, 4, 5], "sample_rate": 44100}
        execution_results = [
            ModelExecution("model1", {}, {}, 10.0, True, quality_score=0.8),
            ModelExecution("model2", {}, {}, 15.0, True, quality_score=0.9)
        ]
        quality_score = 0.85
        workflow_plan = {"name": "test_workflow", "steps": []}
        
        with patch('uuid.uuid4', return_value="test-uuid"):
            results = await orchestrator._compile_final_results(
                final_audio_data, execution_results, quality_score, workflow_plan
            )
            
            assert results["quality_score"] == 0.85
            assert results["output_filename"] == "mastered_test-uuid.wav"
            assert results["processing_summary"]["total_steps"] == 2
            assert results["processing_summary"]["successful_steps"] == 2
            assert len(results["model_executions"]) == 2

if __name__ == "__main__":
    pytest.main([__file__])
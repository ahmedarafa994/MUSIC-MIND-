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

logger = logging.getLogger(__name__)

class MusicGenerationAgent(BaseAgent):
    """Agent specialized in AI music generation"""
    
    def __init__(self, agent_id: str = None):
        super().__init__(agent_id)
        self.capabilities = [
            "music_generation",
            "style_transfer",
            "melody_creation",
            "harmony_generation",
            "rhythm_creation"
        ]
        self.supported_genres = [
            "pop", "rock", "jazz", "classical", "electronic", 
            "hip-hop", "country", "blues", "folk", "ambient"
        ]
        self.supported_moods = [
            "happy", "sad", "energetic", "calm", "mysterious",
            "romantic", "aggressive", "peaceful", "dramatic", "uplifting"
        ]
        
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process music generation request"""
        self.update_status(AgentStatus.THINKING, "Analyzing generation request")
        
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
            task = AgentTask(TaskType.GENERATION, request)
            self.current_task = task
            task.start()
            
            self.update_status(AgentStatus.PLANNING, "Creating generation plan")
            
            # Prepare execution plan
            execution_plan = await self.prepare_execution_plan(request)
            
            self.update_status(AgentStatus.EXECUTING, "Generating music")
            
            # Execute generation
            results = await self._execute_generation(request, task)
            
            # Complete task
            task.complete(results)
            self.add_task_to_history(task.to_dict())
            
            self.update_status(AgentStatus.COMPLETED, "Generation completed")
            self.current_task = None
            
            return results
            
        except Exception as e:
            logger.error(f"Error in music generation: {e}")
            if self.current_task:
                self.current_task.fail(str(e))
            
            self.update_status(AgentStatus.FAILED, f"Generation failed: {str(e)}")
            
            return {
                "success": False,
                "error": str(e),
                "agent_id": self.agent_id
            }
    
    async def _execute_generation(self, request: Dict[str, Any], task: AgentTask) -> Dict[str, Any]:
        """Execute the actual music generation"""
        prompt = request.get("prompt", "")
        genre = request.get("genre", "pop")
        mood = request.get("mood", "happy")
        tempo = request.get("tempo", 120)
        duration = request.get("duration", 30)
        key = request.get("key", "C")
        instruments = request.get("instruments", ["piano", "guitar"])
        
        # Update progress
        task.update_progress(10)
        
        # Simulate generation process (in real implementation, this would call AI models)
        await asyncio.sleep(1)  # Simulate processing time
        task.update_progress(30)
        
        # Generate audio file path
        output_filename = f"generated_{uuid.uuid4()}.wav"
        output_path = os.path.join(settings.UPLOAD_PATH, output_filename)
        
        # Simulate audio generation
        success = await self._simulate_audio_generation(
            output_path, duration, tempo, key, genre, mood
        )
        
        task.update_progress(70)
        
        if not success:
            raise Exception("Failed to generate audio")
        
        # Analyze generated audio
        metadata = AudioProcessor.extract_metadata(output_path)
        task.update_progress(90)
        
        # Calculate quality score
        quality_score = self._calculate_generation_quality(request, metadata)
        
        task.update_progress(100)
        
        return {
            "success": True,
            "output_file_path": output_path,
            "filename": output_filename,
            "metadata": metadata,
            "quality_score": quality_score,
            "generation_parameters": {
                "prompt": prompt,
                "genre": genre,
                "mood": mood,
                "tempo": tempo,
                "duration": duration,
                "key": key,
                "instruments": instruments
            },
            "agent_id": self.agent_id,
            "processing_time": task.get_execution_time()
        }
    
    async def _simulate_audio_generation(
        self, output_path: str, duration: int, tempo: int, 
        key: str, genre: str, mood: str
    ) -> bool:
        """Simulate audio generation (replace with actual AI model calls)"""
        try:
            import numpy as np
            import soundfile as sf
            
            # Generate simple sine wave as placeholder
            sample_rate = 44100
            t = np.linspace(0, duration, int(sample_rate * duration))
            
            # Create a simple melody based on parameters
            base_freq = self._key_to_frequency(key)
            
            # Generate multiple harmonics
            audio = np.zeros_like(t)
            for i, harmonic in enumerate([1, 0.5, 0.25, 0.125]):
                freq = base_freq * (i + 1)
                audio += harmonic * np.sin(2 * np.pi * freq * t)
            
            # Apply tempo-based modulation
            tempo_factor = tempo / 120.0
            modulation = np.sin(2 * np.pi * tempo_factor * t)
            audio = audio * (0.8 + 0.2 * modulation)
            
            # Normalize
            audio = audio / np.max(np.abs(audio)) * 0.8
            
            # Save audio
            sf.write(output_path, audio, sample_rate)
            return True
            
        except Exception as e:
            logger.error(f"Error in audio generation simulation: {e}")
            return False
    
    def _key_to_frequency(self, key: str) -> float:
        """Convert musical key to base frequency"""
        key_frequencies = {
            'C': 261.63, 'C#': 277.18, 'D': 293.66, 'D#': 311.13,
            'E': 329.63, 'F': 349.23, 'F#': 369.99, 'G': 392.00,
            'G#': 415.30, 'A': 440.00, 'A#': 466.16, 'B': 493.88
        }
        return key_frequencies.get(key, 261.63)
    
    def _calculate_generation_quality(self, request: Dict[str, Any], metadata: Dict[str, Any]) -> float:
        """Calculate quality score for generated music"""
        score = 0.8  # Base score
        
        # Check if duration matches request
        requested_duration = request.get("duration", 30)
        actual_duration = metadata.get("duration", 0)
        
        if actual_duration > 0:
            duration_accuracy = 1 - abs(requested_duration - actual_duration) / requested_duration
            score += duration_accuracy * 0.1
        
        # Check tempo accuracy
        requested_tempo = request.get("tempo", 120)
        detected_tempo = metadata.get("tempo", 120)
        
        if detected_tempo > 0:
            tempo_accuracy = 1 - abs(requested_tempo - detected_tempo) / requested_tempo
            score += tempo_accuracy * 0.1
        
        return min(1.0, max(0.0, score))
    
    def get_capabilities(self) -> List[str]:
        """Get agent capabilities"""
        return self.capabilities
    
    def estimate_cost(self, request: Dict[str, Any]) -> float:
        """Estimate processing cost"""
        base_cost = 0.10  # $0.10 base cost
        
        duration = request.get("duration", 30)
        complexity_multiplier = 1.0
        
        # Adjust cost based on duration
        duration_cost = duration * 0.01  # $0.01 per second
        
        # Adjust based on complexity
        instruments = request.get("instruments", [])
        if len(instruments) > 3:
            complexity_multiplier += 0.5
        
        genre = request.get("genre", "pop")
        if genre in ["classical", "jazz"]:
            complexity_multiplier += 0.3
        
        total_cost = (base_cost + duration_cost) * complexity_multiplier
        return round(total_cost, 2)
    
    def estimate_time(self, request: Dict[str, Any]) -> int:
        """Estimate processing time in seconds"""
        base_time = 30  # 30 seconds base time
        
        duration = request.get("duration", 30)
        duration_time = duration * 2  # 2 seconds processing per second of audio
        
        complexity_time = 0
        instruments = request.get("instruments", [])
        complexity_time += len(instruments) * 10
        
        return base_time + duration_time + complexity_time
    
    async def validate_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Validate music generation request"""
        validation = await super().validate_request(request)
        
        if not validation["valid"]:
            return validation
        
        # Check prompt
        prompt = request.get("prompt", "")
        if not prompt or len(prompt.strip()) < 10:
            validation["valid"] = False
            validation["errors"].append("Prompt must be at least 10 characters long")
        
        # Check duration
        duration = request.get("duration", 30)
        if not isinstance(duration, (int, float)) or duration < 10 or duration > 300:
            validation["valid"] = False
            validation["errors"].append("Duration must be between 10 and 300 seconds")
        
        # Check tempo
        tempo = request.get("tempo")
        if tempo is not None:
            if not isinstance(tempo, (int, float)) or tempo < 60 or tempo > 200:
                validation["valid"] = False
                validation["errors"].append("Tempo must be between 60 and 200 BPM")
        
        # Check genre
        genre = request.get("genre")
        if genre and genre not in self.supported_genres:
            validation["warnings"].append(f"Genre '{genre}' may not be fully supported")
        
        # Check mood
        mood = request.get("mood")
        if mood and mood not in self.supported_moods:
            validation["warnings"].append(f"Mood '{mood}' may not be fully supported")
        
        return validation
    
    async def prepare_execution_plan(self, request: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prepare execution plan for music generation"""
        plan = []
        
        plan.append({
            "step": 1,
            "type": "analysis",
            "description": "Analyze prompt and parameters",
            "estimated_time": 10
        })
        
        plan.append({
            "step": 2,
            "type": "composition",
            "description": "Generate musical composition",
            "estimated_time": 60
        })
        
        plan.append({
            "step": 3,
            "type": "synthesis",
            "description": "Synthesize audio",
            "estimated_time": 30
        })
        
        plan.append({
            "step": 4,
            "type": "post_processing",
            "description": "Apply post-processing and effects",
            "estimated_time": 20
        })
        
        plan.append({
            "step": 5,
            "type": "quality_check",
            "description": "Analyze and validate output",
            "estimated_time": 10
        })
        
        return plan
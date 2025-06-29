from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import asyncio
import numpy as np
import logging

app = FastAPI(title="Music Gen Service")
logger = logging.getLogger(__name__)

class ProcessRequest(BaseModel):
    audio_data: Optional[Dict[str, Any]] = None
    parameters: Dict[str, Any] = {}
    step_config: Dict[str, Any] = {}

class ProcessResponse(BaseModel):
    audio_data: Dict[str, Any]
    metadata: Dict[str, Any]
    success: bool

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "model": "music_gen"}

@app.get("/capabilities")
async def get_capabilities():
    """Get model capabilities"""
    return {
        "model_name": "music_gen",
        "type": "generation",
        "supported_formats": ["wav", "mp3"],
        "max_duration": 300,
        "parameters": {
            "length": {"type": "int", "min": 10, "max": 300, "default": 30},
            "style": {"type": "string", "options": ["auto", "classical", "electronic", "rock"], "default": "auto"},
            "tempo": {"type": "int", "min": 60, "max": 200, "default": 120}
        }
    }

@app.get("/resources")
async def get_resources():
    """Get current resource status"""
    return {
        "available": True,
        "gpu_memory": "8GB",
        "cpu_usage": 45,
        "queue_length": 0
    }

@app.post("/process", response_model=ProcessResponse)
async def process_audio(request: ProcessRequest):
    """Process audio with Music Gen model"""
    
    try:
        # Simulate processing time
        await asyncio.sleep(2)
        
        # Extract parameters
        length = request.parameters.get("length", 30)
        style = request.parameters.get("style", "auto")
        tempo = request.parameters.get("tempo", 120)
        
        # Simulate audio generation
        sample_rate = 44100
        duration = length
        audio_samples = np.random.randn(int(sample_rate * duration))
        
        # Apply basic tempo modulation
        t = np.linspace(0, duration, len(audio_samples))
        tempo_factor = tempo / 120.0
        modulation = np.sin(2 * np.pi * tempo_factor * t)
        audio_samples = audio_samples * (0.8 + 0.2 * modulation)
        
        # Normalize
        audio_samples = audio_samples / np.max(np.abs(audio_samples)) * 0.8
        
        return ProcessResponse(
            audio_data={
                "audio": audio_samples.tolist(),
                "sample_rate": sample_rate,
                "duration": duration
            },
            metadata={
                "model": "music_gen",
                "style": style,
                "tempo": tempo,
                "generated_length": length
            },
            success=True
        )
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
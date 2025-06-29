import httpx
import asyncio
from typing import Dict, Any, Optional, BinaryIO
from app.core.config import settings
import structlog

logger = structlog.get_logger()

class LANDRMasteringService:
    """Service for integrating with LANDR's professional mastering API"""
    
    def __init__(self):
        self.api_key = settings.LANDR_API_KEY
        self.base_url = "https://api.landr.com/v1"
        self.headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "landr-mastering.p.rapidapi.com",
            "Content-Type": "application/json"
        }
    
    async def upload_audio_for_mastering(
        self,
        audio_file: BinaryIO,
        filename: str,
        mastering_options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Upload audio file to LANDR for mastering"""
        try:
            # Default mastering options
            default_options = {
                "intensity": "medium",  # low, medium, high
                "style": "balanced",    # warm, balanced, open, punchy
                "loudness": -14,        # LUFS target loudness
                "stereo_width": "normal" # narrow, normal, wide
            }
            
            if mastering_options:
                default_options.update(mastering_options)
            
            # Prepare multipart form data
            files = {
                "audio": (filename, audio_file, "audio/wav")
            }
            
            data = {
                "options": default_options
            }
            
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.base_url}/master",
                    headers={k: v for k, v in self.headers.items() if k != "Content-Type"},
                    files=files,
                    data=data
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info("Audio uploaded to LANDR for mastering", 
                           filename=filename, 
                           job_id=result.get("job_id"))
                
                return {
                    "success": True,
                    "job_id": result.get("job_id"),
                    "status": result.get("status", "processing"),
                    "estimated_completion": result.get("estimated_completion"),
                    "options_used": default_options
                }
                
        except httpx.HTTPStatusError as e:
            logger.error("LANDR API error", 
                        status_code=e.response.status_code,
                        error=e.response.text)
            return {
                "success": False,
                "error": f"LANDR API error: {e.response.status_code}",
                "details": e.response.text
            }
        except Exception as e:
            logger.error("Failed to upload to LANDR", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    async def check_mastering_status(self, job_id: str) -> Dict[str, Any]:
        """Check the status of a mastering job"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/master/{job_id}/status",
                    headers=self.headers
                )
                
                response.raise_for_status()
                result = response.json()
                
                return {
                    "success": True,
                    "job_id": job_id,
                    "status": result.get("status"),
                    "progress": result.get("progress", 0),
                    "estimated_completion": result.get("estimated_completion"),
                    "download_url": result.get("download_url") if result.get("status") == "completed" else None
                }
                
        except httpx.HTTPStatusError as e:
            logger.error("Failed to check LANDR status", 
                        job_id=job_id,
                        status_code=e.response.status_code)
            return {
                "success": False,
                "error": f"Status check failed: {e.response.status_code}"
            }
        except Exception as e:
            logger.error("Failed to check LANDR status", job_id=job_id, error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    async def download_mastered_audio(self, job_id: str) -> Dict[str, Any]:
        """Download the mastered audio file"""
        try:
            # First check if the job is completed
            status_result = await self.check_mastering_status(job_id)
            
            if not status_result["success"]:
                return status_result
            
            if status_result["status"] != "completed":
                return {
                    "success": False,
                    "error": f"Job not completed yet. Status: {status_result['status']}"
                }
            
            download_url = status_result.get("download_url")
            if not download_url:
                return {
                    "success": False,
                    "error": "No download URL available"
                }
            
            # Download the mastered file
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.get(
                    download_url,
                    headers=self.headers
                )
                
                response.raise_for_status()
                
                return {
                    "success": True,
                    "job_id": job_id,
                    "audio_data": response.content,
                    "content_type": response.headers.get("content-type", "audio/wav"),
                    "file_size": len(response.content)
                }
                
        except Exception as e:
            logger.error("Failed to download mastered audio", job_id=job_id, error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_mastering_presets(self) -> Dict[str, Any]:
        """Get available mastering presets and options"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/presets",
                    headers=self.headers
                )
                
                response.raise_for_status()
                result = response.json()
                
                return {
                    "success": True,
                    "presets": result.get("presets", []),
                    "styles": result.get("styles", ["warm", "balanced", "open", "punchy"]),
                    "intensity_levels": result.get("intensity_levels", ["low", "medium", "high"]),
                    "loudness_range": result.get("loudness_range", {"min": -23, "max": -6})
                }
                
        except Exception as e:
            logger.error("Failed to get LANDR presets", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "presets": [],
                "styles": ["warm", "balanced", "open", "punchy"],
                "intensity_levels": ["low", "medium", "high"],
                "loudness_range": {"min": -23, "max": -6}
            }
    
    async def master_audio_complete_workflow(
        self,
        audio_file: BinaryIO,
        filename: str,
        mastering_options: Dict[str, Any] = None,
        max_wait_time: int = 600  # 10 minutes
    ) -> Dict[str, Any]:
        """Complete mastering workflow: upload, wait, and download"""
        try:
            # Step 1: Upload for mastering
            upload_result = await self.upload_audio_for_mastering(
                audio_file, filename, mastering_options
            )
            
            if not upload_result["success"]:
                return upload_result
            
            job_id = upload_result["job_id"]
            
            # Step 2: Wait for completion
            wait_time = 0
            check_interval = 30  # Check every 30 seconds
            
            while wait_time < max_wait_time:
                status_result = await self.check_mastering_status(job_id)
                
                if not status_result["success"]:
                    return status_result
                
                status = status_result["status"]
                
                if status == "completed":
                    break
                elif status == "failed":
                    return {
                        "success": False,
                        "error": "Mastering job failed",
                        "job_id": job_id
                    }
                
                # Wait before next check
                await asyncio.sleep(check_interval)
                wait_time += check_interval
                
                logger.info("Waiting for LANDR mastering completion", 
                           job_id=job_id, 
                           status=status,
                           progress=status_result.get("progress", 0))
            
            if wait_time >= max_wait_time:
                return {
                    "success": False,
                    "error": "Mastering timeout - job taking too long",
                    "job_id": job_id
                }
            
            # Step 3: Download mastered audio
            download_result = await self.download_mastered_audio(job_id)
            
            if download_result["success"]:
                logger.info("LANDR mastering completed successfully", 
                           job_id=job_id,
                           file_size=download_result["file_size"])
            
            return download_result
            
        except Exception as e:
            logger.error("LANDR complete workflow failed", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    def is_configured(self) -> bool:
        """Check if LANDR API is properly configured"""
        return bool(self.api_key)
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test the LANDR API connection"""
        try:
            presets_result = await self.get_mastering_presets()
            
            if presets_result["success"]:
                return {
                    "success": True,
                    "message": "LANDR API connection successful",
                    "service": "LANDR Mastering"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to connect to LANDR API",
                    "details": presets_result.get("error")
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"LANDR connection test failed: {str(e)}"
            }
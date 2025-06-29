import asyncio
from app.services.master_chain_orchestrator import MasterChainOrchestrator
from app.services.websocket_manager import websocket_manager
import structlog

logger = structlog.get_logger()

class EnhancedOrchestrator(MasterChainOrchestrator):
    """Enhanced orchestrator with real-time WebSocket updates"""
    
    async def _update_job_progress(
        self, 
        job_id: str, 
        progress: float, 
        current_step: str, 
        status = None
    ):
        """Update job progress and send WebSocket updates"""
        # Call parent method
        await super()._update_job_progress(job_id, progress, current_step, status)
        
        # Send WebSocket update
        job = self.active_jobs.get(job_id)
        if job:
            update_data = {
                "progress": progress,
                "current_step": current_step,
                "status": status.value if status else job.status.value,
                "estimated_completion": job.estimated_completion.isoformat() if job.estimated_completion else None
            }
            
            await websocket_manager.send_job_update(job_id, update_data)
            
            # Also send user notification for major milestones
            if progress in [25, 50, 75, 100] or status:
                notification = {
                    "title": f"Processing Update - {progress}%",
                    "message": current_step,
                    "job_id": job_id,
                    "progress": progress
                }
                await websocket_manager.send_user_notification(job.user_id, notification)

# Replace the global orchestrator
enhanced_orchestrator = EnhancedOrchestrator()
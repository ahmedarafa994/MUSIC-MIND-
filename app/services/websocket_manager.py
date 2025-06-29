import asyncio
import json
from typing import Dict, Set
from fastapi import WebSocket
import structlog

logger = structlog.get_logger()

class WebSocketManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.user_connections: Dict[str, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str, job_id: str = None):
        """Connect a WebSocket for a user and optionally a specific job"""
        await websocket.accept()
        
        # Add to user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)
        
        # Add to job connections if job_id provided
        if job_id:
            if job_id not in self.active_connections:
                self.active_connections[job_id] = set()
            self.active_connections[job_id].add(websocket)
        
        logger.info("WebSocket connected", user_id=user_id, job_id=job_id)
    
    def disconnect(self, websocket: WebSocket, user_id: str, job_id: str = None):
        """Disconnect a WebSocket"""
        # Remove from user connections
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Remove from job connections
        if job_id and job_id in self.active_connections:
            self.active_connections[job_id].discard(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
        
        logger.info("WebSocket disconnected", user_id=user_id, job_id=job_id)
    
    async def send_job_update(self, job_id: str, update_data: dict):
        """Send update to all connections listening to a specific job"""
        if job_id in self.active_connections:
            message = json.dumps({
                "type": "job_update",
                "job_id": job_id,
                "data": update_data
            })
            
            disconnected = set()
            for connection in self.active_connections[job_id]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.warning("Failed to send WebSocket message", error=str(e))
                    disconnected.add(connection)
            
            # Clean up disconnected connections
            for connection in disconnected:
                self.active_connections[job_id].discard(connection)
    
    async def send_user_notification(self, user_id: str, notification: dict):
        """Send notification to all connections for a user"""
        if user_id in self.user_connections:
            message = json.dumps({
                "type": "notification",
                "data": notification
            })
            
            disconnected = set()
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.warning("Failed to send WebSocket message", error=str(e))
                    disconnected.add(connection)
            
            # Clean up disconnected connections
            for connection in disconnected:
                self.user_connections[user_id].discard(connection)

# Global WebSocket manager
websocket_manager = WebSocketManager()
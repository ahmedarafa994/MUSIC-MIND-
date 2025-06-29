from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from app.core.security import get_current_user_from_token
from app.services.websocket_manager import websocket_manager
import structlog

router = APIRouter()
logger = structlog.get_logger()

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    job_id: str = Query(None),
    token: str = Query(...)
):
    """WebSocket endpoint for real-time updates"""
    
    try:
        # Validate token
        user = await get_current_user_from_token(token)
        if str(user.id) != user_id:
            await websocket.close(code=1008, reason="Unauthorized")
            return
        
        # Connect WebSocket
        await websocket_manager.connect(websocket, user_id, job_id)
        
        try:
            while True:
                # Keep connection alive and handle incoming messages
                data = await websocket.receive_text()
                # Handle any client messages if needed
                logger.debug("Received WebSocket message", user_id=user_id, data=data)
                
        except WebSocketDisconnect:
            websocket_manager.disconnect(websocket, user_id, job_id)
            logger.info("WebSocket disconnected", user_id=user_id)
            
    except Exception as e:
        logger.error("WebSocket error", user_id=user_id, error=str(e))
        await websocket.close(code=1011, reason="Internal error")
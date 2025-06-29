from fastapi import APIRouter
from datetime import datetime
import time
import os

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "uptime": time.time(),
        "environment": os.getenv("ENVIRONMENT", "development")
    }
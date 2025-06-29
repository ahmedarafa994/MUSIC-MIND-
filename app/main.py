from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
import time
import logging
import os
from typing import Dict, Any

# Import routers
from app.api.v1.api import api_router
from app.api.v1.health import router as health_router
from app.core.config import settings
from app.db.database import create_tables
from app.core.logging import setup_logging
from app.core.exceptions import (
    CustomHTTPException,
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)
from app.middleware.monitoring import MonitoringMiddleware, MetricsMiddleware

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer(auto_error=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting AI Music Mastering API...")
    
    # Initialize database
    try:
        create_tables()
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # Create upload directories
    os.makedirs(settings.UPLOAD_PATH, exist_ok=True)
    os.makedirs(settings.TEMP_PATH, exist_ok=True)
    logger.info("Upload directories created")
    
    # Initialize AI model clients
    try:
        from app.services.api_integration_manager import APIIntegrationManager
        api_manager = APIIntegrationManager()
        await api_manager.initialize_clients()
        logger.info("AI model clients initialized")
    except Exception as e:
        logger.warning(f"Some AI model clients failed to initialize: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Music Mastering API...")
    
    # Close Redis connections
    try:
        from app.core.redis_client import redis_client
        await redis_client.close()
        logger.info("Redis connections closed")
    except Exception as e:
        logger.error(f"Error closing Redis connections: {e}")

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered music generation and mastering platform",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# Add monitoring middleware
metrics_middleware = MetricsMiddleware(app)
app.add_middleware(MonitoringMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted host middleware
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

# Exception handlers
app.add_exception_handler(CustomHTTPException, http_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Mount static files
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(health_router, tags=["health"])
app.include_router(api_router, prefix=settings.API_V1_STR)

# Metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """Get application metrics"""
    return metrics_middleware.get_metrics()

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Music Mastering API",
        "version": "1.0.0",
        "docs": f"{settings.API_V1_STR}/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
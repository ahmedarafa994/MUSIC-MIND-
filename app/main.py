from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
import time
import structlog # Use structlog
import os
from typing import Dict, Any

# Import routers
from app.api.v1.api import api_router
from app.api.v1.health import router as health_router
from app.core.config import settings
from app.core.database import init_db, engine as async_engine
from app.core.logging import setup_logging
from app.core.exceptions import (
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)
# Assuming MonitoringMiddleware and MetricsMiddleware are correctly defined elsewhere
from app.middleware.monitoring import MonitoringMiddleware, MetricsMiddleware

# Setup logging FIRST
setup_logging()
logger = structlog.get_logger(__name__) # Use structlog


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting AI Music Mastering API...", project_name=settings.PROJECT_NAME, environment=settings.ENVIRONMENT)
    
    try:
        await init_db()
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error("Failed to initialize database during startup.", error=str(e), exc_info=True)
    
    if settings.STORAGE_PROVIDER == "local" and hasattr(settings, 'LOCAL_STORAGE_PATH'):
        os.makedirs(settings.LOCAL_STORAGE_PATH, exist_ok=True)
        logger.info(f"Local storage path ensured: {settings.LOCAL_STORAGE_PATH}")
    
    if hasattr(settings, 'TEMP_PATH'):
        os.makedirs(settings.TEMP_PATH, exist_ok=True)
        logger.info(f"Temp path ensured: {settings.TEMP_PATH}")
    
    yield
    
    logger.info("Shutting down AI Music Mastering API...")
    
    if async_engine:
        await async_engine.dispose()
        logger.info("Database engine connections closed.")

    logger.info("Application shutdown complete.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-powered music generation and mastering platform.",
    version=getattr(settings, 'APP_VERSION', '1.0.0'),
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.DEBUG else None,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

app.add_middleware(MonitoringMiddleware)

if settings.ALLOWED_HOSTS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).strip() for origin in settings.ALLOWED_HOSTS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

if settings.ENVIRONMENT == "production" and settings.ALLOWED_HOSTS != ["*"]:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# if os.path.exists("static") and settings.DEBUG:
#     app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(health_router, tags=["Health"])
app.include_router(api_router, prefix=settings.API_V1_STR)

if hasattr(MetricsMiddleware, "get_metrics"):
    metrics_middleware_instance = MetricsMiddleware(app)
    @app.get("/metrics", tags=["Monitoring"])
    async def get_metrics_endpoint():
        """Get application metrics (placeholder)."""
        return metrics_middleware_instance.get_metrics()

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint providing basic API information."""
    return {
        "project_name": settings.PROJECT_NAME,
        "version": getattr(settings, 'APP_VERSION', '1.0.0'),
        "environment": settings.ENVIRONMENT,
        "documentation_url": app.docs_url if settings.DEBUG else "disabled_in_production",
        "health_check_url": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn server directly for development...")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_config=None,
        use_colors=settings.DEBUG
    )
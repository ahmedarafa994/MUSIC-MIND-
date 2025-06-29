from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, audio
from app.api.v1 import audio_processing_api # Import the new router

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(audio.router, prefix="/audio", tags=["audio"]) # Existing audio file management
api_router.include_router(audio_processing_api.router, prefix="/audio", tags=["Audio Processing"]) # New mastering/processing routes
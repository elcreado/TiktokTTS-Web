from fastapi import APIRouter
from services.database import db_service
from datetime import datetime

router = APIRouter(prefix="/api", tags=["health"])

@router.get("/")
async def root():
    """Root endpoint"""
    return {"message": "TikTok Live TTS Bot API", "status": "running"}

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected" if db_service.client else "disconnected",
        "timestamp": datetime.now().isoformat()
    }
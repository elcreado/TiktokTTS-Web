"""
TikTok Live TTS Bot - Refactored Server
A modular FastAPI application for TikTok Live stream TTS integration.

This refactored version separates concerns into different modules:
- config/ - Configuration and settings
- models/ - Data models and schemas
- services/ - Business logic and external integrations
- routes/ - API endpoints
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# Import configuration
from config.settings import settings

# Import services
from services.database import db_service

# Import routes
from routes.health_routes import router as health_router
from routes.tiktok_routes import router as tiktok_router
from routes.chat_routes import router as chat_router
from routes.websocket_routes import router as websocket_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.APP_TITLE,
    version=settings.APP_VERSION,
    description="A modular TikTok Live TTS Bot with real-time WebSocket communication"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

# Include routers
app.include_router(health_router)
app.include_router(tiktok_router)
app.include_router(chat_router)
app.include_router(websocket_router)

@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup"""
    logger.info("🚀 Starting TikTok Live TTS Bot...")
    
    # Connect to database
    try:
        await db_service.connect()
        logger.info("✅ Database connected successfully")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise
    
    logger.info("🎯 TikTok Live TTS Bot started successfully!")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("🛑 Shutting down TikTok Live TTS Bot...")
    
    # Disconnect from database
    try:
        await db_service.disconnect()
        logger.info("✅ Database disconnected successfully")
    except Exception as e:
        logger.error(f"❌ Database disconnection failed: {e}")
    
    logger.info("👋 TikTok Live TTS Bot shutdown complete!")

# For debugging and development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True  # Enable hot reload for development
    )
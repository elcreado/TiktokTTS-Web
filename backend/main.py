#!/usr/bin/env python3
"""
TikTok Live TTS Bot - Main Entry Point
Main application entry point for production deployment.
This is the file that should be executed to run the application.

Usage:
    python main.py
    uvicorn main:app --host 0.0.0.0 --port 8001
"""

import uvicorn
from server import app
from config.settings import settings

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False  # Set to False for production
    )
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings:
    # Database configuration
    MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
    DATABASE_NAME = "tiktok_tts_bot"
    
    # TikTok configuration
    SING_API_KEY = os.environ.get('SING_API_KEY', '')
    
    # Server configuration
    HOST = "0.0.0.0"
    PORT = 8001
    
    # App configuration
    APP_TITLE = "TikTok Live TTS Bot"
    APP_VERSION = "1.0.0"
    
    # CORS configuration
    CORS_ORIGINS = ["*"]
    CORS_CREDENTIALS = True
    CORS_METHODS = ["*"]
    CORS_HEADERS = ["*"]

settings = Settings()
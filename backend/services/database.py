from motor.motor_asyncio import AsyncIOMotorClient
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.client = None
        self.db = None
    
    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(settings.MONGO_URL)
            self.db = self.client[settings.DATABASE_NAME]
            logger.info(f"Connected to MongoDB: {settings.DATABASE_NAME}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    async def save_chat_message(self, chat_message):
        """Save chat message to database"""
        try:
            await self.db.chat_messages.insert_one(chat_message.to_dict())
            logger.info(f"Saved chat message: {chat_message.user}: {chat_message.message}")
        except Exception as e:
            logger.error(f"Error saving message to database: {e}")
            
    async def get_chat_history(self, limit: int = 50):
        """Get chat history from database"""
        try:
            messages = await self.db.chat_messages.find().sort("timestamp", -1).limit(limit).to_list(length=limit)
            return messages
        except Exception as e:
            logger.error(f"Error fetching chat history: {e}")
            return []

# Global database instance
db_service = DatabaseService()
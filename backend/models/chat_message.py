from datetime import datetime
from typing import Optional
import uuid

class ChatMessage:
    def __init__(self, user: str, message: str, username_stream: str = ""):
        self.id = str(uuid.uuid4())
        self.user = user
        self.message = message
        self.timestamp = datetime.now()
        self.username_stream = username_stream
    
    def to_dict(self):
        return {
            "id": self.id,
            "user": self.user,
            "message": self.message,
            "timestamp": self.timestamp,
            "username_stream": self.username_stream
        }
    
    def to_websocket_dict(self, tts_enabled: bool = True):
        return {
            "type": "chat_message", 
            "user": self.user,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "tts_enabled": tts_enabled
        }
    
    @staticmethod
    def format_for_frontend(db_message: dict):
        """Format database message for frontend consumption"""
        return {
            "id": db_message.get("id", str(db_message["_id"])),
            "user": db_message["user"],
            "message": db_message["message"],
            "timestamp": db_message["timestamp"].isoformat() if hasattr(db_message["timestamp"], 'isoformat') else str(db_message["timestamp"])
        }
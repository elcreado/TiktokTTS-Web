from fastapi import APIRouter
from services.database import db_service
from models.chat_message import ChatMessage

router = APIRouter(prefix="/api", tags=["chat"])

@router.get("/chat-history")
async def get_chat_history(limit: int = 50):
    """Get chat message history"""
    messages = await db_service.get_chat_history(limit)
    
    # Convert messages for frontend
    formatted_messages = []
    for msg in messages:
        formatted_messages.append(ChatMessage.format_for_frontend(msg))
    
    return {"messages": formatted_messages}
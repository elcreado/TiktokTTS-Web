from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.websocket_manager import websocket_manager
from services.tiktok_service import tiktok_service
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await websocket_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Handle different message types
            if message_data.get("type") == "test_message":
                # Simulate a chat message for testing using the actual message content
                user = message_data.get("user", "TestUser")
                message = message_data.get("message", "Test message")
                await tiktok_service._handle_chat_message(user, message)
            
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket)
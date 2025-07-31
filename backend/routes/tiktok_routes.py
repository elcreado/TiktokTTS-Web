from fastapi import APIRouter, HTTPException
from services.tiktok_service import tiktok_service
from services.websocket_manager import websocket_manager
import json
from datetime import datetime

router = APIRouter(prefix="/api", tags=["tiktok"])

# Global TTS enabled state
tts_enabled = True
current_username = ""

@router.get("/status")
async def get_status():
    """Get current TikTok connection status"""
    return {
        "connected": tiktok_service.is_connected,
        "username": tiktok_service.username,
        "tts_enabled": tts_enabled,
        "timestamp": datetime.now().isoformat()
    }

@router.post("/connect")
async def connect_tiktok(data: dict):
    """Connect to TikTok Live stream"""
    username = data.get("username", "").replace("@", "")
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    
    global current_username
    current_username = username
    
    success = await tiktok_service.connect_to_stream(username)
    
    if success:
        return {"success": True, "message": f"Connected to @{username}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to connect to TikTok live")

@router.post("/disconnect")
async def disconnect_tiktok():
    """Disconnect from TikTok Live stream"""
    global current_username
    current_username = ""
    
    success = await tiktok_service.disconnect_from_stream()
    
    if success:
        return {"success": True, "message": "Disconnected from TikTok live"}
    else:
        raise HTTPException(status_code=500, detail="Failed to disconnect")

@router.post("/force-disconnect")
async def force_disconnect_tiktok():
    """Force disconnect from TikTok Live stream with aggressive cleanup"""
    global current_username
    current_username = ""
    
    try:
        success = await tiktok_service.force_disconnect()
        return {"success": True, "message": "Force disconnected from TikTok live"}
        
    except Exception as e:
        return {"success": True, "message": "Force disconnect attempted - state reset"}

@router.get("/connection-details")
async def get_connection_details():
    """Get detailed connection information for debugging"""
    return {
        "is_connected": tiktok_service.is_connected,
        "username": tiktok_service.username,
        "current_username": current_username,
        "has_client": tiktok_service.client is not None,
        "has_connection_task": tiktok_service.connection_task is not None,
        "task_done": tiktok_service.connection_task.done() if tiktok_service.connection_task else None,
        "tts_enabled": tts_enabled,
        "timestamp": datetime.now().isoformat()
    }

@router.post("/toggle-tts")
async def toggle_tts():
    """Toggle TTS on/off"""
    global tts_enabled
    tts_enabled = not tts_enabled
    
    await websocket_manager.broadcast_json({
        "type": "tts_status",
        "enabled": tts_enabled,
        "timestamp": datetime.now().isoformat()
    })
    
    return {"tts_enabled": tts_enabled}
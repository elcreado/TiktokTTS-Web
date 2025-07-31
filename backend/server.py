from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import json
import logging
from datetime import datetime
import uvicorn
from typing import List, Dict, Optional
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="TikTok Live TTS Bot", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(MONGO_URL)
db = client.tiktok_tts_bot

# Global variables for connection management
tiktok_connections: Dict[str, object] = {}
websocket_connections: List[WebSocket] = []
tts_enabled = True
current_username = ""

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error in broadcast: {e}")
                disconnected.append(connection)
        
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

# TikTok Live Integration
from TikTokLive import TikTokLiveClient
from TikTokLive.events import ConnectEvent, CommentEvent, DisconnectEvent, ViewerCountUpdateEvent

class TikTokLiveBot:
    def __init__(self):
        self.client = None
        self.is_connected = False
        self.username = ""
        self.connection_task = None
        
    async def connect_to_stream(self, username: str):
        try:
            # Clean username (remove @ if present)
            clean_username = username.replace("@", "").strip()
            
            # Initialize TikTok Live client
            self.client = TikTokLiveClient(
                unique_id=clean_username,
                debug=True,
                process_initial_data=False,
                enable_extended_gift_info=True,
                polling_interval_ms=1000
            )
            
            # Set up event handlers
            self.setup_event_handlers()
            
            # Start connection in background
            self.username = clean_username
            self.connection_task = asyncio.create_task(self.start_client())
            
            logger.info(f"Attempting to connect to @{clean_username}'s live stream")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to TikTok live: {e}")
            await manager.broadcast(json.dumps({
                "type": "connection_status",
                "connected": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }))
            return False
    
    def setup_event_handlers(self):
        """Set up all TikTok Live event handlers"""
        
        @self.client.on(ConnectEvent)
        async def on_connect(event: ConnectEvent):
            self.is_connected = True
            logger.info(f"Successfully connected to @{event.unique_id}'s live stream!")
            
            await manager.broadcast(json.dumps({
                "type": "connection_status",
                "connected": True,
                "username": event.unique_id,
                "timestamp": datetime.now().isoformat()
            }))
        
        @self.client.on(CommentEvent)
        async def on_comment(event: CommentEvent):
            user = event.user.nickname if event.user else "Usuario Anónimo"
            message = event.comment
            
            logger.info(f"💬 {user}: {message}")
            await self.handle_chat_message(user, message)
        
        @self.client.on(ViewerCountUpdateEvent)
        async def on_viewer_count_update(event: ViewerCountUpdateEvent):
            logger.info(f"👥 Espectadores: {event.viewer_count}")
            
            await manager.broadcast(json.dumps({
                "type": "viewer_count",
                "count": event.viewer_count,
                "timestamp": datetime.now().isoformat()
            }))
        
        @self.client.on(DisconnectEvent)
        async def on_disconnect(event: DisconnectEvent):
            self.is_connected = False
            logger.info("Disconnected from TikTok live stream")
            
            await manager.broadcast(json.dumps({
                "type": "connection_status",
                "connected": False,
                "username": "",
                "timestamp": datetime.now().isoformat()
            }))
    
    async def start_client(self):
        """Start the TikTok Live client"""
        try:
            if self.client:
                await self.client.connect()
        except Exception as e:
            logger.error(f"Error starting TikTok client: {e}")
            self.is_connected = False
            
            await manager.broadcast(json.dumps({
                "type": "connection_status",
                "connected": False,
                "error": f"No se pudo conectar al live de @{self.username}. Verifica que esté transmitiendo en vivo.",
                "timestamp": datetime.now().isoformat()
            }))
    
    async def disconnect_from_stream(self):
        try:
            if self.client:
                await self.client.disconnect()
            
            if self.connection_task:
                self.connection_task.cancel()
                try:
                    await self.connection_task
                except asyncio.CancelledError:
                    pass
            
            self.is_connected = False
            self.username = ""
            self.client = None
            
            await manager.broadcast(json.dumps({
                "type": "connection_status",
                "connected": False,
                "username": "",
                "timestamp": datetime.now().isoformat()
            }))
            
            logger.info("Disconnected from TikTok live stream")
            return True
            
        except Exception as e:
            logger.error(f"Failed to disconnect: {e}")
            return False
    
    async def handle_chat_message(self, user: str, message: str):
        """Handle incoming chat messages from TikTok Live"""
        global tts_enabled
        
        chat_data = {
            "type": "chat_message",
            "user": user,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "tts_enabled": tts_enabled
        }
        
        # Broadcast to all connected clients
        await manager.broadcast(json.dumps(chat_data))
        
        # Store in database
        try:
            await db.chat_messages.insert_one({
                "id": str(uuid.uuid4()),
                "user": user,
                "message": message,
                "timestamp": datetime.now(),
                "username_stream": self.username
            })
        except Exception as e:
            logger.error(f"Error saving message to database: {e}")
        
        logger.info(f"Chat message from {user}: {message}")

# Initialize TikTok bot
tiktok_bot = TikTokLiveBot()

# API Routes
@app.get("/")
async def root():
    return {"message": "TikTok Live TTS Bot API", "status": "running"}

@app.get("/api/status")
async def get_status():
    return {
        "connected": tiktok_bot.is_connected,
        "username": tiktok_bot.username,
        "tts_enabled": tts_enabled,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/connect")
async def connect_tiktok(data: dict):
    username = data.get("username", "").replace("@", "")
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    
    global current_username
    current_username = username
    
    success = await tiktok_bot.connect_to_stream(username)
    
    if success:
        return {"success": True, "message": f"Connected to @{username}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to connect to TikTok live")

@app.post("/api/disconnect")
async def disconnect_tiktok():
    global current_username
    current_username = ""
    
    success = await tiktok_bot.disconnect_from_stream()
    
    if success:
        return {"success": True, "message": "Disconnected from TikTok live"}
    else:
        raise HTTPException(status_code=500, detail="Failed to disconnect")

@app.post("/api/toggle-tts")
async def toggle_tts():
    global tts_enabled
    tts_enabled = not tts_enabled
    
    await manager.broadcast(json.dumps({
        "type": "tts_status",
        "enabled": tts_enabled,
        "timestamp": datetime.now().isoformat()
    }))
    
    return {"tts_enabled": tts_enabled}

@app.get("/api/chat-history")
async def get_chat_history(limit: int = 50):
    messages = await db.chat_messages.find().sort("timestamp", -1).limit(limit).to_list(length=limit)
    
    # Convert ObjectId to string and format for frontend
    formatted_messages = []
    for msg in messages:
        formatted_messages.append({
            "id": msg.get("id", str(msg["_id"])),
            "user": msg["user"],
            "message": msg["message"],
            "timestamp": msg["timestamp"].isoformat() if hasattr(msg["timestamp"], 'isoformat') else str(msg["timestamp"])
        })
    
    return {"messages": formatted_messages}

# WebSocket endpoint
@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Handle different message types
            if message_data.get("type") == "test_message":
                # Simulate a chat message for testing
                await tiktok_bot.handle_chat_message("TestUser", "¡Hola! Este es un mensaje de prueba")
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected" if client else "disconnected",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
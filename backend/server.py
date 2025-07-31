from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import os
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import json
import logging
from datetime import datetime
import uvicorn
from typing import List, Dict, Optional
import uuid

# Load environment variables
load_dotenv()

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
from TikTokLive.events import ConnectEvent, CommentEvent, DisconnectEvent, UserStatsEvent

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
            
            # Get SING_API_KEY from environment
            sing_api_key = os.environ.get('SING_API_KEY', '')
            logger.info(f"Using SING_API_KEY: {sing_api_key[:20]}..." if sing_api_key else "No SING_API_KEY found")
            
            # Initialize TikTok Live client with basic configuration for 6.5.2
            self.client = TikTokLiveClient(
                unique_id=clean_username
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
        async def on_connect(event):
            self.is_connected = True
            logger.info(f"Successfully connected to live stream!")
            
            await manager.broadcast(json.dumps({
                "type": "connection_status",
                "connected": True,
                "username": getattr(event, 'unique_id', self.username),
                "timestamp": datetime.now().isoformat()
            }))
        
        @self.client.on(CommentEvent)
        async def on_comment(event):
            user = getattr(event, 'user', None)
            user_name = getattr(user, 'nickname', 'Anonymous User') if user else "Anonymous User"
            message = getattr(event, 'comment', 'No message')
            
            logger.info(f"💬 {user_name}: {message}")
            await self.handle_chat_message(user_name, message)
        
        @self.client.on(DisconnectEvent)
        async def on_disconnect(event):
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
                await self.client.start()
        except Exception as e:
            logger.error(f"Error starting TikTok client: {e}")
            self.is_connected = False
            
            # Handle specific TikTok errors
            error_message = str(e)
            if "UserOfflineError" in str(type(e)) or "No Message Provided" in error_message:
                error_message = f"@{self.username} is not currently live. Please try again when they start streaming."
            elif "Failed to parse room ID" in error_message:
                error_message = f"Could not find live stream for @{self.username}. Please check the username and try again."
            else:
                error_message = f"Failed to connect to @{self.username}'s live stream: {error_message}"
            
            await manager.broadcast(json.dumps({
                "type": "connection_status",
                "connected": False,
                "error": error_message,
                "timestamp": datetime.now().isoformat()
            }))
    
    async def disconnect_from_stream(self):
        try:
            logger.info("Starting comprehensive disconnect process...")
            
            # Set disconnected state immediately to prevent new connections
            self.is_connected = False
            
            # First, cancel the connection task with timeout
            if self.connection_task and not self.connection_task.done():
                logger.info("Cancelling connection task...")
                self.connection_task.cancel()
                try:
                    # Wait for cancellation with timeout
                    await asyncio.wait_for(self.connection_task, timeout=3.0)
                except asyncio.CancelledError:
                    logger.info("Connection task cancelled successfully")
                except asyncio.TimeoutError:
                    logger.warning("Connection task cancellation timed out")
                except Exception as e:
                    logger.warning(f"Error waiting for connection task cancellation: {e}")
            
            # Force stop the client with multiple methods and timeout
            if self.client:
                try:
                    logger.info("Force stopping TikTok client...")
                    
                    # Try multiple disconnect methods with timeout
                    disconnect_tasks = []
                    
                    if hasattr(self.client, 'stop'):
                        disconnect_tasks.append(self.client.stop())
                    if hasattr(self.client, 'disconnect'):
                        disconnect_tasks.append(self.client.disconnect())
                    if hasattr(self.client, 'close'):
                        disconnect_tasks.append(self.client.close())
                    
                    # Execute all disconnect methods with timeout
                    if disconnect_tasks:
                        try:
                            await asyncio.wait_for(
                                asyncio.gather(*disconnect_tasks, return_exceptions=True),
                                timeout=5.0
                            )
                            logger.info("TikTok client stopped successfully")
                        except asyncio.TimeoutError:
                            logger.warning("Client disconnect timed out - forcing cleanup")
                        except Exception as e:
                            logger.warning(f"Error during client disconnect methods: {e}")
                    
                    # Force cleanup connection objects if they exist
                    if hasattr(self.client, '_websocket') and self.client._websocket:
                        try:
                            await self.client._websocket.close()
                        except:
                            pass
                    
                    if hasattr(self.client, '_connection') and self.client._connection:
                        try:
                            self.client._connection.close()
                        except:
                            pass
                            
                except Exception as e:
                    logger.warning(f"Error in comprehensive client shutdown: {e}")
            
            # Clear all event handlers to prevent callbacks
            if self.client and hasattr(self.client, '_event_handlers'):
                try:
                    self.client._event_handlers.clear()
                    logger.info("Cleared all event handlers")
                except:
                    pass
            
            # Reset all state variables
            old_username = self.username
            self.username = ""
            self.client = None
            self.connection_task = None
            
            # Force garbage collection
            import gc
            gc.collect()
            
            # Broadcast disconnection status
            await manager.broadcast(json.dumps({
                "type": "connection_status",
                "connected": False,
                "username": "",
                "message": f"Desconectado completamente de @{old_username}" if old_username else "Desconectado",
                "timestamp": datetime.now().isoformat()
            }))
            
            logger.info(f"Successfully and completely disconnected from TikTok live stream (@{old_username})")
            
            # Add a small delay to ensure all cleanup is complete
            await asyncio.sleep(0.5)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to disconnect: {e}")
            # Even if there's an error, aggressively reset the state to prevent stuck connections
            self.is_connected = False
            self.username = ""
            self.client = None
            self.connection_task = None
            
            # Still broadcast disconnection
            try:
                await manager.broadcast(json.dumps({
                    "type": "connection_status",
                    "connected": False,
                    "username": "",
                    "error": "Desconexión forzada debido a error - conexión limpiada",
                    "timestamp": datetime.now().isoformat()
                }))
            except Exception as broadcast_error:
                logger.error(f"Failed to broadcast disconnection: {broadcast_error}")
            
            return True  # Return True since we've reset the state
    
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
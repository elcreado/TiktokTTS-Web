<file>
      <absolute_file_name>/app/backend/services/tiktok_service.py</absolute_file_name>
      <content">import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

from TikTokLive import TikTokLiveClient
from TikTokLive.events import ConnectEvent, CommentEvent, DisconnectEvent, UserStatsEvent

from config.settings import settings
from models.chat_message import ChatMessage
from services.database import db_service
from services.websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

class TikTokService:
    def __init__(self):
        self.client: Optional[TikTokLiveClient] = None
        self.is_connected = False
        self.username = ""
        self.connection_task: Optional[asyncio.Task] = None
        
    async def connect_to_stream(self, username: str) -> bool:
        """Connect to TikTok Live stream"""
        try:
            # Clean username (remove @ if present)
            clean_username = username.replace("@", "").strip()
            
            logger.info(f"Using SING_API_KEY: {settings.SING_API_KEY[:20]}..." if settings.SING_API_KEY else "No SING_API_KEY found")
            
            # Clear any existing client and handlers to prevent duplicates
            if self.client:
                logger.info("🧹 Clearing existing client and event handlers to prevent duplicates")
                try:
                    # Clear event handlers if they exist
                    if hasattr(self.client, '_event_handlers'):
                        self.client._event_handlers.clear()
                    # Cancel existing connection task if running
                    if self.connection_task and not self.connection_task.done():
                        self.connection_task.cancel()
                except Exception as cleanup_error:
                    logger.warning(f"⚠️ Error during client cleanup: {cleanup_error}")
            
            # Initialize TikTok Live client with basic configuration for 6.5.2
            self.client = TikTokLiveClient(unique_id=clean_username)
            
            # Set up event handlers (now on clean client)
            self._setup_event_handlers()
            
            # Start connection in background
            self.username = clean_username
            self.connection_task = asyncio.create_task(self._start_client())
            
            logger.info(f"Attempting to connect to @{clean_username}'s live stream")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to TikTok live: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            await websocket_manager.broadcast_json({
                "type": "connection_status",
                "connected": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            return False
    
    def _setup_event_handlers(self):
        """Set up all TikTok Live event handlers"""
        # Generate unique handler ID for debugging
        handler_id = datetime.now().strftime("%H:%M:%S.%f")
        logger.info(f"🔧 Setting up event handlers with ID: {handler_id}")
        
        @self.client.on(ConnectEvent)
        async def on_connect(event):
            self.is_connected = True
            logger.info(f"✅ [Handler {handler_id}] Successfully connected to live stream!")
            
            await websocket_manager.broadcast_json({
                "type": "connection_status",
                "connected": True,
                "username": getattr(event, 'unique_id', self.username),
                "timestamp": datetime.now().isoformat()
            })
        
        @self.client.on(CommentEvent)
        async def on_comment(event):
            try:
                logger.info(f"🔍 [Handler {handler_id}] Raw comment event received: {type(event)}")
                
                # Extract user info safely
                user_name = self._extract_user_name(event)
                message = self._extract_message_content(event)
                
                logger.info(f"💬 [Handler {handler_id}] Comentario procesado - {user_name}: {message}")
                await self._handle_chat_message(user_name, message)
                
            except Exception as e:
                logger.error(f"💥 [Handler {handler_id}] Error processing comment event: {e}")
                logger.warning(f"⚠️ [Handler {handler_id}] Skipping fallback message to prevent duplicates")
        
        @self.client.on(DisconnectEvent)
        async def on_disconnect(event):
            self.is_connected = False
            logger.info(f"❌ [Handler {handler_id}] Disconnected from TikTok live stream")
            
            await websocket_manager.broadcast_json({
                "type": "connection_status",
                "connected": False,
                "username": "",
                "timestamp": datetime.now().isoformat()
            })
        
        logger.info(f"✅ Event handlers setup complete with ID: {handler_id}")
    
    def _extract_user_name(self, event) -> str:
        """Extract user name from TikTok event safely"""
        user_name = "Usuario Anónimo"
        
        try:
            if hasattr(event, 'user') and event.user:
                user_name = getattr(event.user, 'nickname', 
                          getattr(event.user, 'display_name', 
                          getattr(event.user, 'unique_id', 'Usuario Anónimo')))
        except Exception as user_error:
            logger.warning(f"⚠️ Error accessing event.user: {user_error}")
            try:
                # Fallback: try to access user_info directly
                if hasattr(event, 'user_info') and event.user_info:
                    user_info = event.user_info
                    user_name = getattr(user_info, 'nickName', 
                              getattr(user_info, 'displayName',
                              getattr(user_info, 'uniqueId', 'Usuario Anónimo')))
            except Exception as user_info_error:
                logger.warning(f"⚠️ Error accessing event.user_info: {user_info_error}")
                user_name = "Usuario Anónimo"
        
        return user_name
    
    def _extract_message_content(self, event) -> str:
        """Extract message content from TikTok event safely"""
        message = "Mensaje sin contenido"
        
        try:
            if hasattr(event, 'comment'):
                message = str(event.comment) if event.comment else "Mensaje vacío"
            elif hasattr(event, 'content'):
                message = str(event.content) if event.content else "Mensaje vacío"
            elif hasattr(event, 'text'):
                message = str(event.text) if event.text else "Mensaje vacío"
            else:
                logger.warning(f"⚠️ No comment content found in event")
                message = "Mensaje sin contenido"
        except Exception as msg_error:
            logger.warning(f"⚠️ Error accessing message: {msg_error}")
            message = "Error al leer mensaje"
        
        return message
    
    async def _start_client(self):
        """Start the TikTok Live client"""
        try:
            if self.client:
                logger.info(f"🚀 Starting TikTok Live client for @{self.username}")
                await self.client.start()
                logger.info(f"🎯 TikTok Live client started successfully")
        except Exception as e:
            logger.error(f"💥 Error starting TikTok client: {e}")
            self.is_connected = False
            
            # Handle specific TikTok errors
            error_message = self._format_error_message(e)
            
            await websocket_manager.broadcast_json({
                "type": "connection_status",
                "connected": False,
                "error": error_message,
                "timestamp": datetime.now().isoformat()
            })
    
    def _format_error_message(self, error) -> str:
        """Format error message for user display"""
        error_message = str(error)
        if "UserOfflineError" in str(type(error)) or "No Message Provided" in error_message:
            error_message = f"@{self.username} is not currently live. Please try again when they start streaming."
        elif "Failed to parse room ID" in error_message:
            error_message = f"Could not find live stream for @{self.username}. Please check the username and try again."
        else:
            error_message = f"Failed to connect to @{self.username}'s live stream: {error_message}"
        
        return error_message
    
    async def _handle_chat_message(self, user: str, message: str):
        """Handle incoming chat messages from TikTok Live"""
        chat_message = ChatMessage(user=user, message=message, username_stream=self.username)
        
        # Broadcast to all connected clients
        await websocket_manager.broadcast_json(chat_message.to_websocket_dict())
        
        # Store in database
        await db_service.save_chat_message(chat_message)
        
        logger.info(f"Chat message from {user}: {message}")
    
    async def disconnect_from_stream(self) -> bool:
        """Disconnect from TikTok Live stream with comprehensive cleanup"""
        try:
            logger.info("Starting comprehensive disconnect process...")
            
            # Set disconnected state immediately to prevent new connections
            self.is_connected = False
            
            # Cancel the connection task with timeout
            if self.connection_task and not self.connection_task.done():
                logger.info("Cancelling connection task...")
                self.connection_task.cancel()
                try:
                    await asyncio.wait_for(self.connection_task, timeout=3.0)
                except (asyncio.CancelledError, asyncio.TimeoutError) as e:
                    logger.info(f"Connection task handling: {type(e).__name__}")
                except Exception as e:
                    logger.warning(f"Error waiting for connection task cancellation: {e}")
            
            # Force stop the client with multiple methods and timeout
            if self.client:
                await self._force_client_disconnect()
            
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
            await websocket_manager.broadcast_json({
                "type": "connection_status",
                "connected": False,
                "username": "",
                "message": f"Desconectado completamente de @{old_username}" if old_username else "Desconectado",
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info(f"Successfully and completely disconnected from TikTok live stream (@{old_username})")
            
            # Add a small delay to ensure all cleanup is complete
            await asyncio.sleep(0.5)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to disconnect: {e}")
            # Even if there's an error, aggressively reset the state
            await self._force_reset_state()
            return True  # Return True since we've reset the state
    
    async def _force_client_disconnect(self):
        """Force disconnect the TikTok client using multiple methods"""
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
    
    async def _force_reset_state(self):
        """Force reset all state variables"""
        self.is_connected = False
        self.username = ""
        self.client = None
        self.connection_task = None
        
        # Still broadcast disconnection
        try:
            await websocket_manager.broadcast_json({
                "type": "connection_status",
                "connected": False,
                "username": "",
                "error": "Desconexión forzada debido a error - conexión limpiada",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as broadcast_error:
            logger.error(f"Failed to broadcast disconnection: {broadcast_error}")
    
    async def force_disconnect(self) -> bool:
        """Force disconnect with aggressive cleanup"""
        try:
            logger.info("Force disconnect requested - performing aggressive cleanup")
            
            # Reset state immediately
            self.is_connected = False
            self.username = ""
            
            # Cancel tasks forcefully
            if self.connection_task and not self.connection_task.done():
                self.connection_task.cancel()
            
            # Set client to None
            self.client = None
            self.connection_task = None
            
            # Force garbage collection
            import gc
            gc.collect()
            
            # Broadcast forced disconnection
            await websocket_manager.broadcast_json({
                "type": "connection_status", 
                "connected": False,
                "username": "",
                "message": "Desconexión forzada completada",
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info("Force disconnect completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error in force disconnect: {e}")
            return True  # Return True since we attempt to reset state

# Global TikTok service instance
tiktok_service = TikTokService()
</content>
    </file>
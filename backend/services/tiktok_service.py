import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

from TikTokLive import TikTokLiveClient
from TikTokLive.events import ConnectEvent, CommentEvent, DisconnectEvent, UserStatsEvent

from config.settings import settings
from models.chat_message import ChatMessage

logger = logging.getLogger(__name__)

class TikTokService:
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TikTokService, cls).__new__(cls)
            cls._instance.client: Optional[TikTokLiveClient] = None
            cls._instance.is_connected = False
            cls._instance.username = ""
            cls._instance.connection_task: Optional[asyncio.Task] = None
            cls._instance._websocket_manager = None
            cls._instance._db_service = None
        return cls._instance
    
    def set_dependencies(self, websocket_manager, db_service):
        """Set dependencies to avoid circular imports"""
        self._websocket_manager = websocket_manager
        self._db_service = db_service
        
    async def connect_to_stream(self, username: str) -> bool:
        """Connect to TikTok Live stream with proper cleanup"""
        async with self._lock:
            try:
                # Clean username (remove @ if present)
                clean_username = username.replace("@", "").strip()
                
                logger.info(f"Using SING_API_KEY: {settings.SING_API_KEY[:20]}..." if settings.SING_API_KEY else "No SING_API_KEY found")
                
                # CRITICAL: Always force disconnect and cleanup first
                if self.client or self.is_connected:
                    logger.info("🧹 FORCE CLEANING: Clearing existing client and event handlers to prevent duplicates")
                    await self._force_cleanup()
                
                # Initialize TikTok Live client with basic configuration for 6.5.2
                logger.info(f"🔧 Creating NEW TikTok client for @{clean_username}")
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
                
                if self._websocket_manager:
                    await self._websocket_manager.broadcast_json({
                        "type": "connection_status",
                        "connected": False,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    })
                return False
    
    async def _force_cleanup(self):
        """Force cleanup of all existing connections and handlers"""
        try:
            # Set disconnected state immediately
            self.is_connected = False
            
            # Cancel existing connection task if running
            if self.connection_task and not self.connection_task.done():
                logger.info("Cancelling existing connection task...")
                self.connection_task.cancel()
                try:
                    await asyncio.wait_for(self.connection_task, timeout=2.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    logger.info("Connection task cancelled successfully")
                except Exception as e:
                    logger.warning(f"Error cancelling connection task: {e}")
            
            # Force stop the client with aggressive connection termination
            if self.client:
                logger.info("🔥 AGGRESSIVE DISCONNECT: Force stopping existing TikTok client...")
                try:
                    # Clear event handlers immediately
                    if hasattr(self.client, '_event_handlers'):
                        handler_count = len(self.client._event_handlers) if self.client._event_handlers else 0
                        logger.info(f"Clearing {handler_count} existing event handlers")
                        self.client._event_handlers.clear()
                    
                    # AGGRESSIVE FIX: Close WebSocket connection directly first
                    if hasattr(self.client, '_websocket') and self.client._websocket:
                        logger.info("🔌 Closing WebSocket connection directly...")
                        try:
                            await asyncio.wait_for(self.client._websocket.close(), timeout=1.0)
                            logger.info("✅ WebSocket closed directly")
                        except Exception as ws_error:
                            logger.warning(f"Error closing WebSocket directly: {ws_error}")
                    
                    # Try to close any other connection attributes
                    if hasattr(self.client, '_connection') and self.client._connection:
                        logger.info("🔌 Closing connection attribute...")
                        try:
                            await self.client._connection.close()
                        except Exception as conn_error:
                            logger.warning(f"Error closing connection: {conn_error}")
                    
                    # Now try the standard stop method with timeout
                    if hasattr(self.client, 'stop'):
                        logger.info("⏱️ Calling client.stop() with timeout...")
                        try:
                            await asyncio.wait_for(self.client.stop(), timeout=2.0)
                            logger.info("✅ Client.stop() completed")
                        except asyncio.TimeoutError:
                            logger.warning("⏰ Client.stop() timed out - continuing with force cleanup")
                        except Exception as stop_error:
                            logger.warning(f"Error in client.stop(): {stop_error}")
                    
                    # Final cleanup - close any remaining connections
                    connection_attrs = ['_websocket', '_connection', 'websocket', 'connection']
                    for attr in connection_attrs:
                        if hasattr(self.client, attr):
                            conn = getattr(self.client, attr)
                            if conn and hasattr(conn, 'close'):
                                try:
                                    await conn.close()
                                    logger.info(f"✅ Closed {attr}")
                                except Exception as e:
                                    logger.warning(f"Error closing {attr}: {e}")
                    
                    logger.info("🔥 AGGRESSIVE DISCONNECT COMPLETED")
                    
                except Exception as e:
                    logger.warning(f"Error during aggressive client cleanup: {e}")
                    logger.info("🔥 Continuing with state reset despite cleanup errors")
            
            # Reset all state
            self.client = None
            self.connection_task = None
            self.username = ""
            
            # Force garbage collection
            import gc
            gc.collect()
            
            logger.info("✅ Force cleanup completed")
            
        except Exception as e:
            logger.error(f"Error in force cleanup: {e}")
    
    def _setup_event_handlers(self):
        """Set up all TikTok Live event handlers with unique identifier"""
        # Generate unique handler ID for debugging
        handler_id = datetime.now().strftime("%H:%M:%S.%f")
        logger.info(f"🔧 Setting up SINGLE event handler set with ID: {handler_id}")
        
        @self.client.on(ConnectEvent)
        async def on_connect(event):
            # Check if we should still process connection events
            if not self.client:
                logger.info(f"🚫 [Handler {handler_id}] Ignoring connect event - client is None")
                return
                
            self.is_connected = True
            logger.info(f"✅ [SINGLE Handler {handler_id}] Successfully connected to live stream!")
            
            if self._websocket_manager:
                await self._websocket_manager.broadcast_json({
                    "type": "connection_status",
                    "connected": True,
                    "username": getattr(event, 'unique_id', self.username),
                    "timestamp": datetime.now().isoformat()
                })
        
        @self.client.on(CommentEvent)
        async def on_comment(event):
            try:
                # CRITICAL FIX: Check if we should still process events
                if not self.is_connected or not self.client:
                    logger.info(f"🚫 [Handler {handler_id}] Ignoring comment event - service disconnected")
                    return
                
                logger.info(f"🔍 [SINGLE Handler {handler_id}] Raw comment event received: {type(event)}")
                
                # Extract user info safely
                user_name = self._extract_user_name(event)
                message = self._extract_message_content(event)
                
                logger.info(f"💬 [SINGLE Handler {handler_id}] Comentario procesado - {user_name}: {message}")
                await self._handle_chat_message(user_name, message)
                
            except Exception as e:
                logger.error(f"💥 [SINGLE Handler {handler_id}] Error processing comment event: {e}")
        
        @self.client.on(DisconnectEvent)
        async def on_disconnect(event):
            self.is_connected = False
            logger.info(f"❌ [SINGLE Handler {handler_id}] Disconnected from TikTok live stream")
            
            if self._websocket_manager:
                await self._websocket_manager.broadcast_json({
                    "type": "connection_status",
                    "connected": False,
                    "username": "",
                    "timestamp": datetime.now().isoformat()
                })
        
        logger.info(f"✅ SINGLE event handler set complete with ID: {handler_id}")
    
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
            
            if self._websocket_manager:
                await self._websocket_manager.broadcast_json({
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
        if self._websocket_manager:
            await self._websocket_manager.broadcast_json(chat_message.to_websocket_dict())
        
        # Store in database
        if self._db_service:
            await self._db_service.save_chat_message(chat_message)
        
        logger.info(f"Chat message from {user}: {message}")
    
    async def disconnect_from_stream(self) -> bool:
        """Disconnect from TikTok Live stream with comprehensive cleanup"""
        async with self._lock:
            try:
                logger.info("Starting comprehensive disconnect process...")
                await self._force_cleanup()
                
                # Broadcast disconnection status
                if self._websocket_manager:
                    await self._websocket_manager.broadcast_json({
                        "type": "connection_status",
                        "connected": False,
                        "username": "",
                        "message": "Desconectado completamente",
                        "timestamp": datetime.now().isoformat()
                    })
                
                logger.info("Successfully and completely disconnected from TikTok live stream")
                return True
                
            except Exception as e:
                logger.error(f"Failed to disconnect: {e}")
                return True  # Return True since we attempt to reset state
    
    async def force_disconnect(self) -> bool:
        """Force disconnect with aggressive cleanup"""
        async with self._lock:
            try:
                logger.info("Force disconnect requested - performing aggressive cleanup")
                await self._force_cleanup()
                
                if self._websocket_manager:
                    await self._websocket_manager.broadcast_json({
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
                return True

# Create singleton instance
tiktok_service = TikTokService()
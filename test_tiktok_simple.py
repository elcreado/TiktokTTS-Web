#!/usr/bin/env python3

import asyncio
import logging
from TikTokLive import TikTokLiveClient
from TikTokLive.events import ConnectEvent, CommentEvent, DisconnectEvent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_tiktok_connection():
    """Simple test of TikTok Live connection"""
    
    try:
        # Create client
        client = TikTokLiveClient(unique_id="charlidamelio")
        
        # Set up basic event handlers using event classes
        @client.on(ConnectEvent)
        async def on_connect(event):
            logger.info(f"Connected successfully!")
            print(f"Event type: {type(event)}")
            print(f"Event attributes: {dir(event)}")
        
        @client.on(CommentEvent)
        async def on_comment(event):
            logger.info(f"Comment received: {event}")
        
        @client.on(DisconnectEvent)
        async def on_disconnect(event):
            logger.info(f"Disconnected")
        
        # Try to start the client
        logger.info("Starting TikTok Live client...")
        await client.start()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_tiktok_connection())
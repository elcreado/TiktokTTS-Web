#!/usr/bin/env python3
"""
Simple TikTokLive library test to isolate the get_type error
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_tiktok_library():
    try:
        print("Testing TikTokLive library import...")
        from TikTokLive import TikTokLiveClient
        from TikTokLive.events import ConnectEvent, CommentEvent, DisconnectEvent
        print("✅ Import successful")
        
        print("Testing TikTokLiveClient initialization...")
        client = TikTokLiveClient(unique_id="charlidamelio")
        print("✅ Client initialization successful")
        
        print("Testing event handler setup...")
        
        @client.on(ConnectEvent)
        async def on_connect(event):
            print(f"Connected: {event}")
        
        @client.on(CommentEvent)
        async def on_comment(event):
            print(f"Comment: {event}")
        
        print("✅ Event handlers setup successful")
        
        print("Testing client start (this is where the error likely occurs)...")
        # This is likely where the error occurs
        await asyncio.wait_for(client.start(), timeout=10)
        
    except Exception as e:
        print(f"❌ Error occurred: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        
        # Try to get more details about the error
        if hasattr(e, '__cause__') and e.__cause__:
            print(f"Caused by: {e.__cause__}")
        
        return False
    
    return True

if __name__ == "__main__":
    result = asyncio.run(test_tiktok_library())
    print(f"Test result: {'SUCCESS' if result else 'FAILED'}")
#!/usr/bin/env python3
"""
Detailed TikTokLive error tracing test
"""

import asyncio
import os
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def detailed_tiktok_test():
    try:
        print("=== DETAILED TIKTOK LIVE ERROR TRACING ===")
        
        from TikTokLive import TikTokLiveClient
        from TikTokLive.events import ConnectEvent, CommentEvent, DisconnectEvent
        
        print("1. Creating TikTokLiveClient...")
        client = TikTokLiveClient(unique_id="charlidamelio")
        print("   ✅ Client created successfully")
        
        print("2. Setting up event handlers...")
        
        @client.on(ConnectEvent)
        async def on_connect(event):
            print(f"   📡 Connect event: {event}")
            print(f"   📡 Event type: {type(event)}")
            print(f"   📡 Event attributes: {dir(event)}")
        
        @client.on(CommentEvent)
        async def on_comment(event):
            print(f"   💬 Comment event: {event}")
            print(f"   💬 Event type: {type(event)}")
            print(f"   💬 Event attributes: {dir(event)}")
        
        @client.on(DisconnectEvent)
        async def on_disconnect(event):
            print(f"   🔌 Disconnect event: {event}")
        
        # Add a wildcard event handler to catch all events
        @client.on("*")
        async def on_any_event(event_name, event_data=None):
            print(f"   🌟 Any event: {event_name} - {type(event_data)}")
            if event_data and hasattr(event_data, 'get_type'):
                try:
                    print(f"   🌟 Event get_type: {event_data.get_type()}")
                except Exception as get_type_error:
                    print(f"   ❌ Error calling get_type: {get_type_error}")
        
        print("   ✅ Event handlers set up")
        
        print("3. Starting client (this may cause the error)...")
        
        # Try to start the client and catch any errors
        try:
            await asyncio.wait_for(client.start(), timeout=15)
            print("   ✅ Client started successfully")
        except asyncio.TimeoutError:
            print("   ⏰ Client start timed out (user likely not live)")
        except Exception as start_error:
            print(f"   ❌ Error starting client: {start_error}")
            print(f"   ❌ Error type: {type(start_error)}")
            print(f"   ❌ Full traceback:")
            traceback.print_exc()
            
            # Check if this is the get_type error
            if "get_type" in str(start_error):
                print("   🎯 FOUND THE GET_TYPE ERROR!")
                
                # Try to trace the error source
                tb = traceback.format_exc()
                print(f"   📋 Full traceback:\n{tb}")
        
        print("4. Attempting to stop client...")
        try:
            if hasattr(client, 'stop'):
                await client.stop()
            elif hasattr(client, 'disconnect'):
                await client.disconnect()
            print("   ✅ Client stopped successfully")
        except Exception as stop_error:
            print(f"   ❌ Error stopping client: {stop_error}")
        
    except Exception as e:
        print(f"❌ Outer exception: {e}")
        print(f"❌ Exception type: {type(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(detailed_tiktok_test())
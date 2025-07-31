#!/usr/bin/env python3
"""
TikTok Live Connection Debug Test
Specifically designed to test TikTok Live connection with enhanced event debugging
to troubleshoot why messages are not being captured.
"""

import requests
import json
import time
import websocket
import threading
from datetime import datetime
import sys
import os

class TikTokLiveDebugTester:
    def __init__(self, base_url="https://16dc95cf-bf22-40a9-9086-b03a45b6b471.preview.emergentagent.com"):
        self.base_url = base_url
        self.ws_messages = []
        self.ws_connected = False
        self.connection_events = []
        self.comment_events = []
        self.all_events = []
        
    def log(self, message):
        """Log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] {message}")
        
    def make_request(self, method, endpoint, data=None, timeout=10):
        """Make HTTP request to backend"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)
            
            return response.status_code, response.json() if response.content else {}
        except Exception as e:
            self.log(f"❌ Request error: {e}")
            return None, {}
    
    def on_ws_message(self, ws, message):
        """WebSocket message handler with detailed logging"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log(f"📨 WebSocket message: {message}")
        self.ws_messages.append({"timestamp": timestamp, "message": message})
        
        try:
            data = json.loads(message)
            msg_type = data.get('type', 'unknown')
            
            if msg_type == 'connection_status':
                self.connection_events.append(data)
                self.log(f"🔗 Connection event: connected={data.get('connected')}, username={data.get('username')}")
                if data.get('error'):
                    self.log(f"❌ Connection error: {data.get('error')}")
                    
            elif msg_type == 'chat_message':
                self.comment_events.append(data)
                self.log(f"💬 Chat message: {data.get('user')} - {data.get('message')}")
                
            self.all_events.append(data)
            
        except json.JSONDecodeError:
            self.log(f"⚠️ Non-JSON WebSocket message: {message}")
    
    def on_ws_error(self, ws, error):
        """WebSocket error handler"""
        self.log(f"❌ WebSocket error: {error}")
    
    def on_ws_close(self, ws, close_status_code, close_msg):
        """WebSocket close handler"""
        self.log(f"🔌 WebSocket closed: {close_status_code} - {close_msg}")
        self.ws_connected = False
    
    def on_ws_open(self, ws):
        """WebSocket open handler"""
        self.log("✅ WebSocket connection established")
        self.ws_connected = True
    
    def setup_websocket(self):
        """Setup WebSocket connection for real-time monitoring"""
        ws_url = self.base_url.replace("https://", "wss://").replace("http://", "ws://") + "/api/ws"
        self.log(f"🌐 Connecting to WebSocket: {ws_url}")
        
        try:
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_open=self.on_ws_open,
                on_message=self.on_ws_message,
                on_error=self.on_ws_error,
                on_close=self.on_ws_close
            )
            
            # Run WebSocket in separate thread
            self.ws_thread = threading.Thread(target=self.ws.run_forever)
            self.ws_thread.daemon = True
            self.ws_thread.start()
            
            # Wait for connection
            time.sleep(3)
            return self.ws_connected
            
        except Exception as e:
            self.log(f"❌ WebSocket setup failed: {e}")
            return False
    
    def test_connection_to_popular_user(self, username):
        """Test connection to a popular TikTok user"""
        self.log(f"🎯 Testing connection to popular user: @{username}")
        
        # Clear previous events
        self.connection_events = []
        self.comment_events = []
        self.all_events = []
        
        # Get initial status
        status_code, initial_status = self.make_request('GET', 'api/status')
        self.log(f"📊 Initial status: {initial_status}")
        
        # Attempt connection
        self.log(f"🔗 Attempting to connect to @{username}...")
        status_code, connect_response = self.make_request('POST', 'api/connect', {"username": username})
        
        if status_code == 200:
            self.log(f"✅ Connection request accepted: {connect_response}")
        else:
            self.log(f"❌ Connection request failed: {status_code} - {connect_response}")
            return False
        
        # Monitor for connection events and messages
        self.log("👀 Monitoring for connection events and messages...")
        monitoring_duration = 30  # Monitor for 30 seconds
        start_time = time.time()
        
        while time.time() - start_time < monitoring_duration:
            # Check connection details periodically
            if int(time.time() - start_time) % 5 == 0:
                status_code, details = self.make_request('GET', 'api/connection-details')
                if status_code == 200:
                    self.log(f"📊 Connection details: {details}")
            
            time.sleep(1)
        
        # Final status check
        status_code, final_status = self.make_request('GET', 'api/status')
        self.log(f"📊 Final status: {final_status}")
        
        return True
    
    def test_message_simulation(self):
        """Test message simulation through WebSocket"""
        self.log("🧪 Testing message simulation via WebSocket...")
        
        if not self.ws_connected:
            self.log("❌ WebSocket not connected, cannot test message simulation")
            return False
        
        # Send test message
        test_message = json.dumps({"type": "test_message"})
        self.ws.send(test_message)
        self.log(f"📤 Sent test message: {test_message}")
        
        # Wait for response
        time.sleep(3)
        
        # Check if we received a chat message
        test_messages = [event for event in self.all_events if event.get('type') == 'chat_message' and 'TestUser' in event.get('user', '')]
        
        if test_messages:
            self.log(f"✅ Test message simulation successful: {len(test_messages)} messages received")
            return True
        else:
            self.log("❌ Test message simulation failed - no test messages received")
            return False
    
    def analyze_events(self):
        """Analyze all captured events"""
        self.log("\n📊 EVENT ANALYSIS")
        self.log("=" * 50)
        
        self.log(f"Total WebSocket messages received: {len(self.ws_messages)}")
        self.log(f"Connection events: {len(self.connection_events)}")
        self.log(f"Chat message events: {len(self.comment_events)}")
        self.log(f"All parsed events: {len(self.all_events)}")
        
        # Analyze connection events
        if self.connection_events:
            self.log("\n🔗 CONNECTION EVENTS:")
            for i, event in enumerate(self.connection_events):
                self.log(f"  {i+1}. Connected: {event.get('connected')}, Username: {event.get('username')}")
                if event.get('error'):
                    self.log(f"     Error: {event.get('error')}")
        
        # Analyze chat events
        if self.comment_events:
            self.log("\n💬 CHAT MESSAGE EVENTS:")
            for i, event in enumerate(self.comment_events):
                self.log(f"  {i+1}. {event.get('user')}: {event.get('message')}")
        else:
            self.log("\n💬 NO CHAT MESSAGE EVENTS CAPTURED")
            self.log("   This indicates that either:")
            self.log("   - The user is not currently live")
            self.log("   - No one is commenting during the monitoring period")
            self.log("   - There's an issue with the TikTok Live event handling")
        
        # Analyze all event types
        event_types = {}
        for event in self.all_events:
            event_type = event.get('type', 'unknown')
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        if event_types:
            self.log(f"\n📋 EVENT TYPE SUMMARY:")
            for event_type, count in event_types.items():
                self.log(f"  {event_type}: {count}")
        
        return len(self.comment_events) > 0
    
    def test_backend_logs_monitoring(self):
        """Check if backend is properly logging TikTok events"""
        self.log("\n🔍 BACKEND LOGS ANALYSIS")
        self.log("=" * 30)
        self.log("Note: Backend logs should show detailed TikTok event information")
        self.log("Look for the following in backend logs:")
        self.log("  - '🔍 Raw comment event received'")
        self.log("  - '🔍 Event attributes'")
        self.log("  - '💬 Comentario procesado'")
        self.log("  - '🌟 Any event captured'")
        self.log("  - '🎯 String-based comment event'")
        self.log("  - '📝 Live comment event'")
        
        # The actual log monitoring would require access to backend logs
        # which is not directly available through the API
        return True
    
    def run_comprehensive_debug_test(self):
        """Run comprehensive TikTok Live debug test"""
        self.log("🚀 STARTING TIKTOK LIVE DEBUG TEST")
        self.log("=" * 60)
        
        # Setup WebSocket for real-time monitoring
        if not self.setup_websocket():
            self.log("❌ Failed to setup WebSocket - continuing without real-time monitoring")
        
        # Test popular TikTok users
        popular_users = ["charlidamelio", "addisonre", "zachking"]
        
        for username in popular_users:
            self.log(f"\n🎯 TESTING USER: @{username}")
            self.log("-" * 40)
            
            # Test connection
            success = self.test_connection_to_popular_user(username)
            
            if success:
                # Wait a bit more to capture any delayed events
                self.log("⏳ Waiting for additional events...")
                time.sleep(10)
                
                # Analyze what we captured
                has_messages = self.analyze_events()
                
                if has_messages:
                    self.log(f"✅ Successfully captured messages from @{username}")
                    break
                else:
                    self.log(f"⚠️ No messages captured from @{username} (may not be live)")
            
            # Disconnect before trying next user
            self.log("🔌 Disconnecting...")
            self.make_request('POST', 'api/disconnect')
            time.sleep(3)
        
        # Test message simulation
        self.log(f"\n🧪 MESSAGE SIMULATION TEST")
        self.log("-" * 30)
        self.test_message_simulation()
        
        # Backend logs analysis
        self.test_backend_logs_monitoring()
        
        # Final cleanup
        self.log("\n🧹 CLEANUP")
        self.log("-" * 10)
        self.make_request('POST', 'api/force-disconnect')
        
        if hasattr(self, 'ws'):
            self.ws.close()
        
        # Final summary
        self.log("\n📊 FINAL SUMMARY")
        self.log("=" * 20)
        self.log(f"Total events captured: {len(self.all_events)}")
        self.log(f"Connection events: {len(self.connection_events)}")
        self.log(f"Chat messages: {len(self.comment_events)}")
        
        if self.comment_events:
            self.log("✅ SUCCESS: Chat messages were captured")
            return True
        else:
            self.log("⚠️ NO CHAT MESSAGES CAPTURED")
            self.log("Possible reasons:")
            self.log("  1. Users tested were not live during test")
            self.log("  2. No comments were made during monitoring period")
            self.log("  3. TikTok Live event handling needs debugging")
            self.log("  4. TikTok API changes or rate limiting")
            return False

def main():
    """Main test execution"""
    print("🎯 TikTok Live Connection Debug Test")
    print("=" * 50)
    print("This test will:")
    print("1. Connect to popular TikTok Live streams")
    print("2. Monitor for comment events with enhanced debugging")
    print("3. Test message simulation via WebSocket")
    print("4. Analyze captured events and provide diagnostics")
    print("=" * 50)
    
    tester = TikTokLiveDebugTester()
    success = tester.run_comprehensive_debug_test()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
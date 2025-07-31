import requests
import sys
import json
import time
from datetime import datetime
import websocket
import threading

class TikTokTTSBotTester:
    def __init__(self, base_url="https://08033c89-d06c-48f7-8742-b792371dd8ae.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.ws_messages = []
        self.ws_connected = False

    def run_test(self, name, method, endpoint, expected_status, data=None, timeout=10):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=timeout)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response: {json.dumps(response_data, indent=2)}")
                    return True, response_data
                except:
                    print(f"   Response: {response.text}")
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error: {json.dumps(error_data, indent=2)}")
                except:
                    print(f"   Error: {response.text}")
                return False, {}

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timeout after {timeout}s")
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test root endpoint"""
        return self.run_test("Root Endpoint", "GET", "", 200)

    def test_health_check(self):
        """Test health check endpoint"""
        return self.run_test("Health Check", "GET", "api/health", 200)

    def test_status_endpoint(self):
        """Test status endpoint"""
        return self.run_test("Status Check", "GET", "api/status", 200)

    def test_connect_invalid_username(self):
        """Test connect with invalid/empty username"""
        success, _ = self.run_test(
            "Connect with Empty Username",
            "POST",
            "api/connect",
            400,
            data={"username": ""}
        )
        return success

    def test_connect_valid_username(self):
        """Test connect with valid username (will likely fail as user may not be live)"""
        # Use a more realistic TikTok username that might be live
        test_username = "charlidamelio"  # Popular TikTok user
        success, response = self.run_test(
            "Connect with Popular Username",
            "POST",
            "api/connect",
            200,  # We expect 200 even if connection fails, as the API accepts the request
            data={"username": test_username}
        )
        return success, response

    def test_disconnect(self):
        """Test disconnect endpoint"""
        return self.run_test("Disconnect", "POST", "api/disconnect", 200)

    def test_toggle_tts(self):
        """Test TTS toggle endpoint"""
        return self.run_test("Toggle TTS", "POST", "api/toggle-tts", 200)

    def test_chat_history(self):
        """Test chat history endpoint"""
        return self.run_test("Chat History", "GET", "api/chat-history", 200)

    def test_chat_history_with_limit(self):
        """Test chat history with limit parameter"""
        return self.run_test("Chat History with Limit", "GET", "api/chat-history?limit=10", 200)

    def on_ws_message(self, ws, message):
        """WebSocket message handler"""
        print(f"📨 WebSocket message received: {message}")
        self.ws_messages.append(message)

    def on_ws_error(self, ws, error):
        """WebSocket error handler"""
        print(f"❌ WebSocket error: {error}")

    def on_ws_close(self, ws, close_status_code, close_msg):
        """WebSocket close handler"""
        print(f"🔌 WebSocket connection closed: {close_status_code} - {close_msg}")
        self.ws_connected = False

    def on_ws_open(self, ws):
        """WebSocket open handler"""
        print("✅ WebSocket connection opened")
        self.ws_connected = True
        
        # Send a test message
        test_message = json.dumps({"type": "test_message"})
        ws.send(test_message)
        print(f"📤 Sent test message: {test_message}")

    def test_websocket_connection(self):
        """Test WebSocket connection"""
        print(f"\n🔍 Testing WebSocket Connection...")
        
        # Convert HTTP URL to WebSocket URL
        ws_url = self.base_url.replace("https://", "wss://").replace("http://", "ws://") + "/api/ws"
        print(f"   WebSocket URL: {ws_url}")
        
        try:
            # Create WebSocket connection
            ws = websocket.WebSocketApp(
                ws_url,
                on_open=self.on_ws_open,
                on_message=self.on_ws_message,
                on_error=self.on_ws_error,
                on_close=self.on_ws_close
            )
            
            # Run WebSocket in a separate thread
            ws_thread = threading.Thread(target=ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            # Wait for connection and messages
            time.sleep(5)
            
            # Close connection
            ws.close()
            
            self.tests_run += 1
            if self.ws_connected or len(self.ws_messages) > 0:
                self.tests_passed += 1
                print("✅ WebSocket test passed")
                return True
            else:
                print("❌ WebSocket test failed - no connection or messages")
                return False
                
        except Exception as e:
            self.tests_run += 1
            print(f"❌ WebSocket test failed - Error: {str(e)}")
            return False

def main():
    print("🚀 Starting TikTok Live TTS Bot API Tests")
    print("=" * 60)
    
    # Initialize tester
    tester = TikTokTTSBotTester()
    
    # Run basic endpoint tests
    print("\n📋 BASIC ENDPOINT TESTS")
    print("-" * 30)
    
    tester.test_root_endpoint()
    tester.test_health_check()
    tester.test_status_endpoint()
    
    # Test TTS functionality
    print("\n🔊 TTS FUNCTIONALITY TESTS")
    print("-" * 30)
    
    tester.test_toggle_tts()
    
    # Test chat history
    print("\n💬 CHAT HISTORY TESTS")
    print("-" * 30)
    
    tester.test_chat_history()
    tester.test_chat_history_with_limit()
    
    # Test connection functionality
    print("\n🔗 CONNECTION TESTS")
    print("-" * 30)
    
    tester.test_connect_invalid_username()
    
    # Test with a valid username (may fail if user not live)
    connect_success, connect_response = tester.test_connect_valid_username()
    
    # Test disconnect
    tester.test_disconnect()
    
    # Test WebSocket
    print("\n🌐 WEBSOCKET TESTS")
    print("-" * 30)
    
    tester.test_websocket_connection()
    
    # Print final results
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Tests Run: {tester.tests_run}")
    print(f"Tests Passed: {tester.tests_passed}")
    print(f"Tests Failed: {tester.tests_run - tester.tests_passed}")
    print(f"Success Rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.ws_messages:
        print(f"\nWebSocket Messages Received: {len(tester.ws_messages)}")
        for i, msg in enumerate(tester.ws_messages):
            print(f"  {i+1}. {msg}")
    
    # Return exit code
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
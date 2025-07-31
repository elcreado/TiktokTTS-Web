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

    def test_force_disconnect(self):
        """Test force disconnect endpoint for stubborn connections"""
        return self.run_test("Force Disconnect", "POST", "api/force-disconnect", 200)

    def test_connection_details(self):
        """Test connection details endpoint"""
        return self.run_test("Connection Details", "GET", "api/connection-details", 200)

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

    def test_comprehensive_disconnect_system(self):
        """Test the enhanced disconnection system comprehensively"""
        print(f"\n🔍 Testing Enhanced Disconnection System...")
        
        # First, get initial connection details
        print("   📊 Getting initial connection state...")
        initial_success, initial_data = self.run_test("Initial Connection Details", "GET", "api/connection-details", 200)
        
        if initial_success:
            print(f"   Initial state: connected={initial_data.get('is_connected', False)}")
        
        # Test regular disconnect
        print("   🔌 Testing regular disconnect...")
        disconnect_success, disconnect_data = self.run_test("Regular Disconnect", "POST", "api/disconnect", 200)
        
        # Wait a moment for cleanup
        time.sleep(2)
        
        # Check connection details after disconnect
        print("   📊 Checking state after regular disconnect...")
        after_disconnect_success, after_disconnect_data = self.run_test("Connection Details After Disconnect", "GET", "api/connection-details", 200)
        
        if after_disconnect_success:
            print(f"   State after disconnect: connected={after_disconnect_data.get('is_connected', False)}")
        
        # Test force disconnect
        print("   💪 Testing force disconnect...")
        force_disconnect_success, force_disconnect_data = self.run_test("Force Disconnect", "POST", "api/force-disconnect", 200)
        
        # Wait a moment for cleanup
        time.sleep(2)
        
        # Check final connection details
        print("   📊 Checking final state after force disconnect...")
        final_success, final_data = self.run_test("Final Connection Details", "GET", "api/connection-details", 200)
        
        if final_success:
            print(f"   Final state: connected={final_data.get('is_connected', False)}")
        
        # Evaluate overall success
        overall_success = all([
            initial_success,
            disconnect_success,
            after_disconnect_success,
            force_disconnect_success,
            final_success
        ])
        
        if overall_success:
            print("✅ Enhanced Disconnection System test passed")
        else:
            print("❌ Enhanced Disconnection System test failed")
        
        return overall_success

    def test_connection_state_management(self):
        """Test connection and disconnection sequences multiple times"""
        print(f"\n🔍 Testing Connection State Management...")
        
        test_username = "charlidamelio"  # Popular TikTok user
        success_count = 0
        total_cycles = 3
        
        for cycle in range(total_cycles):
            print(f"   🔄 Cycle {cycle + 1}/{total_cycles}")
            
            # Get initial state
            initial_success, initial_data = self.run_test(f"Cycle {cycle+1} - Initial State", "GET", "api/connection-details", 200)
            if initial_success:
                success_count += 1
            
            # Attempt connection
            connect_success, connect_data = self.run_test(
                f"Cycle {cycle+1} - Connect",
                "POST",
                "api/connect",
                200,
                data={"username": test_username}
            )
            if connect_success:
                success_count += 1
            
            # Wait for connection attempt
            time.sleep(3)
            
            # Check state after connection attempt
            after_connect_success, after_connect_data = self.run_test(f"Cycle {cycle+1} - State After Connect", "GET", "api/connection-details", 200)
            if after_connect_success:
                success_count += 1
            
            # Disconnect
            disconnect_success, disconnect_data = self.run_test(f"Cycle {cycle+1} - Disconnect", "POST", "api/disconnect", 200)
            if disconnect_success:
                success_count += 1
            
            # Wait for disconnect
            time.sleep(2)
            
            # Check final state
            final_success, final_data = self.run_test(f"Cycle {cycle+1} - Final State", "GET", "api/connection-details", 200)
            if final_success:
                success_count += 1
                if final_data.get('is_connected', True) == False:
                    print(f"   ✅ Cycle {cycle+1}: Connection properly reset")
                else:
                    print(f"   ⚠️ Cycle {cycle+1}: Connection may not be properly reset")
        
        expected_tests = total_cycles * 5  # 5 tests per cycle
        success_rate = (success_count / expected_tests) * 100
        
        print(f"   📊 Connection State Management: {success_count}/{expected_tests} tests passed ({success_rate:.1f}%)")
        
        return success_count == expected_tests

    def test_error_handling_and_timeouts(self):
        """Test connection to invalid/offline users and verify proper error handling"""
        print(f"\n🔍 Testing Error Handling and Timeouts...")
        
        # Test with completely invalid username
        invalid_usernames = ["", "nonexistentuser12345", "@invaliduser", "user with spaces"]
        success_count = 0
        
        for username in invalid_usernames:
            print(f"   🚫 Testing invalid username: '{username}'")
            
            if username == "":
                # Empty username should return 400
                success, data = self.run_test(
                    f"Invalid Username: '{username}'",
                    "POST",
                    "api/connect",
                    400,
                    data={"username": username}
                )
            else:
                # Other invalid usernames should return 200 but fail to connect
                success, data = self.run_test(
                    f"Invalid Username: '{username}'",
                    "POST",
                    "api/connect",
                    200,
                    data={"username": username}
                )
            
            if success:
                success_count += 1
            
            # Wait and then disconnect to clean up
            time.sleep(2)
            self.run_test("Cleanup Disconnect", "POST", "api/disconnect", 200)
            time.sleep(1)
        
        print(f"   📊 Error Handling: {success_count}/{len(invalid_usernames)} tests passed")
        
        return success_count == len(invalid_usernames)

    def test_rapid_connect_disconnect_cycles(self):
        """Test multiple rapid connect/disconnect cycles for backend stability"""
        print(f"\n🔍 Testing Rapid Connect/Disconnect Cycles...")
        
        test_username = "charlidamelio"
        rapid_cycles = 5
        success_count = 0
        
        for cycle in range(rapid_cycles):
            print(f"   ⚡ Rapid cycle {cycle + 1}/{rapid_cycles}")
            
            # Quick connect
            connect_success, _ = self.run_test(
                f"Rapid Connect {cycle+1}",
                "POST",
                "api/connect",
                200,
                data={"username": test_username},
                timeout=5
            )
            
            # Minimal wait
            time.sleep(0.5)
            
            # Quick disconnect
            disconnect_success, _ = self.run_test(
                f"Rapid Disconnect {cycle+1}",
                "POST",
                "api/disconnect",
                200,
                timeout=5
            )
            
            # Minimal wait
            time.sleep(0.5)
            
            if connect_success and disconnect_success:
                success_count += 1
        
        # Final cleanup with force disconnect
        print("   🧹 Final cleanup with force disconnect...")
        self.run_test("Final Force Disconnect", "POST", "api/force-disconnect", 200)
        time.sleep(1)
        
        # Check final state
        final_success, final_data = self.run_test("Final State Check", "GET", "api/connection-details", 200)
        
        print(f"   📊 Rapid Cycles: {success_count}/{rapid_cycles} cycles completed successfully")
        
        if final_success and final_data.get('is_connected', True) == False:
            print("   ✅ Backend stability maintained - no stuck connections")
            return success_count >= (rapid_cycles * 0.8)  # Allow 20% failure rate for rapid cycles
        else:
            print("   ⚠️ Potential backend stability issue detected")
            return False
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
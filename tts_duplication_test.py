import requests
import sys
import json
import time
from datetime import datetime
import websocket
import threading
import asyncio
from collections import defaultdict

class TTSDuplicationTester:
    def __init__(self, base_url="https://4cbc6651-841d-4f32-a56a-0500cc578280.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.ws_messages = []
        self.ws_connected = False
        self.message_counts = defaultdict(int)  # Track message duplicates
        self.chat_messages_received = []
        self.connection_events = []
        self.tts_events = []
        
    def reset_message_tracking(self):
        """Reset message tracking for new test"""
        self.ws_messages = []
        self.message_counts = defaultdict(int)
        self.chat_messages_received = []
        self.connection_events = []
        self.tts_events = []

    def on_ws_message(self, ws, message):
        """WebSocket message handler with detailed tracking"""
        print(f"📨 WebSocket message received: {message}")
        self.ws_messages.append(message)
        
        try:
            parsed = json.loads(message)
            msg_type = parsed.get('type', 'unknown')
            
            # Track different message types
            if msg_type == 'chat_message':
                chat_key = f"{parsed.get('user', 'unknown')}:{parsed.get('message', 'unknown')}"
                self.message_counts[chat_key] += 1
                self.chat_messages_received.append(parsed)
                print(f"🔍 Chat message tracked: {chat_key} (count: {self.message_counts[chat_key]})")
                
            elif msg_type == 'connection_status':
                self.connection_events.append(parsed)
                print(f"🔍 Connection event tracked: {parsed.get('connected', 'unknown')}")
                
            elif msg_type == 'tts_status':
                self.tts_events.append(parsed)
                print(f"🔍 TTS event tracked: {parsed.get('enabled', 'unknown')}")
                
        except json.JSONDecodeError:
            print(f"⚠️ Could not parse WebSocket message as JSON: {message}")

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

    def setup_websocket_connection(self):
        """Setup WebSocket connection for testing"""
        ws_url = self.base_url.replace("https://", "wss://").replace("http://", "ws://") + "/api/ws"
        print(f"🔗 Connecting to WebSocket: {ws_url}")
        
        try:
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
            
            # Wait for connection
            time.sleep(2)
            
            return ws if self.ws_connected else None
            
        except Exception as e:
            print(f"❌ Failed to setup WebSocket: {e}")
            return None

    def simulate_chat_message(self, ws, user="TestUser", message="Test message"):
        """Simulate a chat message via WebSocket"""
        if ws and self.ws_connected:
            test_message = json.dumps({
                "type": "test_message",
                "user": user,
                "message": message
            })
            ws.send(test_message)
            print(f"📤 Sent simulated chat message: {user}: {message}")
            return True
        return False

    def test_duplicate_message_detection(self):
        """Test 1: Detect if messages are being duplicated in WebSocket broadcasts"""
        print(f"\n🔍 TEST 1: Duplicate Message Detection")
        print("-" * 50)
        
        self.reset_message_tracking()
        ws = self.setup_websocket_connection()
        
        if not ws:
            print("❌ Failed to establish WebSocket connection")
            self.tests_run += 1
            return False
        
        try:
            # Send multiple unique messages
            test_messages = [
                ("User1", "Hello world!"),
                ("User2", "How are you?"),
                ("User3", "This is a test message"),
                ("User1", "Another message from User1"),
                ("User4", "Final test message")
            ]
            
            print(f"📤 Sending {len(test_messages)} unique messages...")
            
            for user, message in test_messages:
                self.simulate_chat_message(ws, user, message)
                time.sleep(0.5)  # Small delay between messages
            
            # Wait for all messages to be processed
            print("⏳ Waiting for message processing...")
            time.sleep(5)
            
            # Analyze results
            print(f"\n📊 Analysis Results:")
            print(f"   Total WebSocket messages received: {len(self.ws_messages)}")
            print(f"   Chat messages received: {len(self.chat_messages_received)}")
            
            # Check for duplicates
            duplicates_found = False
            for chat_key, count in self.message_counts.items():
                if count > 1:
                    print(f"   🚨 DUPLICATE DETECTED: '{chat_key}' appeared {count} times")
                    duplicates_found = True
                else:
                    print(f"   ✅ Unique message: '{chat_key}' (count: {count})")
            
            # Close WebSocket
            ws.close()
            time.sleep(1)
            
            self.tests_run += 1
            if not duplicates_found:
                self.tests_passed += 1
                print("✅ TEST 1 PASSED: No duplicate messages detected")
                return True
            else:
                print("❌ TEST 1 FAILED: Duplicate messages detected")
                return False
                
        except Exception as e:
            print(f"❌ TEST 1 ERROR: {e}")
            if ws:
                ws.close()
            self.tests_run += 1
            return False

    def test_rapid_message_handling(self):
        """Test 2: Send messages rapidly to test queue management"""
        print(f"\n🔍 TEST 2: Rapid Message Handling")
        print("-" * 50)
        
        self.reset_message_tracking()
        ws = self.setup_websocket_connection()
        
        if not ws:
            print("❌ Failed to establish WebSocket connection")
            self.tests_run += 1
            return False
        
        try:
            # Send messages rapidly
            rapid_messages = [
                ("RapidUser1", "Rapid message 1"),
                ("RapidUser2", "Rapid message 2"),
                ("RapidUser3", "Rapid message 3"),
                ("RapidUser4", "Rapid message 4"),
                ("RapidUser5", "Rapid message 5")
            ]
            
            print(f"⚡ Sending {len(rapid_messages)} messages rapidly...")
            
            # Send all messages with minimal delay
            for user, message in rapid_messages:
                self.simulate_chat_message(ws, user, message)
                time.sleep(0.1)  # Very small delay
            
            # Wait for processing
            print("⏳ Waiting for rapid message processing...")
            time.sleep(8)
            
            # Analyze results
            print(f"\n📊 Rapid Message Analysis:")
            print(f"   Total WebSocket messages received: {len(self.ws_messages)}")
            print(f"   Chat messages received: {len(self.chat_messages_received)}")
            
            # Check for proper handling
            expected_unique_messages = len(rapid_messages)
            actual_unique_messages = len(set(self.message_counts.keys()))
            
            print(f"   Expected unique messages: {expected_unique_messages}")
            print(f"   Actual unique messages: {actual_unique_messages}")
            
            # Check for duplicates in rapid scenario
            rapid_duplicates = False
            for chat_key, count in self.message_counts.items():
                if count > 1:
                    print(f"   🚨 RAPID DUPLICATE: '{chat_key}' appeared {count} times")
                    rapid_duplicates = True
            
            # Close WebSocket
            ws.close()
            time.sleep(1)
            
            self.tests_run += 1
            if not rapid_duplicates and actual_unique_messages >= expected_unique_messages:
                self.tests_passed += 1
                print("✅ TEST 2 PASSED: Rapid messages handled correctly without duplicates")
                return True
            else:
                print("❌ TEST 2 FAILED: Issues with rapid message handling")
                return False
                
        except Exception as e:
            print(f"❌ TEST 2 ERROR: {e}")
            if ws:
                ws.close()
            self.tests_run += 1
            return False

    def test_event_handler_registration(self):
        """Test 3: Test multiple connect/disconnect cycles to check for handler accumulation"""
        print(f"\n🔍 TEST 3: Event Handler Registration Test")
        print("-" * 50)
        
        try:
            # Test multiple connection cycles
            cycles = 3
            all_messages_per_cycle = []
            
            for cycle in range(cycles):
                print(f"\n🔄 Cycle {cycle + 1}/{cycles}")
                
                self.reset_message_tracking()
                ws = self.setup_websocket_connection()
                
                if not ws:
                    print(f"❌ Failed WebSocket connection in cycle {cycle + 1}")
                    continue
                
                # Connect to TikTok (this will register event handlers)
                print("   🔗 Connecting to TikTok...")
                connect_response = requests.post(
                    f"{self.base_url}/api/connect",
                    json={"username": "testuser"},
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                
                time.sleep(2)
                
                # Send a test message
                self.simulate_chat_message(ws, f"CycleUser{cycle+1}", f"Message from cycle {cycle+1}")
                
                # Wait for processing
                time.sleep(3)
                
                # Disconnect
                print("   🔌 Disconnecting from TikTok...")
                disconnect_response = requests.post(
                    f"{self.base_url}/api/disconnect",
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                
                time.sleep(2)
                
                # Record messages for this cycle
                cycle_chat_messages = len(self.chat_messages_received)
                all_messages_per_cycle.append(cycle_chat_messages)
                
                print(f"   📊 Cycle {cycle + 1} chat messages: {cycle_chat_messages}")
                
                # Check for duplicates in this cycle
                cycle_duplicates = any(count > 1 for count in self.message_counts.values())
                if cycle_duplicates:
                    print(f"   🚨 Duplicates detected in cycle {cycle + 1}")
                
                ws.close()
                time.sleep(1)
            
            # Analyze across cycles
            print(f"\n📊 Cross-Cycle Analysis:")
            print(f"   Messages per cycle: {all_messages_per_cycle}")
            
            # Check if message count is increasing (indicating handler accumulation)
            handler_accumulation = False
            if len(all_messages_per_cycle) > 1:
                for i in range(1, len(all_messages_per_cycle)):
                    if all_messages_per_cycle[i] > all_messages_per_cycle[i-1]:
                        print(f"   🚨 HANDLER ACCUMULATION: Cycle {i+1} has more messages than cycle {i}")
                        handler_accumulation = True
            
            self.tests_run += 1
            if not handler_accumulation:
                self.tests_passed += 1
                print("✅ TEST 3 PASSED: No event handler accumulation detected")
                return True
            else:
                print("❌ TEST 3 FAILED: Event handler accumulation detected")
                return False
                
        except Exception as e:
            print(f"❌ TEST 3 ERROR: {e}")
            self.tests_run += 1
            return False

    def test_websocket_single_broadcast(self):
        """Test 4: Verify WebSocket sends each message only once"""
        print(f"\n🔍 TEST 4: WebSocket Single Broadcast Test")
        print("-" * 50)
        
        self.reset_message_tracking()
        ws = self.setup_websocket_connection()
        
        if not ws:
            print("❌ Failed to establish WebSocket connection")
            self.tests_run += 1
            return False
        
        try:
            # Connect to TikTok first
            print("🔗 Connecting to TikTok for real event testing...")
            connect_response = requests.post(
                f"{self.base_url}/api/connect",
                json={"username": "testuser"},
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            time.sleep(2)
            
            # Send a single test message and monitor for duplicates
            unique_message = f"Unique test message {datetime.now().strftime('%H:%M:%S.%f')}"
            self.simulate_chat_message(ws, "SingleTestUser", unique_message)
            
            print(f"📤 Sent unique message: {unique_message}")
            print("⏳ Monitoring for duplicates...")
            
            # Wait and monitor
            time.sleep(5)
            
            # Analyze the specific message
            message_key = f"SingleTestUser:{unique_message}"
            message_count = self.message_counts.get(message_key, 0)
            
            print(f"\n📊 Single Message Analysis:")
            print(f"   Message: '{unique_message}'")
            print(f"   Times received: {message_count}")
            print(f"   Total WebSocket messages: {len(self.ws_messages)}")
            
            # Disconnect
            print("🔌 Disconnecting...")
            disconnect_response = requests.post(
                f"{self.base_url}/api/disconnect",
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            ws.close()
            time.sleep(1)
            
            self.tests_run += 1
            if message_count <= 1:
                self.tests_passed += 1
                print("✅ TEST 4 PASSED: Message sent only once via WebSocket")
                return True
            else:
                print(f"❌ TEST 4 FAILED: Message sent {message_count} times (expected 1)")
                return False
                
        except Exception as e:
            print(f"❌ TEST 4 ERROR: {e}")
            if ws:
                ws.close()
            self.tests_run += 1
            return False

    def run_all_tts_duplication_tests(self):
        """Run all TTS duplication tests"""
        print("🚀 Starting TTS Duplication Tests")
        print("=" * 60)
        
        # Run all tests
        test_results = []
        
        test_results.append(self.test_duplicate_message_detection())
        test_results.append(self.test_rapid_message_handling())
        test_results.append(self.test_event_handler_registration())
        test_results.append(self.test_websocket_single_broadcast())
        
        # Print final results
        print("\n" + "=" * 60)
        print("📊 TTS DUPLICATION TEST RESULTS")
        print("=" * 60)
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        
        if self.tests_run > 0:
            success_rate = (self.tests_passed / self.tests_run) * 100
            print(f"Success Rate: {success_rate:.1f}%")
        
        # Detailed findings
        print(f"\n🔍 DETAILED FINDINGS:")
        
        if all(test_results):
            print("✅ ALL TESTS PASSED: No TTS message duplication detected")
            print("✅ The backend fix for duplicate event handlers appears to be working correctly")
        else:
            print("❌ SOME TESTS FAILED: TTS message duplication issues detected")
            print("❌ The backend may still have duplicate message processing")
        
        # Summary of message tracking
        if hasattr(self, 'message_counts') and self.message_counts:
            print(f"\n📈 MESSAGE TRACKING SUMMARY:")
            for message_key, count in self.message_counts.items():
                if count > 1:
                    print(f"   🚨 DUPLICATE: {message_key} (count: {count})")
                else:
                    print(f"   ✅ UNIQUE: {message_key} (count: {count})")
        
        return all(test_results)

def main():
    """Main function to run TTS duplication tests"""
    tester = TTSDuplicationTester()
    success = tester.run_all_tts_duplication_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
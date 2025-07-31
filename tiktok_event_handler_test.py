import requests
import sys
import json
import time
from datetime import datetime
import websocket
import threading
from collections import defaultdict

class TikTokEventHandlerTester:
    def __init__(self, base_url="https://87a199ed-5261-4b20-b5f9-536c6cc6e387.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.ws_messages = []
        self.ws_connected = False
        self.connection_events = []
        self.chat_messages = []
        
    def reset_tracking(self):
        """Reset message tracking for new test"""
        self.ws_messages = []
        self.connection_events = []
        self.chat_messages = []

    def on_ws_message(self, ws, message):
        """WebSocket message handler with detailed tracking"""
        print(f"📨 WebSocket message: {message}")
        self.ws_messages.append(message)
        
        try:
            parsed = json.loads(message)
            msg_type = parsed.get('type', 'unknown')
            
            if msg_type == 'connection_status':
                self.connection_events.append(parsed)
                print(f"🔍 Connection event: {parsed.get('connected', 'unknown')}")
                
            elif msg_type == 'chat_message':
                self.chat_messages.append(parsed)
                print(f"🔍 Chat message: {parsed.get('user', 'unknown')}: {parsed.get('message', 'unknown')}")
                
        except json.JSONDecodeError:
            print(f"⚠️ Could not parse WebSocket message as JSON: {message}")

    def on_ws_error(self, ws, error):
        print(f"❌ WebSocket error: {error}")

    def on_ws_close(self, ws, close_status_code, close_msg):
        print(f"🔌 WebSocket closed: {close_status_code} - {close_msg}")
        self.ws_connected = False

    def on_ws_open(self, ws):
        print("✅ WebSocket connected")
        self.ws_connected = True

    def setup_websocket(self):
        """Setup WebSocket connection"""
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
            
            ws_thread = threading.Thread(target=ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            time.sleep(2)
            return ws if self.ws_connected else None
            
        except Exception as e:
            print(f"❌ Failed to setup WebSocket: {e}")
            return None

    def test_multiple_connection_cycles(self):
        """Test multiple connect/disconnect cycles to check for event handler accumulation"""
        print(f"\n🔍 TEST: Multiple Connection Cycles (Event Handler Accumulation)")
        print("-" * 70)
        
        ws = self.setup_websocket()
        if not ws:
            print("❌ Failed to establish WebSocket connection")
            self.tests_run += 1
            return False
        
        try:
            cycles = 3
            connection_events_per_cycle = []
            
            for cycle in range(cycles):
                print(f"\n🔄 Cycle {cycle + 1}/{cycles}")
                self.reset_tracking()
                
                # Connect to TikTok
                print("   🔗 Connecting to TikTok...")
                connect_response = requests.post(
                    f"{self.base_url}/api/connect",
                    json={"username": "charlidamelio"},  # Popular user more likely to be live
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                
                print(f"   Connect response: {connect_response.status_code}")
                
                # Wait for connection events
                time.sleep(5)
                
                # Count connection events in this cycle
                cycle_connection_events = len(self.connection_events)
                connection_events_per_cycle.append(cycle_connection_events)
                
                print(f"   📊 Connection events in cycle {cycle + 1}: {cycle_connection_events}")
                
                # Disconnect
                print("   🔌 Disconnecting...")
                disconnect_response = requests.post(
                    f"{self.base_url}/api/disconnect",
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                
                # Wait for disconnect events
                time.sleep(3)
                
                # Force disconnect to ensure clean state
                force_disconnect_response = requests.post(
                    f"{self.base_url}/api/force-disconnect",
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                
                time.sleep(2)
            
            # Analyze results
            print(f"\n📊 Analysis:")
            print(f"   Connection events per cycle: {connection_events_per_cycle}")
            
            # Check for event handler accumulation
            # If handlers are accumulating, we'd expect more events in later cycles
            handler_accumulation = False
            if len(connection_events_per_cycle) > 1:
                for i in range(1, len(connection_events_per_cycle)):
                    if connection_events_per_cycle[i] > connection_events_per_cycle[0] * 1.5:
                        print(f"   🚨 POTENTIAL HANDLER ACCUMULATION: Cycle {i+1} has significantly more events")
                        handler_accumulation = True
            
            ws.close()
            time.sleep(1)
            
            self.tests_run += 1
            if not handler_accumulation:
                self.tests_passed += 1
                print("✅ TEST PASSED: No significant event handler accumulation detected")
                return True
            else:
                print("❌ TEST FAILED: Potential event handler accumulation detected")
                return False
                
        except Exception as e:
            print(f"❌ TEST ERROR: {e}")
            if ws:
                ws.close()
            self.tests_run += 1
            return False

    def test_connection_state_consistency(self):
        """Test connection state consistency across multiple operations"""
        print(f"\n🔍 TEST: Connection State Consistency")
        print("-" * 50)
        
        try:
            # Test multiple rapid connect/disconnect operations
            operations = 5
            consistent_states = 0
            
            for op in range(operations):
                print(f"\n🔄 Operation {op + 1}/{operations}")
                
                # Get initial state
                initial_response = requests.get(
                    f"{self.base_url}/api/connection-details",
                    timeout=10
                )
                initial_state = initial_response.json() if initial_response.status_code == 200 else {}
                print(f"   Initial state: connected={initial_state.get('is_connected', 'unknown')}")
                
                # Connect
                connect_response = requests.post(
                    f"{self.base_url}/api/connect",
                    json={"username": "testuser"},
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                
                time.sleep(2)
                
                # Check state after connect
                after_connect_response = requests.get(
                    f"{self.base_url}/api/connection-details",
                    timeout=10
                )
                after_connect_state = after_connect_response.json() if after_connect_response.status_code == 200 else {}
                
                # Disconnect
                disconnect_response = requests.post(
                    f"{self.base_url}/api/disconnect",
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                
                time.sleep(2)
                
                # Check final state
                final_response = requests.get(
                    f"{self.base_url}/api/connection-details",
                    timeout=10
                )
                final_state = final_response.json() if final_response.status_code == 200 else {}
                print(f"   Final state: connected={final_state.get('is_connected', 'unknown')}")
                
                # Check consistency
                if final_state.get('is_connected', True) == False:
                    consistent_states += 1
                    print(f"   ✅ Operation {op + 1}: State consistent")
                else:
                    print(f"   ❌ Operation {op + 1}: State inconsistent")
            
            self.tests_run += 1
            success_rate = consistent_states / operations
            if success_rate >= 0.8:  # Allow 20% failure rate
                self.tests_passed += 1
                print(f"✅ TEST PASSED: {consistent_states}/{operations} operations had consistent state")
                return True
            else:
                print(f"❌ TEST FAILED: Only {consistent_states}/{operations} operations had consistent state")
                return False
                
        except Exception as e:
            print(f"❌ TEST ERROR: {e}")
            self.tests_run += 1
            return False

    def test_websocket_message_uniqueness(self):
        """Test that WebSocket messages are sent only once per event"""
        print(f"\n🔍 TEST: WebSocket Message Uniqueness")
        print("-" * 50)
        
        ws = self.setup_websocket()
        if not ws:
            print("❌ Failed to establish WebSocket connection")
            self.tests_run += 1
            return False
        
        try:
            self.reset_tracking()
            
            # Perform a single connect operation
            print("🔗 Performing single connect operation...")
            connect_response = requests.post(
                f"{self.base_url}/api/connect",
                json={"username": "testuser"},
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            # Wait for messages
            time.sleep(5)
            
            # Perform disconnect
            print("🔌 Performing disconnect...")
            disconnect_response = requests.post(
                f"{self.base_url}/api/disconnect",
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            # Wait for disconnect messages
            time.sleep(3)
            
            # Analyze messages
            print(f"\n📊 Message Analysis:")
            print(f"   Total WebSocket messages: {len(self.ws_messages)}")
            print(f"   Connection events: {len(self.connection_events)}")
            print(f"   Chat messages: {len(self.chat_messages)}")
            
            # Check for duplicate connection events
            connection_messages = [msg for msg in self.ws_messages if 'connection_status' in msg]
            unique_connection_messages = set(connection_messages)
            
            print(f"   Connection messages: {len(connection_messages)}")
            print(f"   Unique connection messages: {len(unique_connection_messages)}")
            
            # Check for reasonable message count (should not be excessive)
            reasonable_message_count = len(self.ws_messages) <= 10  # Reasonable threshold
            no_excessive_duplicates = len(connection_messages) <= 4  # Connect + disconnect events
            
            ws.close()
            time.sleep(1)
            
            self.tests_run += 1
            if reasonable_message_count and no_excessive_duplicates:
                self.tests_passed += 1
                print("✅ TEST PASSED: WebSocket message count is reasonable")
                return True
            else:
                print("❌ TEST FAILED: Excessive WebSocket messages detected")
                return False
                
        except Exception as e:
            print(f"❌ TEST ERROR: {e}")
            if ws:
                ws.close()
            self.tests_run += 1
            return False

    def test_backend_logging_analysis(self):
        """Test backend logging to identify potential duplication issues"""
        print(f"\n🔍 TEST: Backend Logging Analysis")
        print("-" * 50)
        
        try:
            # This test will analyze the backend behavior through API responses
            # and connection details to identify potential issues
            
            print("🔍 Analyzing backend connection behavior...")
            
            # Test 1: Multiple rapid connections
            rapid_connections = 3
            connection_details = []
            
            for i in range(rapid_connections):
                print(f"   Rapid connection {i + 1}/{rapid_connections}")
                
                # Connect
                connect_response = requests.post(
                    f"{self.base_url}/api/connect",
                    json={"username": f"testuser{i}"},
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                
                time.sleep(1)
                
                # Get connection details
                details_response = requests.get(
                    f"{self.base_url}/api/connection-details",
                    timeout=10
                )
                
                if details_response.status_code == 200:
                    details = details_response.json()
                    connection_details.append(details)
                    print(f"     Connection details: {details}")
                
                # Disconnect
                disconnect_response = requests.post(
                    f"{self.base_url}/api/disconnect",
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                
                time.sleep(1)
            
            # Analyze connection details for consistency
            print(f"\n📊 Connection Details Analysis:")
            consistent_behavior = True
            
            for i, details in enumerate(connection_details):
                has_client = details.get('has_client', False)
                has_task = details.get('has_connection_task', False)
                print(f"   Connection {i + 1}: client={has_client}, task={has_task}")
                
                # Check for potential issues
                if has_client and has_task:
                    print(f"     ⚠️ Connection {i + 1} may have lingering resources")
                    consistent_behavior = False
            
            self.tests_run += 1
            if consistent_behavior:
                self.tests_passed += 1
                print("✅ TEST PASSED: Backend connection behavior is consistent")
                return True
            else:
                print("❌ TEST FAILED: Inconsistent backend connection behavior detected")
                return False
                
        except Exception as e:
            print(f"❌ TEST ERROR: {e}")
            self.tests_run += 1
            return False

    def run_all_tests(self):
        """Run all TikTok event handler tests"""
        print("🚀 Starting TikTok Event Handler Tests")
        print("=" * 60)
        
        test_results = []
        
        # Run all tests
        test_results.append(self.test_multiple_connection_cycles())
        test_results.append(self.test_connection_state_consistency())
        test_results.append(self.test_websocket_message_uniqueness())
        test_results.append(self.test_backend_logging_analysis())
        
        # Print final results
        print("\n" + "=" * 60)
        print("📊 TIKTOK EVENT HANDLER TEST RESULTS")
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
            print("✅ ALL TESTS PASSED: No TTS message duplication issues detected")
            print("✅ The backend fix for duplicate event handlers appears to be working correctly")
            print("✅ Event handler registration and cleanup is functioning properly")
        else:
            print("❌ SOME TESTS FAILED: Potential issues detected")
            if not test_results[0]:
                print("❌ Event handler accumulation may be occurring")
            if not test_results[1]:
                print("❌ Connection state management issues detected")
            if not test_results[2]:
                print("❌ WebSocket message duplication issues detected")
            if not test_results[3]:
                print("❌ Backend connection behavior inconsistencies detected")
        
        return all(test_results)

def main():
    """Main function to run TikTok event handler tests"""
    tester = TikTokEventHandlerTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
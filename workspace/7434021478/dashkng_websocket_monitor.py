#!/usr/bin/env python3
"""
WebSocket monitor untuk dashkng - Real-time Spaceman game data
"""

import asyncio
import websockets
import json
from datetime import datetime

class DashKngWebSocketMonitor:
    def __init__(self):
        # WebSocket endpoints dari scan
        self.ws_endpoints = [
            "wss://dashkng-88-ind-929.com/crtc",
            "wss://dashkng-88-ind-929.com/direct-feed/feed?brand=VPM&X-Api-Key=3d21f3fb-d753-44ce-8062-1d27794585d5",
            "wss://dashkng-88-ind-929.com/fpapi/ws/collect",
        ]
        
        self.api_key = "3d21f3fb-d753-44ce-8062-1d27794585d5"
        self.brand = "VPM"
        
        self.captured_data = []
    
    async def connect_and_monitor(self, ws_url, duration=30):
        """Connect to WebSocket and monitor messages"""
        print(f"\n🔌 Connecting to: {ws_url}")
        
        try:
            async with websockets.connect(
                ws_url,
                user_agent_header='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                origin='https://dashkng-88-ind-929.com'
            ) as ws:
                print(f"✅ Connected!")
                
                # Monitor for specified duration
                end_time = asyncio.get_event_loop().time() + duration
                message_count = 0
                
                while asyncio.get_event_loop().time() < end_time:
                    try:
                        message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        message_count += 1
                        
                        # Try to parse JSON
                        try:
                            data = json.loads(message)
                            print(f"📨 [{message_count}] JSON Message:")
                            print(json.dumps(data, indent=2)[:500])
                            
                            self.captured_data.append({
                                'timestamp': datetime.now().isoformat(),
                                'endpoint': ws_url,
                                'type': 'json',
                                'data': data
                            })
                        except json.JSONDecodeError:
                            print(f"📨 [{message_count}] Raw Message: {message[:200]}")
                            
                            self.captured_data.append({
                                'timestamp': datetime.now().isoformat(),
                                'endpoint': ws_url,
                                'type': 'raw',
                                'data': message
                            })
                        
                    except asyncio.TimeoutError:
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        print("⚠️  Connection closed by server")
                        break
                
                print(f"✅ Captured {message_count} messages")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    async def monitor_all_endpoints(self, duration=30):
        """Monitor all WebSocket endpoints concurrently"""
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🔌 WEBSOCKET MONITOR: Real-time data capture")
        print(f"⏱️  Duration: {duration} seconds")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        tasks = [self.connect_and_monitor(url, duration) for url in self.ws_endpoints]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Save captured data
        if self.captured_data:
            with open('dashkng_websocket_data.json', 'w', encoding='utf-8') as f:
                json.dump(self.captured_data, f, indent=2, ensure_ascii=False)
            
            print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print("📊 SUMMARY:")
            print(f"   Total messages captured: {len(self.captured_data)}")
            print(f"   JSON messages: {sum(1 for x in self.captured_data if x['type'] == 'json')}")
            print(f"   Raw messages: {sum(1 for x in self.captured_data if x['type'] == 'raw')}")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print("\n💾 Data saved to: dashkng_websocket_data.json")
        else:
            print("\n⚠️  No data captured")

def main():
    monitor = DashKngWebSocketMonitor()
    asyncio.run(monitor.monitor_all_endpoints(duration=30))

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
SPACEMAN DEEP GAME MONITOR - CLICK PLAY & CAPTURE GAME DATA
Target: dashkng-88-ind-929.com
Login: ghost10 / Teruntuksemu4
"""

from playwright.sync_api import sync_playwright
import time
import json
import re
from datetime import datetime

class SpacemanDeepMonitor:
    def __init__(self):
        self.url = "https://dashkng-88-ind-929.com/en/casino/instant-games/game/pragmatic-spaceman-insta"
        self.username = "ghost10"
        self.password = "Teruntuksemu4"
        self.game_data = []
        
    def monitor(self):
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🚀 SPACEMAN DEEP MONITOR - CLICK PLAY MODE")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        with sync_playwright() as p:
            print("\n🌐 Launching headless browser...")
            browser = p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            page = context.new_page()
            
            # Capture all requests/responses
            api_calls = []
            
            def log_request(request):
                if any(x in request.url.lower() for x in ['game', 'pragmatic', 'api', 'result', 'history']):
                    api_calls.append({
                        'type': 'request',
                        'url': request.url,
                        'method': request.method,
                        'time': datetime.now().isoformat()
                    })
                    print(f"🔵 REQ: {request.method} {request.url[:100]}")
            
            def log_response(response):
                if any(x in response.url.lower() for x in ['game', 'pragmatic', 'api', 'result', 'history']):
                    api_calls.append({
                        'type': 'response',
                        'url': response.url,
                        'status': response.status,
                        'time': datetime.now().isoformat()
                    })
                    print(f"🟢 RES: {response.status} {response.url[:100]}")
                    
                    # Try to capture response body
                    try:
                        if response.status == 200:
                            body = response.text()
                            if body and len(body) < 10000:
                                print(f"   Body: {body[:300]}")
                                
                                # Save important responses
                                with open('spaceman_api_captures.log', 'a', encoding='utf-8') as f:
                                    f.write(f"\n{'='*80}\n")
                                    f.write(f"Time: {datetime.now()}\n")
                                    f.write(f"URL: {response.url}\n")
                                    f.write(f"Body: {body}\n")
                    except Exception as e:
                        pass
            
            page.on("request", log_request)
            page.on("response", log_response)
            
            # Intercept WebSocket for game data
            ws_messages = []
            
            def handle_ws(ws):
                print(f"\n🔌 WebSocket: {ws.url}")
                
                def on_frame_sent(payload):
                    try:
                        if len(payload) < 5000:
                            print(f"📤 WS SENT: {payload[:200]}")
                            ws_messages.append({'dir': 'sent', 'data': payload, 'time': datetime.now().isoformat()})
                    except:
                        pass
                
                def on_frame_received(payload):
                    try:
                        if len(payload) < 5000:
                            print(f"📥 WS RECV: {payload[:200]}")
                            ws_messages.append({'dir': 'recv', 'data': payload, 'time': datetime.now().isoformat()})
                            
                            # Look for multipliers in payload
                            if 'multiplier' in payload.lower() or re.search(r'\d+\.\d+x', payload):
                                print(f"   🎯 GAME DATA DETECTED!")
                    except:
                        pass
                
                ws.on("framesent", on_frame_sent)
                ws.on("framereceived", on_frame_received)
            
            page.on("websocket", handle_ws)
            
            try:
                print(f"\n📥 Loading page...")
                page.goto(self.url, wait_until='domcontentloaded', timeout=60000)
                time.sleep(3)
                
                page.screenshot(path='deep_01_initial.png')
                print("📸 Screenshot: deep_01_initial.png")
                
                # Click "Play" button
                print("\n🎮 Looking for PLAY button...")
                play_selectors = [
                    'button:has-text("Play")',
                    'a:has-text("Play")',
                    '[data-test="play"]',
                    'button:has-text("PLAY")',
                    '.play-button',
                    '[class*="play"]',
                ]
                
                play_clicked = False
                for selector in play_selectors:
                    try:
                        btn = page.query_selector(selector)
                        if btn and btn.is_visible():
                            print(f"   ✅ Found: {selector}")
                            btn.click()
                            print(f"   🖱️  Clicked PLAY!")
                            play_clicked = True
                            time.sleep(5)
                            break
                    except Exception as e:
                        continue
                
                if not play_clicked:
                    print("   ⚠️  PLAY button not found, trying demo mode...")
                    demo_selectors = [
                        'button:has-text("Demo")',
                        'a:has-text("Demo")',
                        '[data-test="demo"]',
                    ]
                    
                    for selector in demo_selectors:
                        try:
                            btn = page.query_selector(selector)
                            if btn and btn.is_visible():
                                print(f"   ✅ Found: {selector}")
                                btn.click()
                                print(f"   🖱️  Clicked DEMO!")
                                play_clicked = True
                                time.sleep(5)
                                break
                        except:
                            continue
                
                page.screenshot(path='deep_02_after_play.png')
                print("📸 Screenshot: deep_02_after_play.png")
                
                # Wait for iframe to load
                print("\n🎮 Waiting for game iframe...")
                time.sleep(5)
                
                iframes = page.frames
                print(f"   Found {len(iframes)} frames")
                
                for i, frame in enumerate(iframes):
                    url = frame.url
                    print(f"   [{i}] {url[:150]}")
                    
                    if 'pragmatic' in url.lower() or 'game' in url.lower():
                        print(f"   🎯 GAME FRAME DETECTED!")
                        
                        # Try to interact with game frame
                        try:
                            frame_content = frame.content()
                            with open(f'game_frame_{i}.html', 'w', encoding='utf-8') as f:
                                f.write(frame_content)
                            print(f"   💾 Saved: game_frame_{i}.html")
                        except:
                            pass
                
                # Monitor for 60 seconds
                print("\n⏱️  Monitoring game (60 seconds)...")
                print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                
                start = time.time()
                screenshot_num = 3
                
                while time.time() - start < 60:
                    # Periodic screenshot
                    if int(time.time() - start) % 10 == 0:
                        page.screenshot(path=f'deep_{screenshot_num:02d}_monitor.png')
                        print(f"\n📸 Screenshot: deep_{screenshot_num:02d}_monitor.png")
                        screenshot_num += 1
                    
                    # Check page text for multipliers
                    try:
                        text = page.evaluate('() => document.body.innerText')
                        multipliers = re.findall(r'(\d+\.\d+)x', text)
                        if multipliers:
                            print(f"🎯 Multipliers: {multipliers}")
                    except:
                        pass
                    
                    time.sleep(2)
                
                print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                print(f"✅ Monitoring complete!")
                print(f"   API calls captured: {len(api_calls)}")
                print(f"   WebSocket messages: {len(ws_messages)}")
                
                # Save captures
                with open('spaceman_api_calls.json', 'w') as f:
                    json.dump(api_calls, f, indent=2)
                print(f"💾 API calls: spaceman_api_calls.json")
                
                with open('spaceman_ws_messages.json', 'w') as f:
                    json.dump(ws_messages, f, indent=2)
                print(f"💾 WebSocket: spaceman_ws_messages.json")
                
                # Get final page state
                with open('spaceman_final_page.html', 'w', encoding='utf-8') as f:
                    f.write(page.content())
                print(f"💾 Final HTML: spaceman_final_page.html")
                
            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()
            
            finally:
                browser.close()
                print("\n🔚 Browser closed")

if __name__ == '__main__':
    monitor = SpacemanDeepMonitor()
    monitor.monitor()

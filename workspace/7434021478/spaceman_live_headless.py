#!/usr/bin/env python3
"""
SPACEMAN REAL-TIME MONITOR (HEADLESS)
Target: dashkng-88-ind-929.com - LIVE GAME
Login: ghost10 / Teruntuksemu4
"""

from playwright.sync_api import sync_playwright
import time
import json
import re
from datetime import datetime

class SpacemanLiveMonitor:
    def __init__(self):
        self.url = "https://dashkng-88-ind-929.com/en/casino/instant-games/game/pragmatic-spaceman-insta"
        self.username = "ghost10"
        self.password = "Teruntuksemu4"
        self.history = []
        self.websocket_messages = []
        
    def login_and_monitor(self):
        """Login dan monitor game real-time"""
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🚀 SPACEMAN LIVE MONITOR - HEADLESS MODE")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        with sync_playwright() as p:
            print("\n🌐 Launching headless browser...")
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-software-rasterizer',
                ]
            )
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            page = context.new_page()
            
            # Intercept WebSocket messages
            captured_data = []
            
            def handle_websocket(ws):
                print(f"\n🔌 WebSocket connected: {ws.url}")
                
                def handle_frame_sent(payload):
                    try:
                        data = json.loads(payload)
                        captured_data.append({'type': 'sent', 'data': data, 'time': datetime.now().isoformat()})
                        print(f"📤 WS SENT: {json.dumps(data)[:200]}")
                    except:
                        pass
                
                def handle_frame_received(payload):
                    try:
                        data = json.loads(payload)
                        captured_data.append({'type': 'received', 'data': data, 'time': datetime.now().isoformat()})
                        print(f"📥 WS RECV: {json.dumps(data)[:200]}")
                    except:
                        pass
                
                ws.on("framesent", handle_frame_sent)
                ws.on("framereceived", handle_frame_received)
            
            page.on("websocket", handle_websocket)
            
            # Intercept API calls
            def handle_response(response):
                if 'api' in response.url or 'game' in response.url or 'result' in response.url:
                    print(f"\n🌐 API Call: {response.url}")
                    try:
                        if response.status == 200:
                            body = response.text()
                            if body:
                                print(f"   Response: {body[:500]}")
                                
                                # Save to file
                                with open('spaceman_api_responses.log', 'a') as f:
                                    f.write(f"\n{'='*80}\n")
                                    f.write(f"Time: {datetime.now()}\n")
                                    f.write(f"URL: {response.url}\n")
                                    f.write(f"Response: {body}\n")
                    except Exception as e:
                        print(f"   Error reading response: {e}")
            
            page.on("response", handle_response)
            
            try:
                # Navigate to game
                print(f"\n📥 Loading game page...")
                page.goto(self.url, wait_until='networkidle', timeout=60000)
                time.sleep(5)
                
                print(f"✅ Page loaded: {page.title()}")
                
                # Take screenshot
                page.screenshot(path='spaceman_initial.png', full_page=True)
                print("📸 Screenshot: spaceman_initial.png")
                
                # Get page content
                content = page.content()
                
                # Check for login form
                print("\n🔐 Checking for login...")
                
                # Try multiple login strategies
                login_attempts = [
                    # Strategy 1: Direct input fields
                    lambda: self._try_login_direct(page),
                    # Strategy 2: Look for login button first
                    lambda: self._try_login_via_button(page),
                    # Strategy 3: Check for modal/popup
                    lambda: self._try_login_modal(page),
                ]
                
                logged_in = False
                for i, attempt in enumerate(login_attempts, 1):
                    try:
                        print(f"\n   Attempt {i}...")
                        if attempt():
                            logged_in = True
                            print(f"   ✅ Login successful!")
                            break
                    except Exception as e:
                        print(f"   ❌ Failed: {e}")
                        continue
                
                if not logged_in:
                    print("\n⚠️  No login form found - may already be logged in")
                
                time.sleep(3)
                page.screenshot(path='spaceman_after_login.png', full_page=True)
                print("📸 Screenshot: spaceman_after_login.png")
                
                # Find game iframe
                print("\n🎮 Looking for game iframe...")
                iframes = page.query_selector_all('iframe')
                print(f"   Found {len(iframes)} iframes")
                
                game_frame = None
                for i, iframe in enumerate(iframes, 1):
                    src = iframe.get_attribute('src') or ''
                    print(f"   [{i}] {src[:100]}")
                    
                    if 'pragmatic' in src.lower() or 'game' in src.lower():
                        game_frame = page.frame(name=iframe.get_attribute('name'))
                        print(f"   🎯 Game iframe detected!")
                        break
                
                # Monitor page for 90 seconds
                print("\n⏱️  Monitoring for game data (90 seconds)...")
                print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                
                start_time = time.time()
                screenshot_count = 0
                
                while time.time() - start_time < 90:
                    try:
                        # Take periodic screenshots
                        if int(time.time() - start_time) % 10 == 0:
                            screenshot_count += 1
                            page.screenshot(path=f'spaceman_monitor_{screenshot_count}.png')
                            print(f"\n📸 Screenshot {screenshot_count} captured")
                        
                        # Extract text from page
                        text_content = page.evaluate('() => document.body.innerText')
                        
                        # Look for multipliers
                        multipliers = re.findall(r'(\d+\.\d+)x', text_content)
                        if multipliers:
                            print(f"🎯 Found multipliers: {multipliers[:10]}")
                        
                        # Look for numbers that could be results
                        numbers = re.findall(r'\b(\d+\.\d{2})\b', text_content)
                        if numbers:
                            print(f"🔢 Numbers found: {numbers[:10]}")
                        
                    except Exception as e:
                        pass
                    
                    time.sleep(2)
                
                print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                print(f"✅ Monitoring complete! Captured {len(captured_data)} WebSocket messages")
                
                # Save captured data
                if captured_data:
                    with open('spaceman_websocket_data.json', 'w') as f:
                        json.dump(captured_data, f, indent=2)
                    print(f"💾 WebSocket data saved: spaceman_websocket_data.json")
                
                # Analyze page structure
                print("\n📊 Page Analysis:")
                print(f"   Title: {page.title()}")
                print(f"   URL: {page.url}")
                
                # Get all text
                all_text = page.evaluate('() => document.body.innerText')
                with open('spaceman_page_text.txt', 'w') as f:
                    f.write(all_text)
                print(f"💾 Page text saved: spaceman_page_text.txt")
                
                # Get HTML
                with open('spaceman_page.html', 'w') as f:
                    f.write(page.content())
                print(f"💾 HTML saved: spaceman_page.html")
                
            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()
            
            finally:
                browser.close()
                print("\n🔚 Browser closed")
    
    def _try_login_direct(self, page):
        """Try direct login via input fields"""
        username_input = page.query_selector('input[name="username"], input[type="text"]')
        password_input = page.query_selector('input[name="password"], input[type="password"]')
        
        if username_input and password_input:
            username_input.fill(self.username)
            password_input.fill(self.password)
            
            submit = page.query_selector('button[type="submit"], button:has-text("Login")')
            if submit:
                submit.click()
                time.sleep(3)
                return True
        return False
    
    def _try_login_via_button(self, page):
        """Try clicking login button first"""
        login_btn = page.query_selector('button:has-text("Login"), a:has-text("Login")')
        if login_btn:
            login_btn.click()
            time.sleep(2)
            return self._try_login_direct(page)
        return False
    
    def _try_login_modal(self, page):
        """Try login in modal/popup"""
        modals = page.query_selector_all('[role="dialog"], .modal, [class*="modal"]')
        for modal in modals:
            try:
                username = modal.query_selector('input[type="text"]')
                password = modal.query_selector('input[type="password"]')
                if username and password:
                    username.fill(self.username)
                    password.fill(self.password)
                    submit = modal.query_selector('button')
                    if submit:
                        submit.click()
                        time.sleep(3)
                        return True
            except:
                continue
        return False

if __name__ == '__main__':
    monitor = SpacemanLiveMonitor()
    monitor.login_and_monitor()

#!/usr/bin/env python3
"""
SPACEMAN REAL-TIME MONITOR & PREDICTOR
Target: dashkng-88-ind-929.com - LIVE GAME
Login: ghost10 / Teruntuksemu4
"""

from playwright.sync_api import sync_playwright
import time
import json
from datetime import datetime

class SpacemanLiveMonitor:
    def __init__(self):
        self.url = "https://dashkng-88-ind-929.com/en/casino/instant-games/game/pragmatic-spaceman-insta"
        self.username = "ghost10"
        self.password = "Teruntuksemu4"
        self.history = []
        self.predictions = []
        
    def login_and_monitor(self):
        """Login dan monitor game real-time"""
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🚀 SPACEMAN LIVE MONITOR - REAL-TIME PREDICTION")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        with sync_playwright() as p:
            print("\n🌐 Launching browser...")
            browser = p.chromium.launch(headless=False)  # Visible browser
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            page = context.new_page()
            
            try:
                # Navigate to game
                print(f"\n📥 Loading game page...")
                page.goto(self.url, wait_until='networkidle', timeout=60000)
                time.sleep(3)
                
                print(f"✅ Page loaded: {page.title()}")
                
                # Take screenshot
                page.screenshot(path='spaceman_live_initial.png', full_page=True)
                print("📸 Screenshot saved: spaceman_live_initial.png")
                
                # Check if login needed
                print("\n🔐 Checking login status...")
                
                # Look for login button/form
                login_selectors = [
                    'button:has-text("Login")',
                    'button:has-text("Sign In")',
                    'a:has-text("Login")',
                    '[data-test="login"]',
                    'input[name="username"]',
                    'input[type="text"]',
                ]
                
                login_found = False
                for selector in login_selectors:
                    try:
                        element = page.query_selector(selector)
                        if element:
                            print(f"✅ Found login element: {selector}")
                            login_found = True
                            break
                    except:
                        continue
                
                if login_found:
                    print("\n🔑 Attempting login...")
                    
                    # Try to fill username
                    username_selectors = [
                        'input[name="username"]',
                        'input[type="text"]',
                        'input[placeholder*="username" i]',
                        'input[placeholder*="email" i]',
                    ]
                    
                    for selector in username_selectors:
                        try:
                            username_input = page.query_selector(selector)
                            if username_input:
                                username_input.fill(self.username)
                                print(f"✅ Username filled: {self.username}")
                                break
                        except:
                            continue
                    
                    # Try to fill password
                    password_selectors = [
                        'input[name="password"]',
                        'input[type="password"]',
                    ]
                    
                    for selector in password_selectors:
                        try:
                            password_input = page.query_selector(selector)
                            if password_input:
                                password_input.fill(self.password)
                                print(f"✅ Password filled")
                                break
                        except:
                            continue
                    
                    # Click login button
                    login_button_selectors = [
                        'button[type="submit"]',
                        'button:has-text("Login")',
                        'button:has-text("Sign In")',
                    ]
                    
                    for selector in login_button_selectors:
                        try:
                            login_button = page.query_selector(selector)
                            if login_button:
                                login_button.click()
                                print("✅ Login button clicked")
                                time.sleep(5)
                                break
                        except:
                            continue
                    
                    page.screenshot(path='spaceman_live_after_login.png', full_page=True)
                    print("📸 Screenshot after login saved")
                
                else:
                    print("✅ Already logged in or no login required")
                
                # Find game iframe
                print("\n🎮 Looking for game iframe...")
                iframes = page.query_selector_all('iframe')
                print(f"✅ Found {len(iframes)} iframes")
                
                game_iframe = None
                for i, iframe in enumerate(iframes, 1):
                    src = iframe.get_attribute('src') or ''
                    print(f"   [{i}] {src[:100]}...")
                    
                    if 'pragmatic' in src.lower() or 'game' in src.lower():
                        game_iframe = iframe
                        print(f"   🎯 Game iframe detected!")
                
                if game_iframe:
                    print("\n🎮 Game loaded! Monitoring...")
                    
                    # Monitor for results
                    print("\n⏱️  Watching for game results (60 seconds)...")
                    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    
                    start_time = time.time()
                    round_num = 0
                    
                    while time.time() - start_time < 60:
                        # Try to extract game data
                        try:
                            # Look for multiplier text on page
                            multiplier_selectors = [
                                'text=/\\d+\\.\\d+x/i',
                                '[class*="multiplier"]',
                                '[class*="result"]',
                            ]
                            
                            for selector in multiplier_selectors:
                                try:
                                    element = page.query_selector(selector)
                                    if element:
                                        text = element.inner_text()
                                        print(f"🔍 Found text: {text}")
                                except:
                                    pass
                            
                        except:
                            pass
                        
                        time.sleep(2)
                    
                    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    print("⏱️  60 seconds monitoring complete")
                
                else:
                    print("⚠️  Game iframe not found")
                    print("\n📄 Page content analysis...")
                    
                    # Get page text content
                    content = page.content()
                    
                    # Look for game-related keywords
                    keywords = ['spaceman', 'multiplier', 'game', 'play', 'bet']
                    for keyword in keywords:
                        if keyword in content.lower():
                            print(f"   ✅ Found keyword: {keyword}")
                
                print("\n⏸️  Press Ctrl+C to stop or wait for browser close...")
                input("Press Enter to close browser...")
                
            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()
            
            finally:
                browser.close()
                print("\n🔚 Browser closed")

if __name__ == '__main__':
    monitor = SpacemanLiveMonitor()
    monitor.login_and_monitor()

#!/usr/bin/env python3
"""
Playwright scraper untuk dashkng - Extract Spaceman game endpoint
"""

from playwright.sync_api import sync_playwright
import json
import time
from datetime import datetime

class PlaywrightDashKngScraper:
    def __init__(self):
        self.url = "https://dashkng-88-ind-929.com/id-slot/?qtag=a55899_t61355635_c8311_s2hqj93be1ou4&x_pm_click=e7165b7c7323995b3715f4ea72aa5003&tsrc=tg_ads&redirect_creative_id=8311"
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'url': self.url,
            'iframes': [],
            'network_requests': [],
            'websockets': [],
            'game_endpoints': [],
            'page_content': {},
        }
    
    def run(self):
        """Run scraping dengan Playwright"""
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🤖 PLAYWRIGHT AUTOMATION: dashkng-88-ind-929.com")
        print("🎯 Mission: Extract Spaceman game endpoint")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        with sync_playwright() as p:
            print("\n🚀 Launching browser...")
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            page = context.new_page()
            
            # Setup network listener
            def handle_request(request):
                url = request.url
                self.results['network_requests'].append({
                    'url': url,
                    'method': request.method,
                    'resource_type': request.resource_type
                })
                
                # Filter game-related requests
                game_keywords = ['spaceman', 'pragmatic', 'game', 'launch', 'play', 'provider']
                if any(keyword in url.lower() for keyword in game_keywords):
                    self.results['game_endpoints'].append({
                        'url': url,
                        'method': request.method,
                        'type': request.resource_type
                    })
            
            # Setup WebSocket listener
            def handle_websocket(ws):
                print(f"   🔌 WebSocket: {ws.url}")
                self.results['websockets'].append(ws.url)
            
            page.on('request', handle_request)
            page.on('websocket', handle_websocket)
            
            try:
                # Step 1: Navigate
                print(f"\n📥 Loading page...")
                page.goto(self.url, wait_until='networkidle', timeout=30000)
                print(f"✅ Page loaded: {page.title()}")
                
                # Wait for dynamic content
                time.sleep(3)
                
                # Step 2: Screenshot
                print("\n📸 Taking screenshot...")
                page.screenshot(path='dashkng_playwright_initial.png', full_page=True)
                print("✅ Screenshot saved: dashkng_playwright_initial.png")
                
                # Step 3: Find iframes
                print("\n🔍 Searching for iframes...")
                iframes = page.query_selector_all('iframe')
                print(f"✅ Found {len(iframes)} iframes")
                
                for i, iframe in enumerate(iframes, 1):
                    iframe_data = {
                        'index': i,
                        'src': iframe.get_attribute('src') or '',
                        'id': iframe.get_attribute('id') or '',
                        'class': iframe.get_attribute('class') or '',
                    }
                    self.results['iframes'].append(iframe_data)
                    if iframe_data['src']:
                        print(f"   [{i}] {iframe_data['src'][:80]}...")
                
                # Step 4: Search for Spaceman
                print("\n🎮 Searching for Spaceman game...")
                
                # Try multiple selectors
                spaceman_selectors = [
                    'text="Spaceman"',
                    'text="spaceman"',
                    '[title*="Spaceman" i]',
                    '[alt*="Spaceman" i]',
                    'img[src*="spaceman" i]',
                    '[data-game*="spaceman" i]',
                ]
                
                spaceman_element = None
                for selector in spaceman_selectors:
                    try:
                        element = page.query_selector(selector)
                        if element:
                            print(f"✅ Found Spaceman with selector: {selector}")
                            spaceman_element = element
                            break
                    except:
                        continue
                
                if spaceman_element:
                    print("\n🎮 Clicking Spaceman game...")
                    spaceman_element.click()
                    time.sleep(5)  # Wait for game to load
                    
                    # Take screenshot after click
                    page.screenshot(path='dashkng_playwright_after_click.png', full_page=True)
                    print("✅ Screenshot saved: dashkng_playwright_after_click.png")
                    
                    # Check for new iframes
                    new_iframes = page.query_selector_all('iframe')
                    if len(new_iframes) > len(iframes):
                        print(f"✅ New iframes appeared: {len(new_iframes) - len(iframes)}")
                        for i, iframe in enumerate(new_iframes[len(iframes):], len(iframes)+1):
                            iframe_data = {
                                'index': i,
                                'src': iframe.get_attribute('src') or '',
                                'id': iframe.get_attribute('id') or '',
                                'class': iframe.get_attribute('class') or '',
                            }
                            self.results['iframes'].append(iframe_data)
                            if iframe_data['src']:
                                print(f"   [NEW {i}] {iframe_data['src'][:80]}...")
                else:
                    print("⚠️  Spaceman game not found")
                    
                    # Try to get all game elements
                    print("\n🎰 Looking for all games...")
                    games = page.query_selector_all('[data-game], .game-item, .slot-game, .game-card')
                    print(f"✅ Found {len(games)} game elements")
                    
                    if games:
                        print("   First 5 games:")
                        for i, game in enumerate(games[:5], 1):
                            game_name = game.get_attribute('data-game') or game.get_attribute('title') or game.inner_text()[:30]
                            print(f"   [{i}] {game_name}")
                
                # Step 5: Extract page data
                print("\n📊 Extracting page data...")
                
                # Get all script tags
                scripts = page.query_selector_all('script')
                print(f"✅ Found {len(scripts)} script tags")
                
                # Look for config/data in page
                page_data = page.evaluate('''() => {
                    return {
                        has_window_config: typeof window.__CONFIG__ !== 'undefined',
                        has_nuxt: typeof window.__NUXT__ !== 'undefined',
                        has_next: typeof window.__NEXT_DATA__ !== 'undefined',
                        localStorage_keys: Object.keys(localStorage || {}),
                        sessionStorage_keys: Object.keys(sessionStorage || {}),
                    }
                }''')
                
                self.results['page_content'] = page_data
                print(f"   Config found: {page_data}")
                
                # Save results
                with open('dashkng_playwright_results.json', 'w', encoding='utf-8') as f:
                    json.dump(self.results, f, indent=2, ensure_ascii=False)
                
                print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                print("📊 SUMMARY:")
                print(f"   🖼️  Iframes: {len(self.results['iframes'])}")
                print(f"   🌐 Network requests: {len(self.results['network_requests'])}")
                print(f"   🎮 Game endpoints: {len(self.results['game_endpoints'])}")
                print(f"   🔌 WebSockets: {len(self.results['websockets'])}")
                print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                
                if self.results['game_endpoints']:
                    print("\n🎯 GAME ENDPOINTS FOUND:")
                    for endpoint in self.results['game_endpoints'][:10]:
                        print(f"   → {endpoint['url'][:100]}")
                
                if self.results['websockets']:
                    print("\n🔌 WEBSOCKET ENDPOINTS:")
                    for ws in self.results['websockets']:
                        print(f"   → {ws}")
                
                if self.results['iframes']:
                    print("\n🖼️  IFRAMES:")
                    for iframe in self.results['iframes']:
                        if iframe['src']:
                            print(f"   → {iframe['src'][:100]}")
                
                print("\n💾 Results saved to: dashkng_playwright_results.json")
                
            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()
            
            finally:
                browser.close()
                print("\n🔚 Browser closed")
        
        return self.results

if __name__ == '__main__':
    scraper = PlaywrightDashKngScraper()
    scraper.run()

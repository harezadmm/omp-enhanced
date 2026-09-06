#!/usr/bin/env python3
"""
Browser automation untuk extract Spaceman game endpoint dari dashkng
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
from datetime import datetime

class DashKngBrowserScraper:
    def __init__(self):
        self.url = "https://dashkng-88-ind-929.com/id-slot/?qtag=a55899_t61355635_c8311_s2hqj93be1ou4&x_pm_click=e7165b7c7323995b3715f4ea72aa5003&tsrc=tg_ads&redirect_creative_id=8311"
        self.driver = None
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'url': self.url,
            'iframes': [],
            'network_requests': [],
            'websockets': [],
            'game_endpoints': [],
        }
    
    def setup_driver(self):
        """Setup Chrome driver dengan headless mode"""
        print("🚀 Setting up Chrome driver...")
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Enable performance logging untuk capture network requests
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            print("✅ Chrome driver ready!")
            return True
        except Exception as e:
            print(f"❌ Error setting up driver: {e}")
            return False
    
    def capture_network_logs(self):
        """Capture network requests dari Chrome DevTools"""
        print("\n🌐 Capturing network requests...")
        
        try:
            logs = self.driver.get_log('performance')
            
            game_keywords = ['spaceman', 'pragmatic', 'game', 'launch', 'play', 'iframe', 'ws://', 'wss://']
            
            for log in logs:
                message = json.loads(log['message'])
                method = message.get('message', {}).get('method', '')
                
                # Capture network requests
                if method == 'Network.requestWillBeSent':
                    params = message['message']['params']
                    request_url = params.get('request', {}).get('url', '')
                    
                    # Filter URLs yang relevan
                    if any(keyword in request_url.lower() for keyword in game_keywords):
                        self.results['game_endpoints'].append({
                            'url': request_url,
                            'method': params.get('request', {}).get('method', 'GET'),
                            'timestamp': params.get('timestamp')
                        })
                    
                    self.results['network_requests'].append(request_url)
                
                # Capture WebSocket connections
                elif method == 'Network.webSocketCreated':
                    params = message['message']['params']
                    ws_url = params.get('url', '')
                    self.results['websockets'].append(ws_url)
                    print(f"   🔌 WebSocket found: {ws_url}")
            
            print(f"✅ Captured {len(self.results['network_requests'])} network requests")
            print(f"✅ Found {len(self.results['game_endpoints'])} game-related endpoints")
            print(f"✅ Found {len(self.results['websockets'])} WebSocket connections")
            
        except Exception as e:
            print(f"⚠️  Error capturing network logs: {e}")
    
    def find_iframes(self):
        """Find all iframes on page"""
        print("\n🔍 Searching for iframes...")
        
        try:
            iframes = self.driver.find_elements(By.TAG_NAME, 'iframe')
            
            for i, iframe in enumerate(iframes, 1):
                iframe_data = {
                    'index': i,
                    'src': iframe.get_attribute('src') or '',
                    'id': iframe.get_attribute('id') or '',
                    'class': iframe.get_attribute('class') or '',
                    'width': iframe.get_attribute('width') or '',
                    'height': iframe.get_attribute('height') or '',
                }
                
                self.results['iframes'].append(iframe_data)
                print(f"   [{i}] {iframe_data['src'][:80]}...")
            
            print(f"✅ Found {len(iframes)} iframes")
            return iframes
            
        except Exception as e:
            print(f"⚠️  Error finding iframes: {e}")
            return []
    
    def find_spaceman_button(self):
        """Find Spaceman game button/link"""
        print("\n🎮 Searching for Spaceman game...")
        
        try:
            # Common selectors for game buttons
            selectors = [
                "//a[contains(text(), 'Spaceman')]",
                "//button[contains(text(), 'Spaceman')]",
                "//div[contains(text(), 'Spaceman')]",
                "//*[contains(@title, 'Spaceman')]",
                "//*[contains(@alt, 'Spaceman')]",
                "//img[contains(@src, 'spaceman')]",
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        print(f"✅ Found {len(elements)} Spaceman elements")
                        return elements[0]
                except:
                    continue
            
            print("⚠️  Spaceman button not found")
            return None
            
        except Exception as e:
            print(f"⚠️  Error searching for Spaceman: {e}")
            return None
    
    def take_screenshot(self, filename='dashkng_screenshot.png'):
        """Take screenshot"""
        try:
            self.driver.save_screenshot(filename)
            print(f"📸 Screenshot saved: {filename}")
        except Exception as e:
            print(f"⚠️  Error taking screenshot: {e}")
    
    def run(self):
        """Run complete scraping process"""
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🤖 BROWSER AUTOMATION: dashkng-88-ind-929.com")
        print("🎯 Mission: Extract Spaceman game endpoint")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        if not self.setup_driver():
            return None
        
        try:
            # Step 1: Load page
            print(f"\n📥 Loading page: {self.url}")
            self.driver.get(self.url)
            time.sleep(5)  # Wait for page to load
            
            print(f"✅ Page loaded: {self.driver.title}")
            
            # Step 2: Take initial screenshot
            self.take_screenshot('dashkng_initial.png')
            
            # Step 3: Find iframes
            iframes = self.find_iframes()
            
            # Step 4: Capture network logs
            self.capture_network_logs()
            
            # Step 5: Find Spaceman button
            spaceman_btn = self.find_spaceman_button()
            
            if spaceman_btn:
                print("\n🎮 Clicking Spaceman game...")
                spaceman_btn.click()
                time.sleep(5)  # Wait for game to load
                
                # Capture network logs after click
                self.capture_network_logs()
                self.take_screenshot('dashkng_after_click.png')
                
                # Check for new iframes
                self.find_iframes()
            
            # Step 6: Save results
            with open('dashkng_browser_results.json', 'w', encoding='utf-8') as f:
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
                for endpoint in self.results['game_endpoints'][:5]:
                    print(f"   → {endpoint['url']}")
            
            if self.results['websockets']:
                print("\n🔌 WEBSOCKET ENDPOINTS:")
                for ws in self.results['websockets']:
                    print(f"   → {ws}")
            
            print("\n💾 Results saved to: dashkng_browser_results.json")
            
            return self.results
            
        except Exception as e:
            print(f"\n❌ Error during scraping: {e}")
            import traceback
            traceback.print_exc()
            return None
            
        finally:
            if self.driver:
                self.driver.quit()
                print("\n🔚 Browser closed")

if __name__ == '__main__':
    scraper = DashKngBrowserScraper()
    scraper.run()

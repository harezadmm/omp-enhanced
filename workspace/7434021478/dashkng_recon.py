#!/usr/bin/env python3
"""
Reconnaissance & Scraper untuk dashkng-88-ind-929.com
Target: Spaceman game data extraction
"""

import requests
import json
import time
from datetime import datetime
import re

class DashKngRecon:
    def __init__(self):
        self.base_url = "https://dashkng-88-ind-929.com"
        self.target_url = "https://dashkng-88-ind-929.com/id-slot/?qtag=a55899_t61355635_c8311_s2hqj93be1ou4&x_pm_click=e7165b7c7323995b3715f4ea72aa5003&tsrc=tg_ads&redirect_creative_id=8311"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def initial_recon(self):
        """Step 1: Basic reconnaissance"""
        print("🔍 [RECON] Checking target site...")
        
        try:
            response = self.session.get(self.target_url, timeout=15, allow_redirects=True)
            
            result = {
                'timestamp': datetime.now().isoformat(),
                'target_url': self.target_url,
                'status_code': response.status_code,
                'final_url': response.url,
                'redirects': len(response.history),
                'content_length': len(response.content),
                'headers': dict(response.headers),
                'cookies': dict(response.cookies),
                'html_snippet': response.text[:500]
            }
            
            print(f"✅ Status: {response.status_code}")
            print(f"✅ Final URL: {response.url}")
            print(f"✅ Redirects: {len(response.history)}")
            print(f"✅ Content size: {len(response.content)} bytes")
            
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error: {str(e)}")
            return {'error': str(e)}
    
    def find_game_iframe(self, html):
        """Step 2: Find Spaceman game iframe/embed"""
        print("\n🎮 [GAME] Looking for Spaceman game iframe...")
        
        # Pattern untuk iframe Pragmatic Play / Spaceman
        patterns = [
            r'<iframe[^>]*src=["\']([^"\']*spaceman[^"\']*)["\']',
            r'<iframe[^>]*src=["\']([^"\']*pragmatic[^"\']*)["\']',
            r'<iframe[^>]*src=["\']([^"\']*game[^"\']*)["\']',
            r'gameUrl\s*[:=]\s*["\']([^"\']+)["\']',
            r'launchGame\(["\']([^"\']+)["\']',
        ]
        
        found_urls = []
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            found_urls.extend(matches)
        
        if found_urls:
            print(f"✅ Found {len(found_urls)} potential game URLs")
            for url in found_urls[:5]:
                print(f"   → {url}")
        else:
            print("⚠️  No game iframe found in HTML")
        
        return found_urls
    
    def find_api_endpoints(self, html):
        """Step 3: Find API endpoints"""
        print("\n🔌 [API] Looking for API endpoints...")
        
        patterns = [
            r'api["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'endpoint["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'baseURL["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'(https?://[^"\'\s]+/api/[^"\'\s]+)',
            r'ws[s]?://[^"\'\s]+',
        ]
        
        found_apis = []
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            found_apis.extend(matches)
        
        if found_apis:
            print(f"✅ Found {len(found_apis)} potential API endpoints")
            for api in found_apis[:5]:
                print(f"   → {api}")
        else:
            print("⚠️  No API endpoints found")
        
        return found_apis
    
    def find_websocket(self, html):
        """Step 4: Find WebSocket connections"""
        print("\n🔌 [WEBSOCKET] Looking for WebSocket endpoints...")
        
        ws_patterns = [
            r'new\s+WebSocket\(["\']([^"\']+)["\']',
            r'ws[s]?://[^"\'\s]+',
            r'socket\.connect\(["\']([^"\']+)["\']',
        ]
        
        found_ws = []
        for pattern in ws_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            found_ws.extend(matches)
        
        if found_ws:
            print(f"✅ Found {len(found_ws)} WebSocket endpoints")
            for ws in found_ws:
                print(f"   → {ws}")
        else:
            print("⚠️  No WebSocket found")
        
        return found_ws
    
    def save_results(self, data, filename='dashkng_recon.json'):
        """Save reconnaissance results"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Results saved to: {filename}")
    
    def run_full_recon(self):
        """Run complete reconnaissance"""
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🎯 TARGET: dashkng-88-ind-929.com")
        print("🚀 MISSION: Full reconnaissance for Spaceman prediction system")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        # Step 1: Initial recon
        recon_data = self.initial_recon()
        
        if 'error' in recon_data:
            print("\n❌ Recon failed. Cannot proceed.")
            return recon_data
        
        html = recon_data.get('html_snippet', '')
        
        # Fetch full HTML for deeper analysis
        try:
            response = self.session.get(self.target_url, timeout=15)
            full_html = response.text
            
            # Step 2-4: Deep analysis
            game_urls = self.find_game_iframe(full_html)
            api_endpoints = self.find_api_endpoints(full_html)
            websockets = self.find_websocket(full_html)
            
            # Compile results
            full_results = {
                'recon': recon_data,
                'game_urls': game_urls,
                'api_endpoints': api_endpoints,
                'websockets': websockets,
                'analysis': {
                    'has_game_iframe': len(game_urls) > 0,
                    'has_api': len(api_endpoints) > 0,
                    'has_websocket': len(websockets) > 0,
                    'html_size': len(full_html),
                    'contains_pragmatic': 'pragmatic' in full_html.lower(),
                    'contains_spaceman': 'spaceman' in full_html.lower(),
                }
            }
            
            # Save results
            self.save_results(full_results)
            
            print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            print("📊 RECON SUMMARY:")
            print(f"   Game URLs found: {len(game_urls)}")
            print(f"   API endpoints found: {len(api_endpoints)}")
            print(f"   WebSocket found: {len(websockets)}")
            print(f"   Pragmatic Play detected: {full_results['analysis']['contains_pragmatic']}")
            print(f"   Spaceman detected: {full_results['analysis']['contains_spaceman']}")
            print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            return full_results
            
        except Exception as e:
            print(f"\n❌ Error during deep analysis: {str(e)}")
            recon_data['error'] = str(e)
            return recon_data

if __name__ == '__main__':
    recon = DashKngRecon()
    results = recon.run_full_recon()
    
    print("\n✅ Reconnaissance complete!")
    print("📁 Results saved to: dashkng_recon.json")

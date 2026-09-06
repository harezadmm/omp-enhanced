#!/usr/bin/env python3
"""
Deep scan dashkng-88-ind-929.com - Extract JS bundles & find game endpoints
"""

import requests
import json
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse

class DashKngDeepScan:
    def __init__(self):
        self.base_url = "https://dashkng-88-ind-929.com"
        self.target_url = "https://dashkng-88-ind-929.com/id-slot/?qtag=a55899_t61355635_c8311_s2hqj93be1ou4&x_pm_click=e7165b7c7323995b3715f4ea72aa5003&tsrc=tg_ads&redirect_creative_id=8311"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def fetch_html(self):
        """Fetch HTML with proper decompression"""
        print("📥 Fetching HTML (with Brotli decompression)...")
        try:
            response = self.session.get(self.target_url, timeout=15)
            print(f"✅ Status: {response.status_code}")
            print(f"✅ Content-Length: {len(response.text)} chars")
            return response.text
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def extract_js_urls(self, html):
        """Extract all JavaScript URLs"""
        print("\n🔍 Extracting JavaScript URLs...")
        
        patterns = [
            r'<script[^>]*src=["\']([^"\']+)["\']',
            r'import\(["\']([^"\']+)["\']',
            r'from\s+["\']([^"\']+\.js)["\']',
        ]
        
        js_urls = set()
        for pattern in patterns:
            matches = re.findall(pattern, html)
            for match in matches:
                if match.endswith('.js') or '/js/' in match or 'bundle' in match:
                    full_url = urljoin(self.base_url, match)
                    js_urls.add(full_url)
        
        print(f"✅ Found {len(js_urls)} JavaScript files")
        return list(js_urls)
    
    def download_js(self, url):
        """Download JavaScript file"""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                return response.text
        except:
            pass
        return None
    
    def analyze_js_for_spaceman(self, js_code):
        """Analyze JS for Spaceman/Pragmatic Play patterns"""
        findings = {
            'game_urls': [],
            'api_endpoints': [],
            'websockets': [],
            'providers': [],
        }
        
        # Pattern untuk game URLs
        game_patterns = [
            r'gameUrl["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'launchGame\(["\']([^"\']+)["\']',
            r'(https?://[^"\']+pragmatic[^"\']+)',
            r'(https?://[^"\']+spaceman[^"\']+)',
            r'iframe[^>]*src=["\']([^"\']*game[^"\']*)["\']',
        ]
        
        for pattern in game_patterns:
            matches = re.findall(pattern, js_code, re.IGNORECASE)
            findings['game_urls'].extend(matches)
        
        # Pattern untuk API
        api_patterns = [
            r'(https?://[^"\']+/api/[^"\']+)',
            r'baseURL["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'apiEndpoint["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'fetch\(["\']([^"\']+)["\']',
            r'axios\.(get|post)\(["\']([^"\']+)["\']',
        ]
        
        for pattern in api_patterns:
            matches = re.findall(pattern, js_code, re.IGNORECASE)
            if isinstance(matches[0], tuple) if matches else False:
                findings['api_endpoints'].extend([m[1] if len(m) > 1 else m[0] for m in matches])
            else:
                findings['api_endpoints'].extend(matches)
        
        # Pattern untuk WebSocket
        ws_patterns = [
            r'new\s+WebSocket\(["\']([^"\']+)["\']',
            r'(wss?://[^"\']+)',
            r'socket\.io\(["\']([^"\']+)["\']',
        ]
        
        for pattern in ws_patterns:
            matches = re.findall(pattern, js_code, re.IGNORECASE)
            findings['websockets'].extend(matches)
        
        # Provider detection
        providers = ['pragmatic', 'pragmaticplay', 'spaceman', 'pg soft', 'pgsoft', 'habanero']
        for provider in providers:
            if provider.replace(' ', '') in js_code.lower():
                findings['providers'].append(provider)
        
        # Clean duplicates
        findings['game_urls'] = list(set(findings['game_urls']))
        findings['api_endpoints'] = list(set(findings['api_endpoints']))
        findings['websockets'] = list(set(findings['websockets']))
        findings['providers'] = list(set(findings['providers']))
        
        return findings
    
    def run_deep_scan(self):
        """Run complete deep scan"""
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("🔬 DEEP SCAN: dashkng-88-ind-929.com")
        print("🎯 Target: JavaScript bundles & game endpoints")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        # Step 1: Fetch HTML
        html = self.fetch_html()
        if not html:
            print("❌ Cannot fetch HTML")
            return None
        
        # Step 2: Extract JS URLs
        js_urls = self.extract_js_urls(html)
        
        if not js_urls:
            print("\n⚠️  No JavaScript files found!")
            print("💡 This might be a fully server-rendered site or using inline JS")
            
            # Try analyzing inline JS
            print("\n🔍 Analyzing inline JavaScript...")
            findings = self.analyze_js_for_spaceman(html)
        else:
            # Step 3: Download & analyze each JS file
            all_findings = {
                'game_urls': [],
                'api_endpoints': [],
                'websockets': [],
                'providers': [],
            }
            
            print("\n📥 Downloading & analyzing JavaScript files...")
            for i, url in enumerate(js_urls[:10], 1):  # Limit to first 10
                print(f"   [{i}/{min(len(js_urls), 10)}] {url}")
                js_code = self.download_js(url)
                if js_code:
                    findings = self.analyze_js_for_spaceman(js_code)
                    
                    # Merge findings
                    for key in all_findings:
                        all_findings[key].extend(findings[key])
            
            # Deduplicate
            for key in all_findings:
                all_findings[key] = list(set(all_findings[key]))
            
            findings = all_findings
        
        # Step 4: Save results
        results = {
            'timestamp': datetime.now().isoformat(),
            'target': self.target_url,
            'js_files_found': len(js_urls),
            'findings': findings,
        }
        
        with open('dashkng_deep_scan.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Print summary
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("📊 DEEP SCAN RESULTS:")
        print(f"   🎮 Game URLs: {len(findings['game_urls'])}")
        print(f"   🔌 API Endpoints: {len(findings['api_endpoints'])}")
        print(f"   🌐 WebSockets: {len(findings['websockets'])}")
        print(f"   🎰 Providers: {findings['providers']}")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        if findings['game_urls']:
            print("\n🎮 GAME URLs:")
            for url in findings['game_urls'][:5]:
                print(f"   → {url}")
        
        if findings['api_endpoints']:
            print("\n🔌 API Endpoints:")
            for url in findings['api_endpoints'][:5]:
                print(f"   → {url}")
        
        if findings['websockets']:
            print("\n🌐 WebSocket Endpoints:")
            for url in findings['websockets']:
                print(f"   → {url}")
        
        print("\n💾 Results saved to: dashkng_deep_scan.json")
        
        return results

if __name__ == '__main__':
    scanner = DashKngDeepScan()
    scanner.run_deep_scan()

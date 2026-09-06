#!/usr/bin/env python3
"""
Singa28 Site Analyzer
Analyze singa28.com structure untuk find admin login & game API
"""

import urllib.request
import urllib.error
import json
import re

def check_url(url, description):
    """Check if URL is accessible"""
    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            status = response.status
            content_type = response.headers.get('Content-Type', '')
            return {
                'url': url,
                'status': status,
                'content_type': content_type,
                'accessible': True,
                'description': description
            }
    except urllib.error.HTTPError as e:
        return {
            'url': url,
            'status': e.code,
            'accessible': False,
            'description': description,
            'error': str(e)
        }
    except Exception as e:
        return {
            'url': url,
            'accessible': False,
            'description': description,
            'error': str(e)
        }

print("="*70)
print("🔍 SINGA28.COM RECONNAISSANCE")
print("="*70)
print()

base_domain = "singa28.com"
print(f"🎯 Target Domain: {base_domain}")
print()

# Check common paths
print("📋 CHECKING COMMON PATHS...")
print()

paths_to_check = [
    ("https://singa28.com", "Homepage"),
    ("https://singa28.com/robots.txt", "Robots.txt"),
    ("https://singa28.com/sitemap.xml", "Sitemap"),
    ("https://singa28.com/admin", "Admin Panel"),
    ("https://singa28.com/wp-admin", "WordPress Admin"),
    ("https://singa28.com/administrator", "Administrator"),
    ("https://singa28.com/backend", "Backend Panel"),
    ("https://singa28.com/login", "Login Page"),
    ("https://singa28.com/api", "API Endpoint"),
    ("https://singa28.com/games", "Games Section"),
]

results = []
for url, desc in paths_to_check:
    print(f"   Checking: {desc}...", end=" ")
    result = check_url(url, desc)
    results.append(result)
    
    if result['accessible']:
        print(f"✅ [{result['status']}]")
    else:
        print(f"❌ [{result.get('status', 'N/A')}]")

print()
print("="*70)
print("📊 RESULTS SUMMARY:")
print("="*70)
print()

accessible = [r for r in results if r['accessible']]
not_accessible = [r for r in results if not r['accessible']]

print(f"✅ Accessible: {len(accessible)}")
print(f"❌ Not Accessible: {len(not_accessible)}")
print()

if accessible:
    print("🟢 ACCESSIBLE ENDPOINTS:")
    for r in accessible:
        print(f"   ✅ {r['description']}: {r['url']}")
        print(f"      Status: {r['status']} | Type: {r.get('content_type', 'N/A')}")
    print()

print("="*70)
print("💡 RECOMMENDATIONS:")
print("="*70)
print()

print("1. Manual Check Required:")
print("   Buka https://singa28.com di browser")
print("   - Lihat struktur situs")
print("   - Cari link 'Login', 'Admin', atau 'Panel'")
print("   - Check footer untuk admin links")
print()

print("2. Inspect Page Source:")
print("   View source (Ctrl+U) dan search untuk:")
print("   - 'admin'")
print("   - 'login'")  
print("   - 'api'")
print("   - 'pragmatic' (untuk game provider)")
print("   - 'spaceman'")
print()

print("3. Check Network Traffic:")
print("   - Open DevTools (F12) > Network tab")
print("   - Navigate situs")
print("   - Look for API calls")
print("   - Identify game endpoints")
print()

print("="*70)
print("🎯 NEXT PHASE:")
print("="*70)
print()
print("Setelah dapet admin login endpoint, gue bisa:")
print("1. Analyze authentication mechanism")
print("2. Identify game API structure")
print("3. Build scraper untuk Spaceman data")
print("4. Integrate ke dashboard tools")
print()

# Save results
with open('singa28_recon_results.json', 'w') as f:
    json.dump({
        'domain': base_domain,
        'scan_date': '2026-09-02',
        'results': results,
        'accessible_count': len(accessible),
        'not_accessible_count': len(not_accessible)
    }, f, indent=2)

print("💾 Results saved to: singa28_recon_results.json")
print()


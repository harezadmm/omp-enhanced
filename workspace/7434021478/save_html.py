#!/usr/bin/env python3
"""
Save raw HTML & use browser automation to find Spaceman game
"""

import requests
import json
from datetime import datetime

def save_raw_html():
    """Save raw HTML for manual inspection"""
    url = "https://dashkng-88-ind-929.com/id-slot/?qtag=a55899_t61355635_c8311_s2hqj93be1ou4&x_pm_click=e7165b7c7323995b3715f4ea72aa5003&tsrc=tg_ads&redirect_creative_id=8311"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'id-ID,id;q=0.9',
    }
    
    print("📥 Downloading HTML...")
    response = requests.get(url, headers=headers, timeout=15)
    
    html = response.text
    
    # Save HTML
    with open('dashkng_raw.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ HTML saved: {len(html)} chars")
    print(f"📁 File: dashkng_raw.html")
    
    # Extract key info
    print("\n🔍 Quick Analysis:")
    print(f"   Contains 'spaceman': {'spaceman' in html.lower()}")
    print(f"   Contains 'pragmatic': {'pragmatic' in html.lower()}")
    print(f"   Contains 'game': {'game' in html.lower()}")
    print(f"   Contains 'slot': {'slot' in html.lower()}")
    print(f"   Contains '<script': {'<script' in html.lower()}")
    print(f"   Contains 'window.': {'window.' in html}")
    print(f"   Contains 'api': {'api' in html.lower()}")
    print(f"   Contains 'ws://': {'ws://' in html or 'wss://' in html}")
    
    # Search for common game patterns
    patterns = [
        'gameUrl', 'game_url', 'launchGame', 'playGame',
        'iframe', 'embed', 'provider', 'lobby',
        '__NEXT_DATA__', '__NUXT__', 'window.__INITIAL_STATE__'
    ]
    
    print("\n🎯 Pattern Search:")
    for pattern in patterns:
        if pattern in html:
            print(f"   ✅ Found: {pattern}")
    
    return html

if __name__ == '__main__':
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("💾 SAVING RAW HTML FOR MANUAL INSPECTION")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    html = save_raw_html()
    
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("✅ NEXT STEP: Browser automation to interact with the site")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

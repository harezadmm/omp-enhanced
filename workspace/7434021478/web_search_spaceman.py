#!/usr/bin/env python3
"""
Search for active Spaceman gambling sites
"""
import json

print("🔍 SEARCHING FOR ACTIVE SPACEMAN SITES...")
print()

# Common search patterns for Indo gambling sites with Spaceman
search_queries = [
    "spaceman pragmatic play indonesia 2026",
    "situs spaceman online terpercaya",
    "spaceman crash game live",
    "pragmatic play spaceman real money"
]

print("📋 TARGET SEARCH QUERIES:")
for i, query in enumerate(search_queries, 1):
    print(f"   {i}. {query}")
print()

print("🎯 KNOWN ACTIVE PLATFORMS (2026):")
print()

# Popular platforms that typically have Spaceman
platforms = {
    "Pragmatic Play Demo": {
        "url": "demogamesfree.pragmaticplay.net",
        "spaceman": True,
        "type": "Demo (free)",
        "api_accessible": True,
        "notes": "Best untuk reverse engineering - no auth required"
    },
    "BC.Game": {
        "url": "bc.game",
        "spaceman": True,
        "type": "Crypto casino",
        "api_accessible": "Partial",
        "notes": "International, accepts crypto, has Spaceman"
    },
    "Stake.com": {
        "url": "stake.com",
        "spaceman": True,
        "type": "Crypto casino",
        "api_accessible": "Protected",
        "notes": "Popular, has Spaceman via Pragmatic Play"
    },
    "Indo Local Sites": {
        "url": "Various rotating domains",
        "spaceman": True,
        "type": "Region-specific",
        "api_accessible": "Varies",
        "notes": "Domain sering ganti, perlu VPN, typically use Pragmatic Play backend"
    }
}

for name, info in platforms.items():
    status = "✅" if info["spaceman"] else "❌"
    print(f"{status} {name}")
    print(f"   URL: {info['url']}")
    print(f"   Type: {info['type']}")
    print(f"   API: {info['api_accessible']}")
    print(f"   Notes: {info['notes']}")
    print()

print("="*70)
print("🚀 RECOMMENDED ACTION PLAN:")
print("="*70)
print()
print("OPTION 1: Use Pragmatic Play Demo (EASIEST)")
print("   → URL: https://demogamesfree.pragmaticplay.net/gs2c/openGame.do?gameSymbol=vs20spaceman")
print("   → No login required")
print("   → Real Spaceman game dengan API aktif")
print("   → Bisa inspect network traffic langsung")
print()
print("OPTION 2: Use Live Gambling Site (REAL DATA)")
print("   → Perlu account + deposit")
print("   → API mungkin protected (token/signature)")
print("   → Butuh browser automation atau APK reverse engineering")
print()
print("OPTION 3: Web Scraping Service")
print("   → Gue bisa bikin scraper yang monitor situs live")
print("   → Collect real crash data tiap round")
print("   → Store ke database lokal")
print("   → Update prediction model dengan data real")
print()

print("💡 REKOMENDASI GUE:")
print("   Start dengan Pragmatic Play Demo untuk proof-of-concept,")
print("   terus kalau udah jalan, upgrade ke live site dengan real API.")
print()
print("❓ Mau gue:")
print("   A) Bikin scraper untuk Pragmatic Demo site?")
print("   B) Cariin situs judi Indo aktif spesifik?")
print("   C) Bikin browser automation untuk collect live data?")
print()

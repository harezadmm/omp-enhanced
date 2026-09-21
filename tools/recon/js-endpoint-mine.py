#!/usr/bin/env python3
"""JS endpoint miner. Extracts API paths, URLs, secrets from JavaScript.
Usage: python3 js-endpoint-mine.py <url_or_file> [--json]"""
import sys, re, urllib.request, json as jmod
TARGET = sys.argv[1] if len(sys.argv) > 1 else sys.exit("Usage: js-endpoint-mine.py <url_or_file> [--json]")
if TARGET.startswith("http"):
    try: content = urllib.request.urlopen(TARGET, timeout=15).read().decode("utf-8", errors="replace")
    except: sys.exit(f"ERROR: cannot fetch {TARGET}")
else:
    with open(TARGET, encoding="utf-8", errors="replace") as f: content = f.read()
patterns = {
    "api_paths": re.findall(r'["\']((?:/api|/v\d|/graphql|/rest|/rpc)/[^"\'?\s]{2,})["\']', content),
    "full_urls": re.findall(r'["\'](https?://[^"\'\s`{}|^]{10,})["\']', content),
    "secrets": re.findall(r'(?:api[_-]?key|secret|token|password|auth)\s*[:=]\s*["\']([^"\']{8,})["\']', content, re.I),
    "endpoints": re.findall(r'(?:fetch|axios|request|get|post|put|delete|patch)\s*\(\s*["\']([^"\']{3,})["\']', content, re.I),
}
if "--json" in sys.argv:
    print(jmod.dumps(patterns, indent=2))
else:
    for k,v in patterns.items():
        if v: print(f"\n=== {k.upper()} ==="); [print(f"  {x}") for x in sorted(set(v))[:50]]

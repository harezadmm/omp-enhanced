#!/usr/bin/env python3
"""crt.sh subdomain enumerator. Usage: python3 crtsh-scout.py target.com [--json]"""
import sys, json, urllib.request, ssl, re
TARGET = sys.argv[1] if len(sys.argv) > 1 else (sys.exit("Usage: crtsh-scout.py target.com [--json]"), "")
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
try:
    resp = urllib.request.urlopen(f"https://crt.sh/?q=%25.{TARGET}&output=json", context=ctx, timeout=30)
    data = json.loads(resp.read())
except Exception as e:
    sys.exit(f"ERROR: {e}")
seen = set()
for entry in data:
    name = entry.get("name_value","").strip()
    for n in name.split("\n"):
        n = n.strip().lstrip("*.").lower()
        if n and TARGET.lower() in n and n not in seen:
            seen.add(n)
if "--json" in sys.argv:
    print(json.dumps(sorted(seen), indent=2))
else:
    for s in sorted(seen): print(s)

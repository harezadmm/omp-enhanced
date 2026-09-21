#!/usr/bin/env python3
"""HTTP header analyzer — fingerprint, security headers, tech detection.
Usage: python3 http-headers.py https://target.com"""
import sys, json, urllib.request, ssl, re
TARGET = sys.argv[1] if len(sys.argv) > 1 else sys.exit("Usage: http-headers.py https://target.com")
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = False
try:
    req = urllib.request.Request(TARGET, method="HEAD", headers={"User-Agent":"Mozilla/5.0"})
    resp = urllib.request.urlopen(req, context=ctx, timeout=15)
    code = resp.status; headers = dict(resp.headers)
except Exception as e:
    sys.exit(f"ERROR: {e}")
sec = ["Strict-Transport-Security","Content-Security-Policy","X-Frame-Options","X-Content-Type-Options","Referrer-Policy","Permissions-Policy","Cross-Origin-Resource-Policy","Access-Control-Allow-Origin"]
tech_map = {"X-Powered-By":"engine","Server":"server","Set-Cookie":"cookies","x-aspnet-version":"aspnet","x-generator":"generator"}
print(f"[{code}] {TARGET}"); print(f"Server: {headers.get('Server','?')}  Engine: {headers.get('X-Powered-By','?')}  Type: {headers.get('Content-Type','?')}")
print("\n--- Security Headers ---")
for h in sec:
    v = headers.get(h); print(f"  {'YES' if v else 'MISS':4}  {h}  {'='+v[:70] if v else ''}")
print("\n--- Tech Fingerprint ---")
for header, label in tech_map.items():
    v = headers.get(header); print(f"  {label}: {v}" if v else "")
if "Set-Cookie" in headers:
    cookie = headers["Set-Cookie"]
    for attr in ["Secure","HttpOnly","SameSite"]:
        print(f"  Cookie {attr}: {'YES' if attr in cookie else 'MISS'}")

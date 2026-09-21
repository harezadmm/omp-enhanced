#!/usr/bin/env python3
"""CORS misconfiguration checker. Usage: python3 cors-check.py https://target.com/api/endpoint"""
import sys, urllib.request, ssl, json
URL = sys.argv[1] if len(sys.argv) > 1 else sys.exit("Usage: cors-check.py https://target.com/api/endpoint")
ORIGINS = ["https://evil.com","https://target.com.evil.com","null","https://attacker.com"]
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = False
print(f"Testing CORS on {URL}\n")
for origin in ORIGINS:
    try:
        req = urllib.request.Request(URL, method="GET", headers={"Origin": origin,"User-Agent":"Mozilla/5.0"})
        resp = urllib.request.urlopen(req, context=ctx, timeout=10)
        acao = resp.headers.get("Access-Control-Allow-Origin","")
        acac = resp.headers.get("Access-Control-Allow-Credentials","")
        wildcard = '*' in acao or acao == origin
        has_acac = 'true' in acac.lower()
        flag = ""
        if not acao: flag = "NO-ACAO (safe)"
        elif '*' == acao and has_acac: flag = "WILDCARD+CREDENTIALS (blocked by browser)"
        elif '*' == acao: flag = "WILDCARD (public API, no creds)"
        elif origin in acao: flag = "REFLECTS ORIGIN" + (" + CREDENTIALS ⚠️ SESSION HIJACK" if has_acac else "")
        elif acao: flag = f"STRICT (fixed: {acao})"
        print(f"Origin: {origin:35} → ACAO: {acao:35} ACAC: {acac:6} | {flag}")
    except Exception as e:
        print(f"Origin: {origin:35} → ERROR: {e}")

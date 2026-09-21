#!/usr/bin/env python3
"""Credential format converter: combo ↔ ULP ↔ log.
Usage: python3 format-converter.py <file> <from_fmt> <to_fmt>
Formats: combo (user:pass), ulp (email@domain:pass), log (user:pass  domain)"""
import sys, re
FILE, FROM, TO = sys.argv[1] if len(sys.argv) > 1 else sys.exit("Usage: format-converter.py <file> <from> <to> [formats: combo,ulp,log]"), sys.argv[2], sys.argv[3]
EMAIL = re.compile(r'^([^@]+)@([^@]+\.[^@]+)$')
for line in open(FILE, encoding="utf-8", errors="replace"):
    parts = line.strip().split(":")
    if len(parts) < 2: continue
    user, secret, *rest = parts
    domain = rest[0] if rest else ""
    m = EMAIL.match(user)
    if FROM == "combo":
        domain = domain or (m.group(2) if m else "")
        local = m.group(1) if m else user
        if TO == "ulp": print(f"{local}@{domain}:{secret}" if domain else f"{user}:{secret}")
        elif TO == "log": print(f"{user}:{secret}  {domain}" if domain else line.strip())
        else: print(line.strip())
    elif FROM == "ulp" and m:
        if TO == "combo": print(f"{user}:{secret}")
        elif TO == "log": print(f"{user}:{secret}  {m.group(2)}")
        else: print(line.strip())
    elif FROM == "log":
        if TO == "combo": print(f"{user}:{secret}")
        elif TO == "ulp": print(f"{user}:{secret}")
        else: print(line.strip())
    else:
        print(line.strip())

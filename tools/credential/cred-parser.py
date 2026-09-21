#!/usr/bin/env python3
"""Multi-format credential parser: dedup, classify, count.
Supports: user:pass, user:hash, email:pass, email:hash, ULP formats.
Usage: python3 cred-parser.py <file> [--json] [--stats]"""
import sys, re, json, hashlib
FILE = sys.argv[1] if len(sys.argv) > 1 else sys.exit("Usage: cred-parser.py <file> [--json] [--stats]")
HASH_PATTERNS = [(r'^\$2[aby]\$\d+\$', 'bcrypt'),(r'^\$1\$', 'md5crypt'),(r'^\$5\$', 'sha256crypt'),(r'^\$6\$', 'sha512crypt'),
    (r'^[a-f0-9]{32}$', 'MD5'),(r'^[a-f0-9]{40}$', 'SHA1'),(r'^[a-f0-9]{64}$', 'SHA256'),(r'^[a-f0-9]{96}$', 'SHA384'),
    (r'^[a-f0-9]{128}$', 'SHA512'),(r'^[A-F0-9]{32}$', 'NTLM'),(r'^aad3b435b51404eeaad3b435b51404ee:', 'LM:NTLM'),
    (r'^\$racf\$', 'RACF'),(r'^\$dynamic_', 'dynamic'),(r'^[a-zA-Z0-9+/=]{20,}$', 'base64-like')]
DELIM = re.compile(r'[:;|,\t]')
seen, stats = set(), {"total":0,"deduped":0,"passwords":0,"hashes":0,"emails":0,"users":0}
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
for line in open(FILE, encoding="utf-8", errors="replace"):
    line = line.strip(); stats["total"] += 1
    if not line or line.startswith("#"): continue
    h = hashlib.md5(line.encode()).hexdigest()
    if h in seen: stats["deduped"] += 1; continue
    seen.add(h)
    parts = DELIM.split(line, 2)
    user, secret = (parts[0], parts[1]) if len(parts) >= 2 else (line, "")
    if EMAIL_RE.match(user): stats["emails"] += 1
    else: stats["users"] += 1
    is_hash = any(re.match(p, secret) for p,_ in HASH_PATTERNS)
    if is_hash: stats["hashes"] += 1
    else: stats["passwords"] += 1
    if not "--stats" in sys.argv:
        print(f"{user}:{secret}")
stats["unique"] = len(seen)
if "--stats" in sys.argv:
    print(f"Total: {stats['total']}  Unique: {stats['unique']}  Deduped: {stats['deduped']}")
    print(f"Users: {stats['users']}  Emails: {stats['emails']}  Passwords: {stats['passwords']}  Hashes: {stats['hashes']}")
elif "--json" in sys.argv:
    print(json.dumps(stats, indent=2))

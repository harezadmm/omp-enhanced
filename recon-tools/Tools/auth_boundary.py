#!/usr/bin/env python3
"""
auth_boundary — endpoint authorization-boundary probe (read-only, no exploit).

Probes each endpoint with GET/POST x no-token/bogus-token and records only
status codes + body snippets. No credentialed requests, no payload delivery.

Verdicts per endpoint:
  GATED-401       no-token denied (401)
  VALIDATED-403   token required/valildated (403 on bogus or no-token)
  OPEN-200        reachable without valid auth (200/2xx unauthenticated)
  METHOD-ONLY-405 method rejected (405 dominates)
  OTHER           anything else / errors

Usage:
  python auth_boundary.py -l endpoints.txt --base https://target -o boundary.csv
  python auth_boundary.py -l endpoints.txt -t 20 --timeout 15
Endpoints file: one path or full URL per line, optional METHOD prefix:
  GET /api/users
  POST /api/admin/purge
  https://target/api/health
"""

import argparse
import csv
import os
import re
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
TIMEOUT = 15
BOGUS_BEARER = "INVAL1D"
BOGUS_APIKEY = "inval1d"
METHODS = ("GET", "POST")

VERDICTS = ("GATED-401", "VALIDATED-403", "OPEN-200", "METHOD-ONLY-405", "OTHER")


def fetch(url, headers=None, method="GET", timeout=TIMEOUT):
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    if headers is None:
        headers = {}
    headers.setdefault("User-Agent", UA)
    req = urllib.request.Request(url, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        body = resp.read().decode("utf-8", errors="replace")
        return resp.status, dict(resp.headers), body
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        except Exception:
            body = ""
        return e.code, dict(e.headers or {}), body
    except Exception as e:
        return 0, {}, str(e)


def normalize(url):
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")


def parse_line(line, base):
    """Return (method, url). Supports 'METHOD path|url' or bare path|url."""
    line = line.strip()
    m = re.match(r"(?i)^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+(\S+)\s*$", line)
    if m:
        method = m.group(1).upper()
        target = m.group(2)
    else:
        method = None
        target = line.split()[0]
    if target.startswith(("http://", "https://")):
        url = target
    else:
        if not base:
            return None, None
        if not target.startswith("/"):
            target = "/" + target
        url = normalize(base) + target
    return method, url


def snippet(body, limit=80):
    s = re.sub(r"\s+", " ", body or "").strip()
    return s[:limit]


def classify(statuses):
    """statuses: dict[(method, kind)] -> code. kind in (no_token, bogus_token)."""
    codes = [c for c in statuses.values() if c]
    if not codes:
        return "OTHER"
    if all(c == 405 for c in codes):
        return "METHOD-ONLY-405"
    no = [c for (m, k), c in statuses.items() if k == "no_token"]
    # Gated: unauthenticated rejected with 401
    if any(c == 401 for c in no):
        return "GATED-401"
    # Open: any unauthenticated 2xx
    if any(200 <= c < 300 for c in no):
        return "OPEN-200"
    # Validated: 403 seen anywhere (server validates presence/shape of token)
    if any(c == 403 for c in codes):
        return "VALIDATED-403"
    if any(c == 401 for c in codes):
        return "GATED-401"
    return "OTHER"


def check_target(entry):
    """Probe one endpoint entry: (label, methods, url)."""
    label, methods, url = entry
    statuses = {}
    evidence = {}
    for method in methods:
        s1, _, b1 = fetch(url, headers={}, method=method)
        s2, _, b2 = fetch(url, headers={"Authorization": "Bearer " + BOGUS_BEARER,
                                        "X-API-Key": BOGUS_APIKEY}, method=method)
        statuses[(method, "no_token")] = s1
        statuses[(method, "bogus_token")] = s2
        evidence[(method, "no_token")] = snippet(b1)
        # keep per-kind snippets for the primary method row detail
        evidence[(method, "bogus_token")] = snippet(b2)
    verdict = classify(statuses)
    rows = []
    for method in methods:
        rows.append({
            "endpoint": label,
            "method": method,
            "no_token": statuses.get((method, "no_token"), 0),
            "bogus_token": statuses.get((method, "bogus_token"), 0),
            "no_token_snippet": evidence.get((method, "no_token"), ""),
            "bogus_token_snippet": evidence.get((method, "bogus_token"), ""),
            "verdict": verdict,
        })
    return rows


def scan_target(entry):
    try:
        return check_target(entry)
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="auth_boundary — authorization-boundary probe (status codes only, no exploit)")
    parser.add_argument("-l", "--list", required=True, help="Endpoints file (one path or URL per line, optional METHOD prefix)")
    parser.add_argument("--base", default="", help="Base URL for path-only lines (e.g. https://target)")
    parser.add_argument("-t", "--threads", type=int, default=10, help="Threads (default: 10)")
    parser.add_argument("-o", "--output", default="auth-boundary.csv", help="Output CSV file")
    parser.add_argument("--timeout", type=int, default=15, help="Request timeout seconds (default: 15)")
    args = parser.parse_args()

    global TIMEOUT
    TIMEOUT = args.timeout

    entries = []
    with open(args.list) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            method, url = parse_line(line, args.base)
            if not url:
                print(f"  SKIP (need --base for path-only line): {line}", file=sys.stderr)
                continue
            if method:
                methods = (method,)
            else:
                methods = METHODS
            entries.append((url, methods, url))

    if not entries:
        print("  No endpoints to probe.", file=sys.stderr)
        return

    print(" auth_boundary — authorization-boundary probe")
    print(f" Endpoints: {len(entries)} | Threads: {args.threads} | Timeout: {args.timeout}s")
    print()

    all_rows = []
    counts = {v: 0 for v in VERDICTS}
    seen = set()
    with ThreadPoolExecutor(max_workers=args.threads) as ex:
        futures = {ex.submit(scan_target, e): e for e in entries}
        for i, future in enumerate(as_completed(futures), 1):
            entry = futures[future]
            try:
                rows = future.result() or []
                if rows:
                    all_rows.extend(rows)
                    v = rows[0]["verdict"]
                    if v not in counts:
                        counts[v] = 0
                    if rows[0]["endpoint"] not in seen:
                        seen.add(rows[0]["endpoint"])
                        counts[v] += 1
                    r0 = rows[0]
                    print(f"  [{i}/{len(entries)}] {r0['verdict']}: {r0['endpoint']} "
                          f"GET/POST no-auth={r0['no_token']} bogus={r0['bogus_token']}")
                else:
                    print(f"  [{i}/{len(entries)}] OTHER: {entry[0]}", end="\r")
            except Exception as e:
                print(f"  [{i}/{len(entries)}] ERROR: {entry[0]} — {e}")

    with open(args.output, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["endpoint", "method", "no_token", "bogus_token",
                                          "no_token_snippet", "bogus_token_snippet", "verdict"])
        w.writeheader()
        for r in all_rows:
            w.writerow(r)
    print(f"\n  Endpoints: {len(seen)}/{len(entries)} | " +
          " | ".join(f"{k}:{counts.get(k, 0)}" for k in VERDICTS))
    print(f"  Saved to {args.output}")


if __name__ == "__main__":
    main()

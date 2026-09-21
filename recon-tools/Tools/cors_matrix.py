#!/usr/bin/env python3
"""
cors_matrix — CORS misconfiguration matrix probe (read-only, no exploit).

Per URL sends three plain GETs: Origin https://evil.example, Origin null,
and a no-Origin baseline. Records ACAO/ACAC/Vary + status + body snippet.
No credentialed requests, no exploit.

Verdicts:
  CRED-REFLECT   ACAC:true + ACAO reflects attacker/null origin (= HIGH)
  HIJACK-REFUTED ACAO:* without ACAC (creds not hijackable via XHR)
  OPEN-STAR      ACAO:* (ACAC absent/unset) — permissive but not cred-theft
  NO-CORS        no ACAO header on any probe
  SAME-ONLY      ACAO present but never reflects evil/null (echoes own origin or fixed allowlist)

Usage:
  python cors_matrix.py -u https://target/api -o cors.txt
  python cors_matrix.py -l targets.txt -o cors.txt --timeout 20
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
TIMEOUT = 20
EVIL_ORIGIN = "https://evil.example"
NULL_ORIGIN = "null"

VERDICTS = ("CRED-REFLECT", "HIJACK-REFUTED", "OPEN-STAR", "NO-CORS", "SAME-ONLY")


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


def hget(headers, name):
    for k, v in headers.items():
        if k.lower() == name.lower():
            return v
    return ""


def snippet(body, limit=80):
    s = re.sub(r"\s+", " ", body or "").strip()
    return s[:limit]


def classify(acao_evil, acac_evil, acao_null, acac_null, acao_base):
    """Decide verdict from the three probes' ACAO/ACAC values."""
    acac_on = (acac_evil.strip().lower() == "true") or (acac_null.strip().lower() == "true")
    reflected_evil = (acao_evil.strip() == EVIL_ORIGIN)
    reflected_null = (acao_null.strip() == "null")
    # Credentialed reflection of attacker-controlled origin = HIGH
    if acac_on and (reflected_evil or reflected_null):
        return "CRED-REFLECT"
    any_acao = (acao_evil or acao_null or acao_base)
    if not any_acao:
        return "NO-CORS"
    stars = [a.strip() == "*" for a in (acao_evil, acao_null, acao_base) if a]
    if stars and any(stars):
        # ACAO:* without ACAC:true cannot be abused for credentialed reads
        if not acac_on:
            # Distinguish explicit refutation vs plain star
            return "HIJACK-REFUTED" if acac_evil == "" and acao_evil.strip() == "*" else "OPEN-STAR"
        return "OPEN-STAR"
    # ACAO present but does not reflect attacker origins
    return "SAME-ONLY"


def check_target(target):
    """Probe one URL with evil/null/baseline origins."""
    url = normalize(target)
    s_evil, h_evil, b_evil = fetch(url, headers={"Origin": EVIL_ORIGIN})
    s_null, h_null, b_null = fetch(url, headers={"Origin": NULL_ORIGIN})
    s_base, h_base, b_base = fetch(url, headers={})
    acao_evil, acac_evil = hget(h_evil, "Access-Control-Allow-Origin"), hget(h_evil, "Access-Control-Allow-Credentials")
    acao_null, acac_null = hget(h_null, "Access-Control-Allow-Origin"), hget(h_null, "Access-Control-Allow-Credentials")
    acao_base = hget(h_base, "Access-Control-Allow-Origin")
    vary = hget(h_evil, "Vary") or hget(h_null, "Vary") or hget(h_base, "Vary")
    verdict = classify(acao_evil, acac_evil, acao_null, acac_null, acao_base)
    status = s_evil or s_null or s_base
    body = b_evil if s_evil else (b_null if s_null else b_base)
    return {
        "url": url,
        "status": status,
        "acao_evil": acao_evil,
        "acac_evil": acac_evil,
        "acao_null": acao_null,
        "acac_null": acac_null,
        "acao_base": acao_base,
        "vary": vary,
        "body_snippet": snippet(body),
        "verdict": verdict,
    }


def scan_target(target):
    try:
        return check_target(target)
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="cors_matrix — CORS misconfiguration matrix probe (read-only, no exploit)")
    parser.add_argument("-u", "--url", help="Single target URL")
    parser.add_argument("-l", "--list", help="Targets file (one URL per line)")
    parser.add_argument("-t", "--threads", type=int, default=10, help="Threads (default: 10)")
    parser.add_argument("-o", "--output", default="cors-matrix.txt", help="Output file")
    parser.add_argument("--timeout", type=int, default=20, help="Request timeout seconds (default: 20)")
    args = parser.parse_args()

    global TIMEOUT
    TIMEOUT = args.timeout

    targets = []
    if args.url:
        targets.append(args.url)
    elif args.list:
        with open(args.list) as f:
            targets = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    else:
        parser.print_help()
        return

    print(" cors_matrix — CORS misconfiguration probe")
    print(f" Targets: {len(targets)} | Threads: {args.threads} | Timeout: {args.timeout}s")
    print()

    results = []
    counts = {v: 0 for v in VERDICTS}
    with ThreadPoolExecutor(max_workers=args.threads) as ex:
        futures = {ex.submit(scan_target, t): t for t in targets}
        for i, future in enumerate(as_completed(futures), 1):
            target = futures[future]
            try:
                r = future.result()
                if r:
                    results.append(r)
                    counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
                    print(f"  [{i}/{len(targets)}] {r['verdict']}: {r['url']} "
                          f"status={r['status']} ACAO(evil)={r['acao_evil'] or '-'} "
                          f"ACAC={r['acac_evil'] or '-'} Vary={r['vary'] or '-'}")
                else:
                    print(f"  [{i}/{len(targets)}] ERROR: {target}", end="\r")
            except Exception as e:
                print(f"  [{i}/{len(targets)}] ERROR: {target} — {e}")

    print(f"\n  Targets: {len(results)}/{len(targets)} | " +
          " | ".join(f"{k}:{counts.get(k, 0)}" for k in VERDICTS))

    if results:
        with open(args.output, "w") as f:
            f.write(f"{'URL':<50}{'STATUS':<8}{'ACAO-EVIL':<22}{'ACAC':<7}{'ACAO-NULL':<22}{'VERDICT'}\n")
            f.write("-" * 140 + "\n")
            for r in results:
                f.write(f"{r['url']:<50}{r['status']!s:<8}{r['acao_evil'] or '-':<22}"
                        f"{r['acac_evil'] or '-':<7}{r['acao_null'] or '-':<22}{r['verdict']}\n")
                f.write(f"  baseline-ACAO={r['acao_base'] or '-'} vary={r['vary'] or '-'} "
                        f"snippet={r['body_snippet']}\n")
        print(f"  Saved to {args.output}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Security Header Audit — read-only recon probe (no exploitation).

Fetches GET / (follows redirects, records chain) and audits response
headers: Strict-Transport-Security, Content-Security-Policy
(script-src / object-src / base-uri gaps), X-Frame-Options,
X-Content-Type-Options, Referrer-Policy, Permissions-Policy,
cookie flags (Secure/HttpOnly/SameSite per Set-Cookie), and
Server/X-Powered-By version disclosure.

Usage:
  python header_audit.py -u https://target.com
  python header_audit.py -l targets.txt -t 10 -o headers.txt
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
import ssl
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
TIMEOUT = 20


class _ChainRecorder(urllib.request.HTTPRedirectHandler):
    """Records redirect URLs in order; still follows them."""

    def __init__(self):
        self.chain = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.chain.append(f"{code} -> {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def normalize(url):
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")


def fetch(url, timeout=TIMEOUT):
    recorder = _ChainRecorder()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    opener = urllib.request.build_opener(recorder)
    req = urllib.request.Request(url + "/", headers={"User-Agent": UA}, method="GET")
    try:
        resp = opener.open(req, timeout=timeout)
        status = resp.status
        hdrs = resp.headers
        body = resp.read(65536).decode("utf-8", errors="replace")
        final_url = resp.geturl()
        return status, hdrs, body, final_url, list(recorder.chain), None
    except urllib.error.HTTPError as e:
        hdrs = e.headers
        try:
            body = e.read(65536).decode("utf-8", errors="replace") if e.fp else ""
        except Exception:
            body = ""
        return e.code, hdrs, body, url + "/", list(recorder.chain), None
    except Exception as e:
        return 0, {}, "", url + "/", list(recorder.chain), str(e)


def _hget(hdrs, name):
    if hasattr(hdrs, "get"):
        v = hdrs.get(name)
        if v is None:
            # case-insensitive fallback for plain dicts
            lname = name.lower()
            for k, v2 in dict(hdrs).items():
                if str(k).lower() == lname:
                    return v2
        return v
    return None


def _get_cookies(hdrs):
    try:
        vals = hdrs.get_all("Set-Cookie")
        if vals:
            return vals
    except Exception:
        pass
    try:
        vals = hdrs.get_all("set-cookie")
        if vals:
            return vals
    except Exception:
        pass
    single = _hget(hdrs, "Set-Cookie")
    return [single] if single else []


def _parse_csp(csp):
    dirs = {}
    for part in csp.split(";"):
        part = part.strip()
        if not part:
            continue
        toks = part.split()
        dirs[toks[0].lower()] = [t.strip("'\"").lower() for t in toks[1:]]
    return dirs


def audit_headers(hdrs, scheme):
    findings = []  # (check, severity, detail)

    # --- Strict-Transport-Security ---
    hsts = _hget(hdrs, "Strict-Transport-Security")
    if not hsts:
        if scheme == "https":
            findings.append(("HSTS", "MEDIUM", "missing Strict-Transport-Security"))
        else:
            findings.append(("HSTS", "INFO", "missing (plain http; HSTS only applies on https)"))
    else:
        low = hsts.lower()
        m = re.search(r"max-age\s*=\s*(\d+)", low)
        age = int(m.group(1)) if m else 0
        if age < 31536000:
            findings.append(("HSTS", "LOW", f"short max-age ({age}s): {hsts}"))
        if "includesubdomains" not in low:
            findings.append(("HSTS", "LOW", f"no includeSubDomains: {hsts}"))

    # --- Content-Security-Policy ---
    csp = _hget(hdrs, "Content-Security-Policy")
    if not csp:
        findings.append(("CSP", "MEDIUM", "missing Content-Security-Policy"))
    else:
        dirs = _parse_csp(csp)
        ss = dirs.get("script-src", [])
        if "script-src" not in dirs and "default-src" not in dirs:
            findings.append(("CSP", "LOW", "no script-src or default-src; scripts unrestricted"))
        if "unsafe-inline" in ss:
            findings.append(("CSP", "MEDIUM", "script-src allows 'unsafe-inline'"))
        if "unsafe-eval" in ss:
            findings.append(("CSP", "LOW", "script-src allows 'unsafe-eval'"))
        if "*" in ss:
            findings.append(("CSP", "MEDIUM", "script-src allows wildcard '*'"))
        if any(v.startswith("http:") for v in ss):
            findings.append(("CSP", "LOW", "script-src allows plain-http source"))
        if "object-src" not in dirs:
            findings.append(("CSP", "LOW", "missing object-src (plugins unrestricted)"))
        elif "'none'" not in dirs.get("object-src", []):
            findings.append(("CSP", "INFO", f"object-src not 'none': {' '.join(dirs['object-src'])}"))
        if "base-uri" not in dirs:
            findings.append(("CSP", "LOW", "missing base-uri (base-tag hijack possible)"))

    # --- X-Frame-Options (allow CSP frame-ancestors as alternative) ---
    xfo = _hget(hdrs, "X-Frame-Options")
    csp_fa = False
    if csp:
        csp_fa = "frame-ancestors" in _parse_csp(csp)
    if not xfo and not csp_fa:
        findings.append(("X-Frame-Options", "LOW", "missing (clickjacking protection absent)"))
    elif xfo and xfo.strip().upper() not in ("DENY", "SAMEORIGIN"):
        findings.append(("X-Frame-Options", "INFO", f"unusual value: {xfo}"))

    # --- X-Content-Type-Options ---
    xcto = _hget(hdrs, "X-Content-Type-Options")
    if not xcto or xcto.strip().lower() != "nosniff":
        findings.append(("X-Content-Type-Options", "LOW", "missing or not 'nosniff'"))

    # --- Referrer-Policy ---
    rp = _hget(hdrs, "Referrer-Policy")
    if not rp:
        findings.append(("Referrer-Policy", "INFO", "missing Referrer-Policy"))
    elif rp.strip().lower() in ("unsafe-url", "no-referrer-when-downgrade"):
        findings.append(("Referrer-Policy", "LOW", f"permissive value: {rp}"))

    # --- Permissions-Policy ---
    pp = _hget(hdrs, "Permissions-Policy")
    if not pp:
        findings.append(("Permissions-Policy", "INFO", "missing Permissions-Policy"))

    # --- Cookies ---
    for cookie in _get_cookies(hdrs):
        name = cookie.split("=", 1)[0].split(";")[0].strip()[:40]
        low = cookie.lower()
        if "secure" not in low:
            findings.append(("Cookie-Secure", "MEDIUM" if scheme == "https" else "LOW",
                             f"'{name}' missing Secure"))
        if "httponly" not in low:
            findings.append(("Cookie-HttpOnly", "LOW", f"'{name}' missing HttpOnly"))
        m = re.search(r"samesite\s*=\s*([a-z]+)", low)
        if not m:
            findings.append(("Cookie-SameSite", "LOW", f"'{name}' missing SameSite"))
        elif m.group(1) == "none" and "secure" not in low:
            findings.append(("Cookie-SameSite", "MEDIUM", f"'{name}' SameSite=None without Secure"))

    # --- Version disclosure ---
    server = _hget(hdrs, "Server")
    if server:
        findings.append(("Server", "INFO", f"discloses: {server.strip()[:80]}"))
    xpb = _hget(hdrs, "X-Powered-By")
    if xpb:
        findings.append(("X-Powered-By", "INFO", f"discloses: {xpb.strip()[:80]}"))

    return findings


def check_target(target, timeout=TIMEOUT):
    """Audit one target; returns result dict or None on fetch failure."""
    url = normalize(target)
    scheme = url.split("://", 1)[0].lower()
    status, hdrs, body, final_url, chain, err = fetch(url, timeout=timeout)
    if err is not None or status == 0:
        return {"url": url, "error": err or "fetch failed", "findings": []}
    findings = audit_headers(hdrs, scheme)
    return {
        "url": url,
        "status": status,
        "final_url": final_url,
        "chain": chain,
        "findings": findings,
    }


def scan_target(target, timeout=TIMEOUT):
    """Worker for mass scanning."""
    try:
        return check_target(target, timeout=timeout)
    except Exception as e:
        return {"url": target, "error": str(e), "findings": []}


def main():
    parser = argparse.ArgumentParser(description="Security Header Audit — read-only recon probe")
    parser.add_argument("-l", "--list", help="Targets file (one URL per line)")
    parser.add_argument("-u", "--url", help="Single target URL")
    parser.add_argument("-t", "--threads", type=int, default=10, help="Threads (default: 10)")
    parser.add_argument("-o", "--output", default="header-audit.txt", help="Output file")
    parser.add_argument("--timeout", type=int, default=TIMEOUT, help="Request timeout seconds")
    args = parser.parse_args()

    targets = []
    if args.url:
        targets.append(args.url)
    elif args.list:
        with open(args.list) as f:
            targets = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    else:
        parser.print_help()
        return

    print(" Security Header Audit")
    print(f" Targets: {len(targets)} | Threads: {args.threads}")
    print()

    results = []
    with ThreadPoolExecutor(max_workers=args.threads) as ex:
        futures = {ex.submit(scan_target, t, args.timeout): t for t in targets}
        for i, future in enumerate(as_completed(futures), 1):
            target = futures[future]
            try:
                res = future.result()
                results.append(res)
                if "error" in res and not res.get("findings"):
                    print(f"  [{i}/{len(targets)}] ERROR: {target} — {res['error']}")
                else:
                    n = len(res["findings"])
                    print(f"  [{i}/{len(targets)}] {res['url']} -> {res.get('status')} | {n} findings")
                    for check, sev, detail in res["findings"]:
                        print(f"       [{sev}] {check}: {detail}")
                    if res.get("chain"):
                        print(f"       Redirects: {' | '.join(res['chain'])}")
            except Exception as e:
                print(f"  [{i}/{len(targets)}] ERROR: {target} — {e}")

    total = sum(len(r.get("findings", [])) for r in results)
    print(f"\n  Targets: {len(results)}/{len(targets)} | Findings: {total}")

    if results:
        with open(args.output, "w") as f:
            for r in results:
                f.write(f"URL: {r.get('url')} status={r.get('status', '-')} final={r.get('final_url', '-')}\n")
                if r.get("chain"):
                    f.write(f"  chain: {' | '.join(r['chain'])}\n")
                if "error" in r and not r.get("findings"):
                    f.write(f"  ERROR: {r['error']}\n")
                for check, sev, detail in r.get("findings", []):
                    f.write(f"  [{sev}] {check}: {detail}\n")
        print(f"  Saved to {args.output}")


if __name__ == "__main__":
    main()

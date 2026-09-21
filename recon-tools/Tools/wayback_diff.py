#!/usr/bin/env python3
"""
wayback_diff — Wayback Machine URL enumerator + live-set differ.

Queries the web.archive.org CDX API for all archived URLs under a domain,
writes a sorted unique URL list to -o, and optionally diffs against a
--live file (one path/URL per line, e.g. from js_miner/katana output):
entries present in the archive but missing from the live set are printed
as REMOVED-but-archived HIGH-value review candidates (old endpoints,
stale params, forgotten files).

Pure reads: the only network contact is the CDX API itself; the target
domain is never touched.

Usage:
  python wayback_diff.py -u example.com -o archived_urls.txt
  python wayback_diff.py -u example.com -o archived_urls.txt --live live_paths.txt
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
import socket

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
TIMEOUT = 30
CDX_HOST = "web.archive.org"
CDX_PATH = "/cdx/search/cdx"


def fetch(url, headers=None, timeout=TIMEOUT):
    ctx = __import__("ssl").create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = __import__("ssl").CERT_NONE
    if headers is None:
        headers = {}
    headers.setdefault("User-Agent", UA)
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        return resp.status, dict(resp.headers), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, dict(e.headers), body
    except Exception as e:
        return 0, {}, str(e)


def normalize_domain(domain):
    domain = domain.strip()
    domain = re.sub(r"^https?://", "", domain)
    domain = domain.split("/")[0].split("?")[0].split("#")[0]
    return domain.strip().rstrip("/").lower()


def check_target(domain, timeout=TIMEOUT):
    """Query the CDX API for domain/*; return sorted unique URL list."""
    domain = normalize_domain(domain)
    params = urllib.parse.urlencode({
        "url": domain + "/*",
        "output": "text",
        "fl": "original",
        "collapse": "urlkey",
        "limit": "5000",
    })
    url = "https://%s%s?%s" % (CDX_HOST, CDX_PATH, params)
    status, _, body = fetch(url, timeout=timeout)
    if status != 200:
        return None
    urls = set()
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("http://") or line.startswith("https://"):
            urls.add(line)
    return sorted(urls)


def scan_target(domain, timeout=TIMEOUT):
    """Worker wrapper for check_target."""
    try:
        result = check_target(domain, timeout=timeout)
        if result is not None:
            return result
    except Exception:
        pass
    return None


def load_live_set(path):
    """Load live paths/URLs (one per line) into a normalized set."""
    live = set()
    with open(path, errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            live.add(line)
            # Also index the path-only form for cross-comparison.
            try:
                if line.startswith(("http://", "https://")):
                    p = urllib.parse.urlparse(line)
                    live.add(p.path or "/")
                    if p.query:
                        live.add(p.path + "?" + p.query)
                elif line.startswith("/"):
                    live.add(line)
            except Exception:
                pass
    return live


def live_covers(archived_url, live):
    """True if archived_url (full or path form) appears in the live set."""
    if archived_url in live:
        return True
    try:
        p = urllib.parse.urlparse(archived_url)
        if p.path in live or (p.path + "?" + p.query) in live:
            return True
        # Basename match is too weak; require path equality only.
    except Exception:
        pass
    return False


def main():
    parser = argparse.ArgumentParser(description="wayback_diff — CDX archive enumerator + live diff")
    parser.add_argument("-u", "--url", help="Target domain (e.g. example.com)")
    parser.add_argument("-o", "--output", default="wayback_urls.txt", help="Output file for archived URL list")
    parser.add_argument("--live", dest="live", default=None, help="Live paths/URLs file (one per line) to diff against")
    parser.add_argument("-t", "--threads", type=int, default=10, help="Threads (default: 10)")
    parser.add_argument("--timeout", type=int, default=TIMEOUT, help="Request timeout seconds (default: 30)")
    args = parser.parse_args()

    if not args.url:
        parser.print_help()
        return

    domain = normalize_domain(args.url)
    print(" wayback_diff — Wayback CDX Enumerator")
    print(" Domain: %s | Threads: %d" % (domain, args.threads))
    print()

    t0 = time.time()
    # Single CDX query; ThreadPoolExecutor kept for CLI parity / future multi-domain use.
    with ThreadPoolExecutor(max_workers=max(1, args.threads)) as ex:
        future = ex.submit(scan_target, domain, args.timeout)
        archived = future.result()

    if archived is None:
        print("  ERROR: CDX query failed for %s" % domain)
        sys.exit(1)

    with open(args.output, "w") as f:
        for u in archived:
            f.write(u + "\n")
    print("  Archived URLs: %d" % len(archived))
    print("  Saved to %s" % args.output)

    removed = []
    if args.live:
        if not os.path.isfile(args.live):
            print("  ERROR: live file not found: %s" % args.live)
            sys.exit(1)
        live = load_live_set(args.live)
        print("  Live entries: %d (%s)" % (len(live), args.live))
        for u in archived:
            if not live_covers(u, live):
                removed.append(u)
        print()
        print("  REMOVED-but-archived (HIGH-value review candidates): %d/%d" % (len(removed), len(archived)))
        for u in removed:
            print("  [HIGH] REMOVED: %s" % u)

    dt = time.time() - t0
    print()
    print("  Done: archived=%d%s in %.1fs" % (
        len(archived),
        (" removed=%d" % len(removed)) if args.live else "",
        dt))


if __name__ == "__main__":
    main()

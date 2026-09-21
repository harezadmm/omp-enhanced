#!/usr/bin/env python3
"""
JS Miner — read-only recon.

GET <url>/, extract <script src> tags, fetch same-origin JS files
(cap 20 files, 2MB each), regex for API endpoints, fetch/axios
callsites and WebSocket URLs. Prints endpoint|method|source-file table.

Usage:
  python js_miner.py -u https://target.com
  python js_miner.py -u https://target.com -o endpoints.txt --timeout 20
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
TIMEOUT = 20
MAX_JS_FILES = 20
MAX_JS_BYTES = 2 * 1024 * 1024

SRC_RE = re.compile(r'<script[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
FETCH_RE = re.compile(r'fetch\s*\(\s*["\'`]([^"\'`]+)["\'`]', re.IGNORECASE)
AXIOS_RE = re.compile(r'axios\s*\.\s*(get|post|put|delete|patch|head|options)\s*\(\s*["\'`]([^"\'`]+)["\'`]', re.IGNORECASE)
AJAX_RE = re.compile(r'\$\.(?:get|post|ajax)\s*\([^)]*?["\'`](/?[A-Za-z0-9_\-/]+)["\'`]', re.IGNORECASE)
API_PATH_RE = re.compile(r'["\'`](\/api\/[a-zA-Z0-9_\-/{}]+)["\'`]')
WS_RE = re.compile(r'new\s+WebSocket\s*\(\s*["\'`]([^"\'`]+)["\'`]', re.IGNORECASE)


def fetch(url, headers=None, method="GET", timeout=TIMEOUT, max_bytes=None):
    if headers is None:
        headers = {}
    headers.setdefault("User-Agent", UA)
    req = urllib.request.Request(url, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        raw = resp.read(max_bytes) if max_bytes else resp.read()
        ctype = resp.headers.get("Content-Type", "")
        text = raw.decode("utf-8", errors="replace")
        return resp.status, dict(resp.headers), text
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, dict(e.headers), body
    except Exception as e:
        return 0, {}, str(e)


def normalize(url):
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")


def extract_scripts(html, base_url):
    origin = urllib.parse.urlparse(base_url).netloc.lower()
    out = []
    seen = set()
    for m in SRC_RE.finditer(html):
        src = m.group(1).strip()
        if src.startswith("data:") or src.startswith("blob:"):
            continue
        abs_url = urllib.parse.urljoin(base_url + "/", src)
        abs_url = abs_url.split("#")[0]
        # chop query version param but keep path; drop query entirely
        abs_url = abs_url.split("?")[0]
        host = urllib.parse.urlparse(abs_url).netloc.lower()
        if host != origin:
            continue
        if abs_url not in seen:
            seen.add(abs_url)
            out.append(abs_url)
    return out[:MAX_JS_FILES]


def mine_js(source_url, body):
    findings = []
    for m in FETCH_RE.finditer(body):
        findings.append({"endpoint": m.group(1), "method": "FETCH", "source": source_url})
    for m in AXIOS_RE.finditer(body):
        findings.append({"endpoint": m.group(2), "method": m.group(1).upper(), "source": source_url})
    for m in AJAX_RE.finditer(body):
        findings.append({"endpoint": m.group(1), "method": "AJAX", "source": source_url})
    for m in API_PATH_RE.finditer(body):
        findings.append({"endpoint": m.group(1), "method": "PATH", "source": source_url})
    for m in WS_RE.finditer(body):
        findings.append({"endpoint": m.group(1), "method": "WS", "source": source_url})
    return findings


def check_target(target, timeout=TIMEOUT):
    """Fetch homepage, JS files, mine endpoints. Return list of findings."""
    url = normalize(target)
    status, _, html = fetch(url + "/", timeout=timeout)
    if status != 200 or not html:
        return {"url": url, "findings": [], "error": "http %s" % status}
    scripts = extract_scripts(html, url)
    findings = []
    for js_url in scripts:
        s, _, body = fetch(js_url, timeout=timeout, max_bytes=MAX_JS_BYTES + 1)
        if s != 200 or not body:
            continue
        body = body[:MAX_JS_BYTES]
        findings.extend(mine_js(js_url, body))
    # dedupe, keep order
    seen = set()
    uniq = []
    for f in findings:
        key = (f["endpoint"], f["method"], f["source"])
        if key not in seen:
            seen.add(key)
            uniq.append(f)
    return {"url": url, "findings": uniq, "js_files": scripts}


def scan_target(target, timeout=TIMEOUT):
    """Worker for mass scanning."""
    try:
        result = check_target(target, timeout=timeout)
        if result is not None:
            return result
    except Exception:
        pass
    return None


def main():
    parser = argparse.ArgumentParser(description="JS Miner — API endpoint recon via JS files (read-only)")
    parser.add_argument("-l", "--list", help="Targets file (one URL per line)")
    parser.add_argument("-u", "--url", help="Single target URL")
    parser.add_argument("-t", "--threads", type=int, default=10, help="Threads (default: 10)")
    parser.add_argument("-o", "--output", default="js-miner-endpoints.txt", help="Output file")
    parser.add_argument("--timeout", type=int, default=20, help="Request timeout seconds (default: 20)")
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

    print(" JS Miner")
    print(" Targets: %d | Threads: %d" % (len(targets), args.threads))
    print()

    all_findings = []
    with ThreadPoolExecutor(max_workers=args.threads) as ex:
        futures = {ex.submit(scan_target, t, args.timeout): t for t in targets}
        for i, future in enumerate(as_completed(futures), 1):
            target = futures[future]
            try:
                result = future.result()
                if result:
                    n = len(result.get("findings", []))
                    print("  [%d/%d] %s: %d endpoints (%d js files)" % (
                        i, len(targets), result.get("url", target), n, len(result.get("js_files", []))))
                    all_findings.extend(result.get("findings", []))
                else:
                    print("  [%d/%d] ERROR: %s" % (i, len(targets), target), end="\r")
            except Exception as e:
                print("  [%d/%d] ERROR: %s — %s" % (i, len(targets), target, e))

    print("\n  Endpoints: %d" % len(all_findings))
    if all_findings:
        print("  endpoint|method|source-file")
        for f in all_findings[:50]:
            print("  %s|%s|%s" % (f["endpoint"], f["method"], f["source"]))
        if len(all_findings) > 50:
            print("  ... and %d more" % (len(all_findings) - 50))
        with open(args.output, "w") as fh:
            for f in all_findings:
                fh.write("%s|%s|%s\n" % (f["endpoint"], f["method"], f["source"]))
        print("  Saved to %s" % args.output)


if __name__ == "__main__":
    main()

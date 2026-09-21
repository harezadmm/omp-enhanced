#!/usr/bin/env python3
"""
Subdomain Enumeration via crt.sh (Certificate Transparency) — read-only recon.

Queries the crt.sh JSON API for a domain, extracts unique subdomains,
strips wildcard prefixes, optionally resolves each via DNS.

Usage:
  python subdomain_crt.py -u example.com
  python subdomain_crt.py -l domains.txt -t 20 --resolve
  python subdomain_crt.py -u example.com -o subs.txt --resolve --json out.json
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
TIMEOUT = 25


def fetch(url, headers=None, method="GET", timeout=TIMEOUT):
    if headers is None:
        headers = {}
    headers.setdefault("User-Agent", UA)
    req = urllib.request.Request(url, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status, dict(resp.headers), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, dict(e.headers), body
    except Exception as e:
        return 0, {}, str(e)


def normalize_domain(domain):
    domain = domain.strip().lower()
    domain = re.sub(r"^https?://", "", domain)
    domain = domain.split("/")[0].split(":")[0]
    domain = domain.lstrip("*.")
    return domain.rstrip(".")


def check_target(domain, timeout=TIMEOUT):
    """Query crt.sh for a domain; return dict with domain, subdomains list."""
    domain = normalize_domain(domain)
    if not domain:
        return {"domain": domain, "subdomains": [], "error": "empty domain"}
    q = urllib.parse.quote("%." + domain, safe="")
    url = "https://crt.sh/?q=%s&output=json" % q
    status, _, body = fetch(url, timeout=timeout)
    if status != 200:
        return {"domain": domain, "subdomains": [], "error": "http %s" % status}
    try:
        data = json.loads(body)
    except Exception as e:
        return {"domain": domain, "subdomains": [], "error": "bad json: %s" % e}
    names = set()
    if isinstance(data, list):
        for entry in data:
            raw = str(entry.get("name_value", ""))
            for line in raw.splitlines():
                name = line.strip().lower().rstrip(".")
                if name.startswith("*."):
                    name = name[2:]
                if name and re.match(r"^[a-z0-9_.*-]+(\.[a-z0-9_-]+)+$", name) and "*" not in name:
                    names.add(name)
    # Keep only names under the base domain
    subs = sorted(n for n in names if n == domain or n.endswith("." + domain))
    return {"domain": domain, "subdomains": subs}


def resolve_name(name, timeout=3):
    try:
        old = socket.getdefaulttimeout()
        socket.setdefaulttimeout(timeout)
        try:
            _, _, ips = socket.gethostbyname_ex(name)
            return ips
        finally:
            socket.setdefaulttimeout(old)
    except Exception:
        return []


def scan_target(domain, timeout=TIMEOUT, resolve=False):
    """Worker for mass scanning."""
    try:
        result = check_target(domain, timeout=timeout)
        if resolve and result.get("subdomains"):
            resolved = {}
            for sub in result["subdomains"]:
                ips = resolve_name(sub)
                if ips:
                    resolved[sub] = ips
            result["resolved"] = resolved
        return result
    except Exception:
        pass
    return None


def main():
    parser = argparse.ArgumentParser(description="Subdomain enumeration via crt.sh (read-only recon)")
    parser.add_argument("-l", "--list", help="Domains file (one domain per line)")
    parser.add_argument("-u", "--url", help="Single domain (or URL, host is extracted)")
    parser.add_argument("-t", "--threads", type=int, default=10, help="Threads (default: 10)")
    parser.add_argument("-o", "--output", default="subdomains.txt", help="Output file (one subdomain per line)")
    parser.add_argument("--resolve", action="store_true", help="Resolve subdomains via DNS (3s timeout each)")
    parser.add_argument("--json", dest="json_out", default=None, help="JSON summary output file")
    parser.add_argument("--timeout", type=int, default=25, help="Request timeout seconds (default: 25)")
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

    print(" Subdomain crt.sh Scanner")
    print(" Targets: %d | Threads: %d | Resolve: %s" % (len(targets), args.threads, args.resolve))
    print()

    results = []
    with ThreadPoolExecutor(max_workers=args.threads) as ex:
        futures = {ex.submit(scan_target, t, args.timeout, args.resolve): t for t in targets}
        for i, future in enumerate(as_completed(futures), 1):
            target = futures[future]
            try:
                result = future.result()
                if result:
                    n = len(result.get("subdomains", []))
                    print("  [%d/%d] %s: %d subdomains" % (i, len(targets), result.get("domain", target), n))
                    results.append(result)
                else:
                    print("  [%d/%d] ERROR: %s" % (i, len(targets), target), end="\r")
            except Exception as e:
                print("  [%d/%d] ERROR: %s — %s" % (i, len(targets), target, e))

    total = sum(len(r.get("subdomains", [])) for r in results)
    print("\n  Domains: %d/%d | Subdomains: %d" % (len(results), len(targets), total))

    if results:
        seen = set()
        with open(args.output, "w") as f:
            for r in results:
                for sub in r.get("subdomains", []):
                    if sub not in seen:
                        seen.add(sub)
                        if args.resolve:
                            ips = (r.get("resolved") or {}).get(sub)
                            if ips:
                                f.write("%s # %s\n" % (sub, ",".join(ips)))
                            else:
                                f.write("%s\n" % sub)
                        else:
                            f.write("%s\n" % sub)
        print("  Saved to %s" % args.output)

    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(results, f, indent=2)
        print("  JSON saved to %s" % args.json_out)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Rate-Limit Probe — gentle read-only recon (no exploitation, no flooding).

Sends N sequential GETs to one URL with a polite delay + jitter between
requests, records per-request status/latency, and classifies the target:
  RATE-LIMITED — a 429 was observed (stops at first 429)
  LOCKOUT      — early 2xx responses followed by persistent 403s
  NO-LIMIT     — no 429 and no lockout pattern across the burst

Safety: delay defaults to 1s (never below 1s), burst defaults to 20
(never above 50), and the probe aborts early on the first 429.

Usage:
  python rate_probe.py -u https://target.com/login
  python rate_probe.py -u https://target.com/ --burst 10 --delay 2 -o rate.txt
"""

import argparse
import json
import os
import random
import re
import sys
import time
import urllib.request
import urllib.error
import ssl
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed  # noqa: F401 (template parity)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
TIMEOUT = 20
DEFAULT_BURST = 20
MAX_BURST = 50
DEFAULT_DELAY = 1.0
MIN_DELAY = 1.0


def normalize(url):
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")


def single_get(url, timeout=TIMEOUT):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": UA}, method="GET")
    start = time.monotonic()
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        latency = time.monotonic() - start
        retry = resp.headers.get("Retry-After")
        return resp.status, latency, retry, None
    except urllib.error.HTTPError as e:
        latency = time.monotonic() - start
        try:
            retry = e.headers.get("Retry-After") if e.headers else None
        except Exception:
            retry = None
        return e.code, latency, retry, None
    except Exception as e:
        return 0, time.monotonic() - start, None, str(e)


def check_target(target, burst=DEFAULT_BURST, delay=DEFAULT_DELAY, timeout=TIMEOUT):
    """Gentle sequential burst probe; stops early on first 429."""
    burst = max(1, min(int(burst), MAX_BURST))
    delay = max(float(delay), MIN_DELAY)
    url = normalize(target)
    rows = []  # (seq, status, latency, retry_after, error)
    verdict = "NO-LIMIT"
    stopped_early = False
    for seq in range(1, burst + 1):
        status, latency, retry, err = single_get(url, timeout=timeout)
        rows.append((seq, status, latency, retry, err))
        if status == 429:
            verdict = "RATE-LIMITED"
            stopped_early = True
            break
        if seq < burst:
            time.sleep(delay + random.uniform(0, 0.3))
    if verdict != "RATE-LIMITED" and _is_lockout([r[1] for r in rows]):
        verdict = "LOCKOUT"
    retry_after = next((r[3] for r in rows if r[3]), None)
    return {
        "url": url,
        "burst": burst,
        "delay": delay,
        "sent": len(rows),
        "rows": rows,
        "verdict": verdict,
        "retry_after": retry_after,
        "stopped_early": stopped_early,
    }


def _is_lockout(statuses):
    """2xx at the start, then 403s through the end of the burst."""
    if len(statuses) < 3:
        return False
    if not any(200 <= s < 300 for s in statuses[:2]):
        return False
    tail = statuses[-3:]
    return all(s == 403 for s in tail)


def scan_target(target, burst=DEFAULT_BURST, delay=DEFAULT_DELAY, timeout=TIMEOUT):
    """Worker wrapper (sequential probe; kept for template parity)."""
    try:
        return check_target(target, burst=burst, delay=delay, timeout=timeout)
    except Exception as e:
        return {"url": target, "error": str(e), "verdict": "ERROR", "rows": []}


def main():
    parser = argparse.ArgumentParser(description="Rate-Limit Probe — gentle burst recon (max 50 reqs, stops on 429)")
    parser.add_argument("-l", "--list", help="Targets file (one URL per line)")
    parser.add_argument("-u", "--url", help="Single target URL")
    parser.add_argument("--burst", type=int, default=DEFAULT_BURST,
                        help=f"Requests to send, clamped to 1-{MAX_BURST} (default: {DEFAULT_BURST})")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY,
                        help=f"Seconds between requests, minimum {MIN_DELAY} (default: {DEFAULT_DELAY})")
    parser.add_argument("-o", "--output", default="rate-probe.txt", help="Output file")
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

    burst = max(1, min(args.burst, MAX_BURST))
    delay = max(args.delay, MIN_DELAY)

    print(" Rate-Limit Probe (gentle: sequential, delay>=1s, stops on 429)")
    print(f" Targets: {len(targets)} | Burst: {burst} | Delay: {delay}s")
    print()

    results = []
    for i, target in enumerate(targets, 1):
        res = scan_target(target, burst=burst, delay=delay, timeout=args.timeout)
        results.append(res)
        if res.get("verdict") == "ERROR":
            print(f"  [{i}/{len(targets)}] ERROR: {target} — {res.get('error')}")
            continue
        print(f"  [{i}/{len(targets)}] {res['url']} -> {res['verdict']} ({res['sent']} reqs)")
        for seq, status, latency, retry, err in res["rows"]:
            extra = f" retry-after={retry}" if retry else ""
            extra += f" err={err}" if err else ""
            print(f"       #{seq}: {status} {latency:.2f}s{extra}")
        if res.get("stopped_early"):
            print("       Stopped early on first 429.")

    print(f"\n  Probed: {len(results)}/{len(targets)}")

    if results:
        with open(args.output, "w") as f:
            for r in results:
                f.write(f"URL: {r.get('url')} verdict={r.get('verdict')} sent={r.get('sent', 0)}\n")
                if r.get("retry_after"):
                    f.write(f"  Retry-After: {r['retry_after']}\n")
                for row in r.get("rows", []):
                    seq, status, latency, retry, err = row
                    f.write(f"  #{seq} status={status} latency={latency:.3f}s"
                            + (f" retry-after={retry}" if retry else "")
                            + (f" err={err}" if err else "") + "\n")
        print(f"  Saved to {args.output}")


if __name__ == "__main__":
    main()

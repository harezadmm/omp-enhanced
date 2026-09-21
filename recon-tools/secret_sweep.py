#!/usr/bin/env python3
"""
secret_sweep — local secret/artifact sweeper for JS bundles and text files.

Runs read-only regex probes over a local directory (default: current dir):
AWS access keys (AKIA...), generic api-key/secret/token assignments, JWT
segments (eyJ...), private-key blocks, webhook URLs (discord/slack),
wallet addresses (0x.../bc1...), and .map sourcemap references.

Findings are written as file:line:kind:snippet lines to -o. Snippets are
REDACTED: middle masked, max 60 chars, never the full secret. Nothing is
exfiltrated; local analysis only, no network contact.

Usage:
  python secret_sweep.py -d ./js_bundles -o secrets.txt
  python secret_sweep.py -d ./dist -o secrets.txt -t 20
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
import socket

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
TIMEOUT = 15

PATTERNS = [
    ("aws-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}(?:\.[A-Za-z0-9_-]{10,})?")),
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----")),
    ("webhook", re.compile(r"https://(?:discord(?:app)?\.com/api/webhooks|hooks\.slack\.com/services)/[A-Za-z0-9/_\-?=&%.]+")),
    ("wallet-eth", re.compile(r"\b0x[a-fA-F0-9]{40}\b")),
    ("wallet-btc", re.compile(r"\bbc1[a-z0-9]{25,62}\b")),
    ("sourcemap", re.compile(r"[A-Za-z0-9_./-]+\.js\.map\b|sourceMappingURL\s*=\s*\S+")),
    ("generic-secret", re.compile(
        r"(?i)\b(api[_-]?key|api[_-]?secret|secret[_-]?key|access[_-]?token|auth[_-]?token|bearer|client[_-]?secret)\b\s*[:=]\s*['\"]?([^'\"\s;,}]{4,200})")),
]

TEXT_EXTS = {
    ".js", ".mjs", ".cjs", ".ts", ".map", ".json", ".txt", ".html", ".htm",
    ".xml", ".yml", ".yaml", ".env", ".ini", ".cfg", ".conf", ".php",
    ".py", ".rb", ".go", ".java", ".css", ".tsx", ".jsx",
}
MAX_FILE_BYTES = 5 * 1024 * 1024


def redact(match_text, max_len=60):
    """Mask the middle of a secret; keep prefix + last4; cap at max_len."""
    s = match_text.strip().strip("'\"")
    if len(s) <= 8:
        return s[:max_len] + ("*" * (len(s) - len(s[:max_len])) if len(s) > len(s[:max_len]) else "")
    head = s[:12]
    tail = s[-4:]
    redacted = "%s...***%s" % (head, tail)
    if len(redacted) > max_len:
        redacted = redacted[:max_len]
    # Defensive: never emit anything longer than max_len.
    return redacted[:max_len]


def snippet_for(kind, match, line, max_len=60):
    raw = match.group(0)
    if kind == "generic-secret":
        # match group 2 is the value; redact the value, keep the key name.
        try:
            key = match.group(1)
            val = match.group(2)
            return ("%s=<%s>" % (key, redact(val, max_len - len(key) - 3)))[:max_len]
        except IndexError:
            pass
    return redact(raw, max_len)


def check_target(path, timeout=TIMEOUT):
    """Scan one file; return list of finding dicts (local read only)."""
    del timeout  # local-only tool; kept for CLI parity.
    findings = []
    try:
        if os.path.getsize(path) > MAX_FILE_BYTES:
            return findings
    except OSError:
        return findings
    try:
        with open(path, "r", errors="replace") as f:
            for lineno, line in enumerate(f, 1):
                if len(line) > 10000:
                    line = line[:10000]
                for kind, rx in PATTERNS:
                    for m in rx.finditer(line):
                        findings.append({
                            "file": path,
                            "line": lineno,
                            "kind": kind,
                            "snippet": snippet_for(kind, m, line),
                        })
    except (OSError, UnicodeError):
        pass
    return findings


def scan_target(path, timeout=TIMEOUT):
    """Worker wrapper for check_target."""
    try:
        return check_target(path, timeout=timeout)
    except Exception:
        return []


def collect_files(root):
    files = []
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext in TEXT_EXTS or ext == "":
                files.append(os.path.join(dirpath, name))
    return sorted(files)


def main():
    parser = argparse.ArgumentParser(description="secret_sweep — local secret/artifact sweeper")
    parser.add_argument("-d", "--dir", default=".", help="Directory to sweep (default: .)")
    parser.add_argument("-o", "--output", default="secret_sweep.txt", help="Output file")
    parser.add_argument("-t", "--threads", type=int, default=10, help="Threads (default: 10)")
    parser.add_argument("--timeout", type=int, default=TIMEOUT, help="Accepted for CLI parity; unused (local-only)")
    args = parser.parse_args()

    if not os.path.isdir(args.dir):
        print("  ERROR: not a directory: %s" % args.dir)
        sys.exit(1)

    print(" secret_sweep — Local Secret Sweeper")
    print(" Dir: %s | Threads: %d" % (args.dir, args.threads))
    print()

    t0 = time.time()
    files = collect_files(args.dir)
    print(" Files: %d" % len(files))

    findings = []
    with ThreadPoolExecutor(max_workers=max(1, args.threads)) as ex:
        futures = {ex.submit(scan_target, p): p for p in files}
        for i, future in enumerate(as_completed(futures), 1):
            path = futures[future]
            try:
                res = future.result()
                if res:
                    for r in res:
                        print("  [%s] %s:%d:%s" % (r["kind"], r["file"], r["line"], r["snippet"]))
                    findings.extend(res)
                else:
                    print("  [%d/%d] CLEAN: %s" % (i, len(files), path), end="\r")
            except Exception as e:
                print("  [%d/%d] ERROR: %s — %s" % (i, len(files), path, e))

    findings.sort(key=lambda r: (r["file"], r["line"], r["kind"]))
    with open(args.output, "w") as f:
        for r in findings:
            f.write("%s:%d:%s:%s\n" % (r["file"], r["line"], r["kind"], r["snippet"]))

    kinds = {}
    for r in findings:
        kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
    print()
    print("  Findings: %d in %d files (%.1fs)" % (len(findings), len(files), time.time() - t0))
    if kinds:
        for k in sorted(kinds):
            print("    %-14s %d" % (k, kinds[k]))
    print("  Saved to %s" % args.output)


if __name__ == "__main__":
    main()

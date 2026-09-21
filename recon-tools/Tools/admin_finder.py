#!/usr/bin/env python3
"""
  ╔══════════════════════════════════════════════════════════════╗
  ║              A D M I N    F I N D E R                      ║
  ║         Admin Panel Discovery & Brute-Force Scanner        ║
  ╚══════════════════════════════════════════════════════════════╝
"""

import os, sys, re, ssl, time, json, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
TIMEOUT = 10

# ─── Admin Paths Database ───────────────────────────────────────────
ADMIN_PATHS = [
    # Generic
    "admin", "administrator", "admin.php", "admin/login", "admin/login.php",
    "admin/index.php", "admin/admin.php", "admin/home.php",
    "login", "login.php", "signin", "signin.php", "sign-in", "sign-in.php",
    "auth", "auth/login", "auth/admin",
    "backend", "backend/login", "backend/admin",
    "control", "control.php", "controlpanel", "control-panel",
    "dashboard", "dashboard.php", "dashboard/login",
    "panel", "panel.php", "panel/login", "panel/admin",
    "manager", "manager.php", "manager/login", "manager/admin",
    "cp", "cp.php", "cp/login", "moderator", "moderator.php",
    "system", "system.php", "system/login", "system/admin",
    "secure", "secure.php", "secure/login", "secure/admin",
    "master", "master.php", "master/login", "webmaster", "webmaster.php",
    "siteadmin", "siteadmin.php", "site-admin", "site-admin.php",
    "user", "user.php", "user/login", "user/admin",
    "users", "users.php", "users/login",
    "account", "account.php", "account/login",
    "member", "member.php", "members", "members.php",
    "staff", "staff.php", "staff/login",
    "office", "office.php", "office/login",

    # CMS-specific
    "wp-admin", "wp-admin/admin.php", "wp-login.php",
    "administrator/index.php",  # Joomla
    "user/login",  # Drupal
    "umbraco", "umbraco/login.aspx",
    "concrete", "concrete/index.php/login",
    "magento", "magento/admin", "magento/index.php/admin",
    "admin/", "index.php/admin",

    # Technology-specific
    "phpmyadmin", "phpMyAdmin", "phpmyadmin/index.php", "pma", "pma/index.php",
    "adminer", "adminer.php",
    "mysql", "mysql/admin", "mysql/index.php",
    "db", "db/admin", "database", "database/admin",
    "sql", "sql/admin", "sql/index.php",
    "pgadmin", "pgadmin/index.php", "phppgadmin",
    "mssql", "mssql/manager",

    # Web servers
    "cpanel", "whm", "webmail", "webmail.php",
    "roundcube", "roundcube/index.php",
    "squirrelmail", "squirrelmail/src/login.php",
    "horde", "horde/login.php",
    "webmin", "webmin/index.cgi",
    "plesk", "plesk/login.php",
    "ispconfig", "ispconfig/index.php",
    "vesta", "vesta/login/index.php",
    "directadmin", "directadmin/login.php",
    "zpanel", "zpanel/index.php",
    "sentora", "sentora/index.php",

    # CMS panels
    "typo3", "typo3/index.php",
    "prestashop", "prestashop/admin",
    "opencart", "opencart/admin",
    "magento", "magento/admin",
    "shopify", "shopify/admin",
    "woocommerce", "woocommerce/admin",
    "drupal", "drupal/admin",
    "joomla", "joomla/administrator",
    "craft", "craft/admin",
    "statamic", "statamic/cp",
    "october", "october/backend",
    "pyrocms", "pyrocms/admin",
    "pagekit", "pagekit/admin",
    "bolt", "bolt/bolt",
    "grav", "grav/admin",
    "processwire", "processwire/admin",
    "modx", "modx/manager",
    "textpattern", "textpattern/index.php",
    "serendipity", "serendipity_admin.php",
    "dotclear", "dotclear/admin",
    "b2evolution", "b2evolution/admin",
    "nucleus", "nucleus/index.php",
    "pivotx", "pivotx/index.php",

    # Framework panels
    "laravel", "laravel/admin",
    "nova", "nova/login",
    "horizon", "horizon/dashboard",
    "telescope", "telescope/requests",
    "filament", "filament/admin",
    "orchid", "orchid/login",
    "voyager", "voyager/login",
    "nova", "nova/dashboard",

    # DevOps
    "jenkins", "jenkins/login",
    "gitlab", "gitlab/users/sign_in",
    "grafana", "grafana/login",
    "kibana", "kibana/login",
    "prometheus", "prometheus/graph",
    "portainer", "portainer/",
    "rancher", "rancher/auth/login",
    "traefik", "traefik/dashboard/",
    "kong", "kong/",
    "nifi", "nifi/login",
    "airflow", "airflow/login",
    "superset", "superset/login",
    "redash", "redash/login",

    # API panels
    "api", "api/v1", "api/admin", "api/docs",
    "swagger", "swagger/index.html", "swagger-ui.html",
    "graphql", "graphql/playground", "graphiql",
    "docs", "api-docs", "redoc",

    # Debug
    "debug", "debug/default", "debug/bar",
    "phpinfo.php", "info.php", "test.php", "phpinfo",
    "server-status", "server-info",
    "status", "health", "healthcheck", "ping",
    "actuator", "actuator/health", "actuator/info",
    "metrics", "stats",

    # Config
    ".env", ".env.example", ".env.backup", ".env.local", ".env.production",
    "config.php", "config.php.bak", "config.php.old",
    "settings.php", "settings.ini",
    "wp-config.php", "wp-config.php.bak", "wp-config.php.old",
    "configuration.php", "configuration.php.bak",
    "parameters.yml", "parameters.yml.dist",
    "database.yml", "database.ini",
    "app.config", "web.config", "web.config.bak",
    "application.properties", "application.yml", "application.yaml",
    "settings.py", "config.py", "config.json", "config.yml",
    "secret.key", "secrets.yml", "credentials.json",
    "docker-compose.yml", "docker-compose.yaml", "Dockerfile",
    ".git/config", ".gitignore", ".git/HEAD",
    ".svn/entries", ".hg/hgrc",
    ".htaccess", ".htpasswd", ".htpasswd.bak",
    "robots.txt", "sitemap.xml", "crossdomain.xml",
    "security.txt", ".well-known/security.txt",
]

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

def normalize(url):
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")

# ─── Scanner ────────────────────────────────────────────────────────
def check_path(args):
    """Check a single admin path on a target."""
    target, path = args
    url = normalize(target)
    full_url = f"{url}/{path}"

    s, h, body, final_url = fetch(full_url)

    if s == 0:
        return None

    result = {
        "target": target,
        "path": path,
        "url": full_url,
        "status": s,
        "final_url": final_url,
        "size": len(body),
        "interesting": False,
        "reason": None,
    }

    # 200 OK — potentially interesting
    if s == 200:
        body_lower = body.lower()

        # Check for login indicators
        login_words = ["login", "password", "username", "sign in", "log in", "signin", "email", "credential"]
        admin_words = ["admin", "dashboard", "control panel", "backend", "manage", "administration"]
        config_words = ["password", "secret", "key", "token", "api_key", "database", "host", "user", "db_"]
        debug_words = ["phpinfo", "php version", "environment", "debug", "trace", "exception"]

        if "login" in body_lower and any(w in body_lower for w in admin_words):
            result["interesting"] = True
            result["reason"] = "Admin Login Panel"
        elif any(w in body_lower for w in login_words) and len(body) > 500:
            result["interesting"] = True
            result["reason"] = "Login Page"
        elif any(w in body_lower for w in admin_words) and len(body) > 500:
            result["interesting"] = True
            result["reason"] = "Admin Panel"
        elif any(w in body_lower for w in config_words):
            result["interesting"] = True
            result["reason"] = "Config/Secrets Exposure"
        elif any(w in body_lower for w in debug_words):
            result["interesting"] = True
            result["reason"] = "Debug/Info Page"
        elif "index of" in body_lower:
            result["interesting"] = True
            result["reason"] = "Directory Listing"
        # Check title
        title_match = re.search(r'<title>([^<]+)</title>', body, re.IGNORECASE)
        if title_match:
            title = title_match.group(1)
            if any(w in title.lower() for w in login_words + admin_words):
                result["title"] = title

    # 301/302 — redirect (might be auth redirect)
    elif s in [301, 302]:
        location = h.get("Location", "")
        if "login" in location.lower() or "admin" in location.lower():
            result["interesting"] = True
            result["reason"] = f"Redirect to login (HTTP {s})"
            result["redirect"] = location

    # 401/403 — auth required (admin exists!)
    elif s in [401, 403]:
        result["interesting"] = True
        result["reason"] = f"Auth Required (HTTP {s})"

    # 500 — potential vulnerability
    elif s == 500:
        result["interesting"] = True
        result["reason"] = "Server Error (potential misconfiguration)"

    if result["interesting"]:
        return result
    return None

# ─── Default Credential Check ──────────────────────────────────────
DEFAULT_CREDS = [
    ("admin", "admin"), ("admin", "password"), ("admin", "admin123"),
    ("admin", "123456"), ("admin", "12345678"), ("admin", "123456789"),
    ("root", "root"), ("root", "admin"), ("root", "password"),
    ("root", "toor"), ("root", "123456"),
    ("administrator", "administrator"), ("administrator", "admin"),
    ("user", "user"), ("user", "password"), ("user", "123456"),
    ("test", "test"), ("test", "testing"),
    ("guest", "guest"), ("guest", "password"),
    ("manager", "manager"), ("manager", "admin"),
    ("demo", "demo"), ("demo", "password"),
    ("sa", "sa"), ("sa", "password"),
    ("postgres", "postgres"), ("postgres", "password"),
    ("mysql", "mysql"), ("mysql", "password"),
    ("oracle", "oracle"), ("oracle", "password"),
]

def check_default_creds(url, username, password, login_field="username", pass_field="password"):
    """Check if default credentials work on a login form."""
    data = urllib.parse.urlencode({
        login_field: username,
        pass_field: password,
    }).encode()
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    s, h, body, final_url = fetch(url, data=data, headers=headers, method="POST", timeout=15)

    # Check if login succeeded (redirected to dashboard, or no "invalid" message)
    if s in [301, 302]:
        location = h.get("Location", "")
        if "login" not in location.lower() and "error" not in location.lower():
            return True, f"Redirected to {location}"

    if s == 200 and "invalid" not in body.lower() and "incorrect" not in body.lower() and "wrong" not in body.lower():
        if "dashboard" in body.lower() or "admin" in body.lower() or "welcome" in body.lower():
            return True, "Logged in successfully"

    return False, None

# ─── Main ───────────────────────────────────────────────────────────
def main():
    print("""
    A D M I N   F I N D E R
    Admin Panel Discovery & Brute-Force Scanner
    """)

    print("  [1] Single target scan")
    print("  [2] Mass target scan (file)")
    print("  [3] Quick scan (top 50 paths only)")
    print("  [4] Full scan (all paths)")
    print("  [5] Check default credentials on found panels")
    print("  [0] Exit")
    print()

    choice = input("  Select: ").strip()

    if choice == "0":
        return

    if choice == "1":
        targets = [input("  Target URL: ").strip()]
    elif choice == "2":
        filepath = input("  Targets file: ").strip()
        if not os.path.exists(filepath):
            print(f"  File not found: {filepath}")
            return
        with open(filepath) as f:
            targets = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    else:
        return

    # Select paths
    if choice == "3":
        paths = ADMIN_PATHS[:50]
    elif choice == "4":
        paths = ADMIN_PATHS
    else:
        paths = ADMIN_PATHS[:100]

    threads = input("  Threads (default 30): ").strip()
    threads = int(threads) if threads.isdigit() else 30

    print(f"\n  Scanning {len(targets)} target(s) × {len(paths)} paths...")
    print("  " + "═" * 50)

    # Build task list
    tasks = []
    for target in targets:
        for path in paths:
            tasks.append((target, path))

    results = []
    with ThreadPoolExecutor(max_workers=threads) as ex:
        futures = {ex.submit(check_path, task): task for task in tasks}
        for i, future in enumerate(as_completed(futures), 1):
            task = futures[future]
            try:
                result = future.result()
                if result:
                    results.append(result)
                    print(f"  [{i}/{len(tasks)}] {result['status']} {result['reason']}: {result['url']}")
                else:
                    if i % 100 == 0:
                        print(f"  [{i}/{len(tasks)}] Scanning...", end="\r")
            except Exception as e:
                pass

    # Group by target
    found = {}
    for r in results:
        found.setdefault(r["target"], []).append(r)

    print(f"\n\n  " + "═" * 50)
    print(f"  SCAN COMPLETE")
    print(f"  " + "═" * 50)
    print(f"  Targets scanned: {len(targets)}")
    print(f"  Paths tested:    {len(tasks)}")
    print(f"  Interesting:     {len(results)}")

    for target, items in found.items():
        print(f"\n  [{target}] — {len(items)} finding(s):")
        for item in items[:20]:
            print(f"    {item['status']} {item['reason']:<30s} {item['path']}")

    # Check default credentials
    if choice == "5" and results:
        login_panels = [r for r in results if "login" in r.get("reason", "").lower() or r["status"] == 401]
        if login_panels:
            print(f"\n  Checking default credentials on {len(login_panels)} panels...")
            for panel in login_panels[:5]:
                url = panel["url"]
                print(f"  [{url}]")
                for user, pwd in DEFAULT_CREDS[:10]:
                    ok, reason = check_default_creds(url, user, pwd)
                    if ok:
                        print(f"    SUCCESS: {user}:{pwd} — {reason}")
                        break
                else:
                    print(f"    No default creds worked")

    if results:
        output_file = f"admin_finder_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n  Saved: {output_file}")

    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Interrupted. Exiting...\n")
        sys.exit(0)
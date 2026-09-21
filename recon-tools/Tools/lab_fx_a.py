"""Lab drill fixtures, module A (PREFIX /fx/a).

Covers: cve-2024-0204_goanywhere, cve-2024-11080_postgrid,
cve-2024-1709_screenconnect, cve-2024-21887_ivanti, cve-2024-23692_hfs,
cve-2024-27956_valvepress, cve-2024-28000_litespeed, cve-2024-2879_layerslider,
cve-2024-3400_panos, cve-2024-34102_cosmicsting, cve-2024-40711_veeam,
cve-2024-4577_phpcgi, secret_sweep (PLANT dirs).

Contract: PREFIX, ROUTES {(method, full_path): (status, ctype, body)},
handle(method, path, headers, body) -> tuple or None (dynamic routes:
query-dependent differentials, header-dependent differentials, and the
panos marker-file handshake), CASES with {BASE}/{PLANT} placeholders.
"""

import re

PREFIX = "/fx/a"


def _add(routes, method, suffix, status=200, ctype="text/plain", body=""):
    routes[(method, PREFIX + suffix)] = (status, ctype, body)


ROUTES = {}

# --- CVE-2024-0204 GoAnywhere: 200 + ViewState vs 404 ---
_add(ROUTES, "GET", "/goanywhere-vuln/goanywhere/images/..;/wizard/InitialAccountSetup.xhtml",
     200, "text/html",
     "<html><body><form>Initial Account Setup"
     '<input type="hidden" name="javax.faces.ViewState" value="abc123"/>'
     "</form></body></html>")
_add(ROUTES, "GET", "/goanywhere-fixed/goanywhere/images/..;/wizard/InitialAccountSetup.xhtml",
     404, "text/plain", "not found")

# --- CVE-2024-11080 Post Grid: Stable tag in-range + dir vs out-of-range ---
_add(ROUTES, "GET", "/postgrid-vuln/wp-content/plugins/post-grid/readme.txt",
     200, "text/plain", "=== Post Grid ===\nStable tag: 2.3.0\n")
_add(ROUTES, "GET", "/postgrid-vuln/wp-content/plugins/post-grid/",
     200, "text/html", "<html><body>post-grid plugin directory</body></html>")
_add(ROUTES, "GET", "/postgrid-fixed/wp-content/plugins/post-grid/readme.txt",
     200, "text/plain", "=== Post Grid ===\nStable tag: 2.3.33\n")
_add(ROUTES, "GET", "/postgrid-fixed/wp-content/plugins/post-grid/",
     200, "text/html", "<html><body>post-grid plugin directory</body></html>")

# --- CVE-2024-1709 ScreenConnect: wizard 200 vs redirect; footer versions ---
_add(ROUTES, "GET", "/screenconnect-vuln/Login",
     200, "text/html",
     "<html><head><title>ConnectWise ScreenConnect Login</title></head>"
     '<body><div class="footer">ScreenConnect Version 23.9.7</div></body></html>')
_add(ROUTES, "GET", "/screenconnect-vuln/SetupWizard.aspx",
     200, "text/html",
     "<html><body><h1>Setup Wizard</h1><p>License Agreement</p>"
     "<p>Create an Administrator account to complete setup</p></body></html>")
_add(ROUTES, "GET", "/screenconnect-vuln/SetupWizard.aspx/",
     200, "text/html",
     "<html><body><h1>Setup Wizard</h1><p>License Agreement</p>"
     "<p>Create an Administrator account to complete setup</p></body></html>")
_add(ROUTES, "GET", "/screenconnect-fixed/Login",
     200, "text/html",
     "<html><head><title>ConnectWise ScreenConnect Login</title></head>"
     '<body><div class="footer">ScreenConnect Version 24.1.5</div></body></html>')
_add(ROUTES, "GET", "/screenconnect-fixed/SetupWizard.aspx", 302, "text/plain", "")
_add(ROUTES, "GET", "/screenconnect-fixed/SetupWizard.aspx/", 302, "text/plain", "")

# --- CVE-2024-21887 Ivanti: JSON result+message vs 404 ---
_add(ROUTES, "GET", "/ivanti21887-vuln/api/v1/totp/user-backup-code/../../license/keys-status/",
     200, "application/json", '{"result": "ok", "message": "license keys status"}')
_add(ROUTES, "GET", "/ivanti21887-fixed/api/v1/totp/user-backup-code/../../license/keys-status/",
     404, "text/plain", "not found")

# --- CVE-2024-28000 LiteSpeed: Stable tag <= 6.3.0.1 vs above ---
_add(ROUTES, "GET", "/litespeed-vuln/wp-content/plugins/litespeed-cache/readme.txt",
     200, "text/plain", "=== LiteSpeed Cache ===\nStable tag: 6.3.0.1\n")
_add(ROUTES, "GET", "/litespeed-fixed/wp-content/plugins/litespeed-cache/readme.txt",
     200, "text/plain", "=== LiteSpeed Cache ===\nStable tag: 6.4.0\n")

# --- CVE-2024-34102 CosmicSting fingerprints (POST endpoint is dynamic) ---
_add(ROUTES, "GET", "/cosmic-vuln/magento_version",
     200, "text/plain", "Magento 2.4.6\n")
_add(ROUTES, "GET", "/cosmic-vuln/rest/all/V1/directory/countries",
     200, "application/json", '{"country_id": "US", "magento": "2.4.6"}')
_add(ROUTES, "GET", "/cosmic-fixed/magento_version", 404, "text/plain", "not found")
_add(ROUTES, "GET", "/cosmic-fixed/rest/all/V1/directory/countries",
     404, "text/plain", "not found")

# --- CVE-2024-40711 Veeam: serverinfo markers vs 404 ---
_add(ROUTES, "GET", "/veeam-vuln/api/v1/serverinfo",
     200, "application/json",
     '{"databaseVendor": "MSSQL", "databaseContentVersion": "13.0.1"}')
_add(ROUTES, "GET", "/veeam-fixed/api/v1/serverinfo", 404, "text/plain", "not found")

# --- CVE-2024-4577 php-cgi: md5("check") echo vs clean page ---
_add(ROUTES, "POST", "/phpcgi-vuln/index.php",
     200, "text/html", "<html><body>3f2ba4ab3b260f4c2dc61a6fac7c3e8a</body></html>")
_add(ROUTES, "POST", "/phpcgi-fixed/index.php",
     200, "text/html", "<html><body>php-cgi landing page</body></html>")

# --- CVE-2024-2879 LayerSlider fingerprint CSS (ajax endpoint is dynamic) ---
_add(ROUTES, "GET", "/ls-vuln/wp-content/plugins/LayerSlider/assets/static/public/front.css",
     200, "text/css", ".ls-clearfix:before{content:\"\";display:table}\n.ls-container{position:relative}\n")
_add(ROUTES, "GET", "/ls-fixed/wp-content/plugins/LayerSlider/assets/static/public/front.css",
     200, "text/css", ".ls-clearfix:before{content:\"\";display:table}\n.ls-container{position:relative}\n")

# ---------------------------------------------------------------- dynamic ---

# PAN-OS marker files "created" on the vuln app via the hipreport handshake.
_CREATED = set()

_HFS_VULN_BASE = (
    "<html><head><title>HFS 2.3m file server</title></head><body>"
    "<h1>Rejetto HttpFileServer HFS 2.3m</h1><p>file list</p></body></html>")
_HFS_VULN_PROBE = (
    "<html><head><title>HFS 2.3m file server</title></head><body>"
    "<h1>Rejetto HttpFileServer HFS 2.3m</h1><p>section: parsed-ok</p></body></html>")
_HFS_FIXED_BASE = (
    "<html><head><title>HFS 2.3n file server</title></head><body>"
    "<h1>Rejetto HttpFileServer HFS 2.3n</h1><p>file list</p></body></html>")

_LS_AJAX_PAGE = (
    "<html><body><div class=\"ls-popup\">popup markup id=1</div></body></html>")
_LS_AJAX_PAGE_B = (
    "<html><body><div class=\"ls-popup\">popup markup id=other</div></body></html>")

_COSMIC_JSON = '{"shipping_methods": []}'
_COSMIC_XML_ERR = (
    '{"message": "XML parsing error: mismatched tag, not well-formed '
    '(libxml DOMDocument SimpleXMLElement)"}')


def _header(headers, name):
    if not headers:
        return ""
    try:
        items = list(headers.items())
    except Exception:
        items = []
    for k, v in items:
        try:
            if k.lower() == name.lower():
                return v
        except Exception:
            continue
    try:
        return headers.get(name, "") or ""
    except Exception:
        return ""


def _splitsuffix(path):
    """Return (app, rest) for /fx/a/<app>/... paths, else (None, None)."""
    if not path.startswith(PREFIX + "/"):
        return None, None
    tail = path[len(PREFIX) + 1:]
    app, sep, rest = tail.partition("/")
    if not sep:
        return None, None
    return app, "/" + rest


def handle(method, path, headers, body):
    raw = path if isinstance(path, str) else ""
    # Strip query only for suffix matching; keep raw for probe detection.
    noq = raw.split("?", 1)[0]
    app, rest = _splitsuffix(noq)
    if app is None:
        return None
    if isinstance(body, (bytes, bytearray)):
        try:
            bstr = bytes(body).decode("utf-8", errors="replace")
        except Exception:
            bstr = ""
    else:
        bstr = body or ""

    # --- HFS: baseline vs template-parse probe (query carries the probe) ---
    if app in ("hfs-vuln", "hfs-fixed") and method == "GET" and (rest == "/" or rest == ""):
        probe = ("section-probe-benign" in raw or "%7B" in raw
                 or "?n=" in raw or "&n=" in raw)
        if app == "hfs-vuln":
            if probe:
                return (200, "text/html", _HFS_VULN_PROBE)
            return (200, "text/html", _HFS_VULN_BASE)
        return (200, "text/html", _HFS_FIXED_BASE)

    # --- ValvePress: POST csv.php, vuln evaluates q (rows differ) ---
    if rest == "/wp-content/plugins/automatic/inc/csv.php" and method == "POST":
        if app == "valvepress-vuln":
            if "2-1" in bstr or "2%2D1" in bstr or "2+-%+1" in bstr:
                return (200, "text/csv", 'q="SELECT 2-1"\nrow: 1\n')
            return (200, "text/csv", 'q="SELECT 1"\nrow: 1\n')
        if app == "valvepress-fixed":
            return (200, "text/csv", 'q="static"\nrow: 1\n')

    # --- LayerSlider: ajax arithmetic differential (query carries id[where]) ---
    if rest == "/wp-admin/admin-ajax.php" and method == "GET":
        if app == "ls-vuln":
            return (200, "text/html", _LS_AJAX_PAGE)
        if app == "ls-fixed":
            if "2-1" in raw or "2%2D1" in raw:
                return (200, "text/html", _LS_AJAX_PAGE_B)
            return (200, "text/html", _LS_AJAX_PAGE)

    # --- CosmicSting: XML request parsed (400+xml error) vs JSON 200 ---
    if rest == "/rest/all/V1/guest-carts/cosmicstingprobe/estimate-shipping-methods" \
            and method == "POST":
        if app == "cosmic-vuln":
            ctype = _header(headers, "Content-Type")
            if "xml" in ctype.lower() or bstr.lstrip().startswith("<?xml"):
                return (400, "application/json", _COSMIC_XML_ERR)
            return (200, "application/json", _COSMIC_JSON)
        if app == "cosmic-fixed":
            return (200, "application/json", _COSMIC_JSON)

    # --- PAN-OS: marker-file handshake (random fname in path / Cookie) ---
    m = re.search(r"/panos3400-(vuln|fixed)/global-protect/portal/images/([A-Za-z0-9_.-]+\.txt)",
                  noq)
    if m and method == "GET":
        if m.group(1) == "vuln" and m.group(2) in _CREATED:
            return (403, "text/plain", "forbidden")
        return (404, "text/plain", "not found")
    if re.search(r"/panos3400-(vuln|fixed)/ssl-vpn/hipreport\.esp$", noq) \
            and method == "POST":
        fixed = "/panos3400-fixed/" in noq
        if fixed:
            return (404, "text/plain", "not found")
        cookie = _header(headers, "Cookie")
        fm = re.search(r"([0-9a-fA-F]{16}\.txt)", cookie)
        if fm:
            _CREATED.add(fm.group(1))
        return (200, "text/html", "Invalid required input parameters.\n")

    return None


CASES = [
    ("cve-2024-0204_goanywhere.py",
     ["-u", "{BASE}/fx/a/goanywhere-vuln"], ["-u", "{BASE}/fx/a/goanywhere-fixed"]),
    ("cve-2024-11080_postgrid.py",
     ["-u", "{BASE}/fx/a/postgrid-vuln"], ["-u", "{BASE}/fx/a/postgrid-fixed"]),
    ("cve-2024-1709_screenconnect.py",
     ["-u", "{BASE}/fx/a/screenconnect-vuln"], ["-u", "{BASE}/fx/a/screenconnect-fixed"]),
    ("cve-2024-21887_ivanti.py",
     ["-u", "{BASE}/fx/a/ivanti21887-vuln"], ["-u", "{BASE}/fx/a/ivanti21887-fixed"]),
    ("cve-2024-23692_hfs.py",
     ["-u", "{BASE}/fx/a/hfs-vuln"], ["-u", "{BASE}/fx/a/hfs-fixed"]),
    ("cve-2024-27956_valvepress.py",
     ["-u", "{BASE}/fx/a/valvepress-vuln"], ["-u", "{BASE}/fx/a/valvepress-fixed"]),
    ("cve-2024-28000_litespeed.py",
     ["-u", "{BASE}/fx/a/litespeed-vuln"], ["-u", "{BASE}/fx/a/litespeed-fixed"]),
    ("cve-2024-2879_layerslider.py",
     ["-u", "{BASE}/fx/a/ls-vuln"], ["-u", "{BASE}/fx/a/ls-fixed"]),
    ("cve-2024-3400_panos.py",
     ["-u", "{BASE}/fx/a/panos3400-vuln"], ["-u", "{BASE}/fx/a/panos3400-fixed"]),
    ("cve-2024-34102_cosmicsting.py",
     ["-u", "{BASE}/fx/a/cosmic-vuln"], ["-u", "{BASE}/fx/a/cosmic-fixed"]),
    ("cve-2024-40711_veeam.py",
     ["-u", "{BASE}/fx/a/veeam-vuln"], ["-u", "{BASE}/fx/a/veeam-fixed"]),
    ("cve-2024-4577_phpcgi.py",
     ["-u", "{BASE}/fx/a/phpcgi-vuln"], ["-u", "{BASE}/fx/a/phpcgi-fixed"]),
    ("secret_sweep.py",
     ["-d", "{PLANT}/dirty"], ["-d", "{PLANT}/clean"]),
]

PLANT = {
    "dirty/creds.env":
        "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE\n"
        "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY\n",
    "dirty/app.js":
        "const token = \"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIn0."
        "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c\";\n"
        "const wallet = \"0x52908400098527886E0F7030069857D2E4169EE7\";\n",
    "clean/notes.txt":
        "hello world: this directory is clean.\n"
        "nothing sensitive here, just lunch plans.\n",
    "clean/app.py":
        "def greet(name):\n"
        "    return 'hello ' + name\n",
}

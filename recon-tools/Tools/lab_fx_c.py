"""Fixture module FxC (PREFIX /fx/c).

Covers: cve-2026-0770_langflow, cve-2026-12394_memberglut,
cve-2026-1281_ivanti_epmm_rce, cve-2026-1405_slider_future_upload,
cve-2026-15826_profilebuilder, cve-2026-16310_memberdash,
cve-2026-18431_avada, cve-2026-20079_fmc, cve-2026-21858_n8n,
cve-2026-23550_modular_ds, cve-2026-2631_datalogics_priv_esc.

OMIT cve-2026-0073_android_adb_bypass: raw TCP socket (ADB port 5555)
protocol, not HTTP — cannot be emulated by this HTTP fixture harness;
manual drill only.
OMIT auth_boundary.py: always-writes (CSV header + one row per endpoint
is written even when every endpoint is gated), so fixed-vs-vuln runs are
not discriminable via output missing/empty; manual drill only.
OMIT cve-2026-20079_fmc from CASES: scanner-side bug (fetch_no_redirect
passes context= to OpenerDirector.open, TypeError -> always UNKNOWN, no
fixture can discriminate); routes kept below so the CASE can be re-added
once the scanner is fixed. Manual drill only until then.

Contract: PREFIX / ROUTES {(method, full_path): (status, ctype, body)} /
handle(method, path, headers, body) -> (status, ctype, body) | None /
CASES [(script, vuln_args, fixed_args)] (arg vectors complete minus
output/timeout; {BASE} replaced by parent) / PLANT {relpath: content}
materialized by parent into a tempdir, referenced as {PLANT} ({BASE}
inside PLANT content is replaced too).
"""

try:
    from urllib.parse import parse_qs
except ImportError:  # pragma: no cover - py2 fallback, never hit
    parse_qs = None

PREFIX = "/fx/c"

# ---------------------------------------------------------------------------
# Static routes: (method, full_path) -> (status, content-type, body)
# ---------------------------------------------------------------------------
ROUTES = {}


def _add(method, full_path, status=200, ctype="text/plain", body=""):
    ROUTES[(method, full_path)] = (status, ctype, body)


# --- cve-2026-0770 langflow: GET /api/v1/auto_login 200 + access_token ---
_add("GET", "/fx/c/langflow-vuln/api/v1/auto_login", 200,
     "application/json",
     '{"access_token": "eyJma3giOiJ2dWxuIn0", "token_type": "bearer"}')
_add("GET", "/fx/c/langflow-fixed/api/v1/auto_login", 404,
     "application/json", '{"detail": "Not Found"}')

# --- cve-2026-12394 memberglut: readme Stable Tag gate + /register/ markers
_add("GET", "/fx/c/memberglut-vuln/wp-content/plugins/memberglut/readme.txt",
     200, "text/plain",
     "=== MemberGlut ===\nStable Tag: 1.1.4\nRequires at least: 6.0\n")
_add("GET", "/fx/c/memberglut-vuln/register/", 200, "text/html",
     "<html><body><form><input name=\"register_nonce\" value=\"abc123\">"
     "<input type=\"hidden\" name=\"memberglut_register\" value=\"1\">"
     "</form></body></html>")
_add("GET", "/fx/c/memberglut-fixed/wp-content/plugins/memberglut/readme.txt",
     200, "text/plain",
     "=== MemberGlut ===\nStable Tag: 1.1.5\nRequires at least: 6.0\n")

# --- cve-2026-1281 ivanti EPMM: login marker + register echo of "vulnerable"
_add("GET", "/fx/c/ivanti-vuln/mifs/user/login.jsp", 200, "text/html",
     "<html><body>Ivanti EPMM login</body></html>")
_add("POST", "/fx/c/ivanti-vuln/mifs/aad/api/v1/device/register", 200,
     "application/json", '{"result": "vulnerable"}')
_add("GET", "/fx/c/ivanti-fixed/mifs/user/login.jsp", 200, "text/html",
     "<html><body>Ivanti EPMM login</body></html>")
for _p in ("/mifs/aad/api/v1/device/register",
           "/mifs/asfV3/api/v1/device/register",
           "/mifs/aad/api/v2/device/certificate",
           "/mifs/aad/api/v1/device/wakeup"):
    _add("POST", "/fx/c/ivanti-fixed" + _p, 400, "application/json",
         '{"error": "bad request"}')

# --- cve-2026-15826 profilebuilder (SLUG profile-builder, FIXED 3.16.4) ---
_add("GET",
     "/fx/c/profilebuilder-vuln/wp-content/plugins/profile-builder/readme.txt",
     200, "text/plain",
     "=== Profile Builder ===\nStable tag: 3.16.4\nRequires at least: 6.0\n")
_add("GET", "/fx/c/profilebuilder-vuln/wp-content/plugins/profile-builder/",
     200, "text/html",
     "<html><body>Index of profile-builder</body></html>")
_add("GET",
     "/fx/c/profilebuilder-fixed/wp-content/plugins/profile-builder/readme.txt",
     200, "text/plain",
     "=== Profile Builder ===\nStable tag: 3.16.5\nRequires at least: 6.0\n")

# --- cve-2026-16310 memberdash (SLUG memberdash, FIXED 1.8.5) ---
_add("GET", "/fx/c/memberdash-vuln/wp-content/plugins/memberdash/readme.txt",
     200, "text/plain",
     "=== MemberDash ===\nStable tag: 1.8.5\nRequires at least: 6.0\n")
_add("GET", "/fx/c/memberdash-fixed/wp-content/plugins/memberdash/readme.txt",
     200, "text/plain",
     "=== MemberDash ===\nStable tag: 1.8.6\nRequires at least: 6.0\n")

# --- cve-2026-18431 avada (Avada <= 7.16 + Fusion Builder <= 3.16) ---
_add("GET", "/fx/c/avada-vuln/wp-content/themes/Avada/style.css", 200,
     "text/css",
     "/*\nTheme Name: Avada\nVersion: 7.16\n*/\n")
_add("GET",
     "/fx/c/avada-vuln/wp-content/plugins/fusion-builder/readme.txt", 200,
     "text/plain", "=== Fusion Builder ===\nStable tag: 3.16\n")
_add("GET", "/fx/c/avada-fixed/wp-content/themes/Avada/style.css", 200,
     "text/css",
     "/*\nTheme Name: Avada\nVersion: 7.17\n*/\n")
_add("GET",
     "/fx/c/avada-fixed/wp-content/plugins/fusion-builder/readme.txt", 200,
     "text/plain", "=== Fusion Builder ===\nStable tag: 3.17\n")

# --- cve-2026-20079 fmc: 200 vs redirect (no Location header possible;
# fixed therefore reads as UNKNOWN -> no output, still discriminable) ---
_add("GET", "/fx/c/fmc-vuln/help/about.cgi", 200, "text/html",
     "<html><body>Cisco FMC about</body></html>")
_add("GET", "/fx/c/fmc-fixed/help/about.cgi", 302, "text/plain", "")

# --- cve-2026-21858 n8n: fingerprint + bypassed-endpoint status ---
_N8N_HOME = ("<html><head><title>n8n</title></head>"
             "<body>n8n workflow automation 1.100.0</body></html>")
_add("GET", "/fx/c/n8n-vuln/", 200, "text/html", _N8N_HOME)
_add("GET", "/fx/c/n8n-vuln/rest/workflows", 200, "application/json",
     '{"data": [{"id": 1, "name": "test workflow"}]}')
_add("GET", "/fx/c/n8n-vuln/api/v1/workflows", 200, "application/json",
     '{"data": [{"id": 1, "name": "test workflow"}]}')
_add("GET", "/fx/c/n8n-fixed/", 200, "text/html", _N8N_HOME)
_add("GET", "/fx/c/n8n-fixed/rest/workflows", 401, "application/json",
     '{"message": "unauthorized"}')
_add("GET", "/fx/c/n8n-fixed/api/v1/workflows", 401, "application/json",
     '{"message": "unauthorized"}')

# --- cve-2026-23550 modular-ds: login cookie in body + wp-admin dashboard --
_add("POST",
     "/fx/c/modular-vuln/wp-content/plugins/modular-ds/api/modular-connector/login",
     200, "application/json",
     '{"success": true, "cookies": "wordpress_logged_in_user=tokenabc123"}')
_add("GET", "/fx/c/modular-vuln/wp-admin/", 200, "text/html",
     "<html><body>dashboard wp-admin-bar</body></html>")
_add("POST",
     "/fx/c/modular-fixed/wp-content/plugins/modular-ds/api/modular-connector/login",
     403, "application/json", '{"error": "forbidden"}')

# --- cve-2026-2631 datalogics: plugin presence + direct admin create -------
_add("GET", "/fx/c/datalogics-vuln/wp-json/datalogics/v1/", 200,
     "application/json", '{"namespace": "datalogics/v1"}')
_add("POST", "/fx/c/datalogics-vuln/wp-json/datalogics/v1/user/create", 201,
     "application/json", '{"id": 2, "created": true}')


# ---------------------------------------------------------------------------
# Dynamic handler (query string stripped here; static ROUTES keep
# matching the query-stripped path in the parent harness).
# Serves the slider-future upload round-trip, which needs the request
# body (image_url basename) and Host header to build the absolute URL
# the scanner fetches back for verification.
# ---------------------------------------------------------------------------
def handle(method, path, headers, body):
    raw = path or "/"
    clean = raw.split("?", 1)[0]
    get_hdr = None
    if hasattr(headers, "get"):
        def get_hdr(name, default=None):
            try:
                return headers.get(name, default)
            except Exception:
                return default
        host = get_hdr("Host", None) or get_hdr("host", "127.0.0.1")
    elif isinstance(headers, dict):
        host = headers.get("Host", headers.get("host", "127.0.0.1"))
    else:
        host = "127.0.0.1"

    # Slider-future arbitrary upload (vuln only; fixed has no routes -> 404).
    if clean == "/fx/c/slider-vuln/wp-json/slider-future/v1/upload-image/" \
            and method == "POST":
        if isinstance(body, (bytes, bytearray)):
            try:
                text = bytes(body).decode("utf-8", errors="replace")
            except Exception:
                text = ""
        else:
            text = body or ""
        image_url = ""
        if parse_qs is not None:
            try:
                qs = parse_qs(text, keep_blank_values=True)
                vals = qs.get("image_url", [])
                if vals:
                    image_url = vals[0]
            except Exception:
                image_url = ""
        basename = (image_url.rsplit("/", 1)[-1].split("?", 1)[0]
                    .strip() or "fx-shell.php")
        url = "http://%s/fx/c/slider-vuln/wp-content/uploads/%s" % (
            host, basename)
        return (200, "application/json", '{"url": "%s"}' % url)

    if clean.startswith("/fx/c/slider-vuln/wp-content/uploads/") \
            and method == "GET":
        return (200, "text/html", "<!-- PWNED -->")

    return None


# ---------------------------------------------------------------------------
# Mass-mode target lists (single-target mode of these scanners never
# writes the output file, so drill them via -l with 2 identical lines
# to force the mass branch).
# ---------------------------------------------------------------------------
PLANT = {
    "ivanti-vuln.txt":
        "{BASE}/fx/c/ivanti-vuln\n{BASE}/fx/c/ivanti-vuln\n",
    "ivanti-fixed.txt":
        "{BASE}/fx/c/ivanti-fixed\n{BASE}/fx/c/ivanti-fixed\n",
    "slider-vuln.txt":
        "{BASE}/fx/c/slider-vuln\n{BASE}/fx/c/slider-vuln\n",
    "slider-fixed.txt":
        "{BASE}/fx/c/slider-fixed\n{BASE}/fx/c/slider-fixed\n",
    "datalogics-vuln.txt":
        "{BASE}/fx/c/datalogics-vuln\n{BASE}/fx/c/datalogics-vuln\n",
    "datalogics-fixed.txt":
        "{BASE}/fx/c/datalogics-fixed\n{BASE}/fx/c/datalogics-fixed\n",
}

CASES = [
    ("cve-2026-0770_langflow.py",
     ["-u", "{BASE}/fx/c/langflow-vuln"],
     ["-u", "{BASE}/fx/c/langflow-fixed"]),
    ("cve-2026-12394_memberglut.py",
     ["-u", "{BASE}/fx/c/memberglut-vuln"],
     ["-u", "{BASE}/fx/c/memberglut-fixed"]),
    ("cve-2026-1281_ivanti_epmm_rce.py",
     ["-l", "{PLANT}/ivanti-vuln.txt"],
     ["-l", "{PLANT}/ivanti-fixed.txt"]),
    ("cve-2026-1405_slider_future_upload.py",
     ["-l", "{PLANT}/slider-vuln.txt", "-s", "http://127.0.0.1/fx-shell.php"],
     ["-l", "{PLANT}/slider-fixed.txt", "-s", "http://127.0.0.1/fx-shell.php"]),
    ("cve-2026-15826_profilebuilder.py",
     ["-u", "{BASE}/fx/c/profilebuilder-vuln"],
     ["-u", "{BASE}/fx/c/profilebuilder-fixed"]),
    ("cve-2026-16310_memberdash.py",
     ["-u", "{BASE}/fx/c/memberdash-vuln"],
     ["-u", "{BASE}/fx/c/memberdash-fixed"]),
    ("cve-2026-18431_avada.py",
     ["-u", "{BASE}/fx/c/avada-vuln"],
     ["-u", "{BASE}/fx/c/avada-fixed"]),
    ("cve-2026-21858_n8n.py",
     ["-u", "{BASE}/fx/c/n8n-vuln"],
     ["-u", "{BASE}/fx/c/n8n-fixed"]),
    ("cve-2026-23550_modular_ds.py",
     ["-u", "{BASE}/fx/c/modular-vuln"],
     ["-u", "{BASE}/fx/c/modular-fixed"]),
    ("cve-2026-20079_fmc.py",
     ["-u", "{BASE}/fx/c/fmc-vuln"],
     ["-u", "{BASE}/fx/c/fmc-fixed"]),
    ("cve-2026-2631_datalogics_priv_esc.py",
     ["-l", "{PLANT}/datalogics-vuln.txt"],
     ["-l", "{PLANT}/datalogics-fixed.txt"]),
]

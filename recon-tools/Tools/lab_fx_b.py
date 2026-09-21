"""Fixture module B for the lab drill harness (PREFIX /fx/b).

Covers: cve-2025-24813_tomcat, cve-2025-25257_fortiweb,
cve-2025-29927_nextjs, cve-2025-32432_craftcms, cve-2025-3248_langflow,
cve-2025-53690_sitecore, cve-2025-55182_react2shell, cve-2025-57819_freepbx,
cve-2025-8489_kingaddons. Kentico routes are emulated correctly below but have
no CASE: cve-2025-2746_kentico.py check_target references undefined m1/m2/s2,
so it raises NameError on any reachable 200/500 endpoint and always yields
UNKNOWN (never writes output) -- unwinnable until the scanner is fixed.
OMIT header_audit: it writes its output file even for clean targets, so
file-hit cannot discriminate vuln from fixed.
"""

PREFIX = "/fx/b"


def _r(status, ctype, body):
    return (status, ctype, body)


_VULN_SOAP_OK = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
    "<soap:Body><GetSecurityDataResponse><GetSecurityDataResult>ok"
    "</GetSecurityDataResult></GetSecurityDataResponse></soap:Body>"
    "</soap:Envelope>"
)
_VULN_SQL_ERR = (
    "System.Data.SqlClient.SqlException: Unclosed quotation mark after "
    "the character string 'checkfirst''. Incorrect syntax near 'checkfirst'."
)

ROUTES = {
    # --- tomcat: version fingerprint via GET / ---
    ("GET", PREFIX + "/tomcat-vuln/"): _r(
        200, "text/html",
        "<html><head><title>Apache Tomcat/9.0.80</title></head>"
        "<body>Apache Tomcat/9.0.80 - Error report</body></html>"),
    ("OPTIONS", PREFIX + "/tomcat-vuln/"): _r(200, "text/plain", ""),
    ("GET", PREFIX + "/tomcat-fixed/"): _r(
        200, "text/html",
        "<html><head><title>Apache Tomcat/9.0.99</title></head>"
        "<body>Apache Tomcat/9.0.99 - Error report</body></html>"),
    ("OPTIONS", PREFIX + "/tomcat-fixed/"): _r(200, "text/plain", ""),
    # --- fortiweb: fingerprint via GET / ---
    ("GET", PREFIX + "/forti-vuln/"): _r(
        200, "text/html",
        "<html><head><title>FortiWeb 7.4.1</title></head>"
        "<body>FortiWeb 7.4.1 login</body></html>"),
    ("GET", PREFIX + "/forti-fixed/"): _r(
        200, "text/html",
        "<html><head><title>FortiWeb 7.8.0</title></head>"
        "<body>FortiWeb 7.8.0 login</body></html>"),
    # --- nextjs fixed: no bypass flip (always 403) ---
    # (nextjs-vuln is fully dynamic in handle(): header-sensitive flip.)
    ("GET", PREFIX + "/nextjs-fixed/"): _r(403, "text/plain", "Forbidden"),
    # --- craftcms: generator-meta version gate ---
    ("GET", PREFIX + "/craft-vuln/"): _r(
        200, "text/html",
        '<html><head><meta name="generator" content="Craft CMS 5.6.10">'
        "</head><body>Craft CMS 5.6.10</body></html>"),
    ("GET", PREFIX + "/craft-vuln/admin/login"): _r(
        200, "text/html",
        '<html><head><meta name="generator" content="Craft CMS 5.6.10">'
        "</head><body>Craft CMS login __craft CraftSessionId</body></html>"),
    ("GET", PREFIX + "/craft-fixed/"): _r(
        200, "text/html",
        '<html><head><meta name="generator" content="Craft CMS 5.6.17">'
        "</head><body>Craft CMS 5.6.17</body></html>"),
    ("GET", PREFIX + "/craft-fixed/admin/login"): _r(
        200, "text/html",
        '<html><head><meta name="generator" content="Craft CMS 5.6.17">'
        "</head><body>Craft CMS login __craft CraftSessionId</body></html>"),
    # --- langflow: version + validate/code shape ---
    ("GET", PREFIX + "/langflow-vuln/api/v1/version"): _r(
        200, "application/json", '{"version": "1.2.0"}'),
    ("POST", PREFIX + "/langflow-vuln/api/v1/validate/code"): _r(
        200, "application/json",
        '{"success": true, "functions": [], "imports": []}'),
    ("GET", PREFIX + "/langflow-fixed/api/v1/version"): _r(
        200, "application/json", '{"version": "1.3.0"}'),
    ("POST", PREFIX + "/langflow-fixed/api/v1/validate/code"): _r(
        403, "application/json", '{"detail": "auth required"}'),
    # --- sitecore: __VIEWSTATE login form ---
    ("GET", PREFIX + "/sitecore-vuln/sitecore/login"): _r(
        200, "text/html",
        '<html><head><title>Sitecore.NET 9.0 Login</title></head><body>'
        '<form method="post">Sitecore login'
        '<input type="hidden" name="__VIEWSTATE" value="abc123" />'
        "</form></body></html>"),
    ("GET", PREFIX + "/sitecore-vuln/sitecore/service/keepalive.aspx"): _r(
        200, "text/plain", "Sitecore.NET 9.0 keepalive"),
    ("GET", PREFIX + "/sitecore-fixed/sitecore/login"): _r(
        404, "text/plain", "not found"),
    ("GET", PREFIX + "/sitecore-fixed/sitecore/service/keepalive.aspx"): _r(
        404, "text/plain", "not found"),
    # --- react2shell: Next.js markers + flight probe ---
    ("GET", PREFIX + "/react-vuln/"): _r(
        200, "text/html",
        '<html><body><div id="__NEXT_DATA__">react-dom/19.0.0</div>'
        '<script src="/_next/static/chunks/app.js"></script></body></html>'),
    ("POST", PREFIX + "/react-vuln/"): _r(
        500, "text/x-component",
        '{"error": "Internal Server Error", "digest": "abc123XYZ"}'),
    ("GET", PREFIX + "/react-fixed/"): _r(
        200, "text/html",
        '<html><body><div id="__NEXT_DATA__">react-dom/19.0.0</div>'
        '<script src="/_next/static/chunks/app.js"></script></body></html>'),
    ("POST", PREFIX + "/react-fixed/"): _r(
        404, "text/plain", "not found"),
    # --- freepbx served dynamically in handle() (raw path keeps query) ---
    # --- kingaddons: readme stable-tag gate + form marker on / ---
    ("GET", PREFIX + "/king-vuln/wp-content/plugins/king-addons/readme.txt"): _r(
        200, "text/plain",
        "=== King Addons for Elementor ===\nStable tag: 25.1.5\n"),
    ("GET", PREFIX + "/king-vuln/"): _r(
        200, "text/html",
        "<html><body><div class=\"king_addons_login\">Login_Register_Form"
        "</div></body></html>"),
    ("GET", PREFIX + "/king-fixed/wp-content/plugins/king-addons/readme.txt"): _r(
        200, "text/plain",
        "=== King Addons for Elementor ===\nStable tag: 51.2.0\n"),
    ("GET", PREFIX + "/king-fixed/"): _r(
        200, "text/html", "<html><body>hello</body></html>"),
}


def _hget(headers, name):
    if not headers:
        return ""
    if hasattr(headers, "get"):
        try:
            v = headers.get(name)
            if v is not None:
                return v
            for k in getattr(headers, "keys", lambda: [])():
                if str(k).lower() == name.lower():
                    return headers[k]
        except Exception:
            pass
        return ""
    try:
        items = dict(headers)
        for k, v in items.items():
            if str(k).lower() == name.lower():
                return v
    except Exception:
        pass
    return ""


def _s(body):
    if body is None:
        return ""
    if isinstance(body, (bytes, bytearray)):
        return bytes(body).decode("utf-8", errors="replace")
    return str(body)


def handle(method, path, headers, body):
    """Dynamic routes: random-ID PUTs, auth/header-sensitive probes."""
    base = path.split("?", 1)[0]
    if not base.startswith(PREFIX + "/"):
        return None
    text = _s(body)

    # --- tomcat: empty-body PUT probe to random /PUT-<rand>.txt ---
    for app, vuln in (("tomcat-vuln", True), ("tomcat-fixed", False)):
        pre = PREFIX + "/" + app
        if base == pre + "/" and method == "PUT":
            return None  # not a probe path; fall through to static
        if base.startswith(pre + "/PUT-") and base.endswith(".txt"):
            if method == "PUT":
                if vuln:
                    return (201, "text/plain", "")
                return (403, "text/plain", "forbidden")
            if method == "DELETE":
                return (200, "text/plain", "")
            return None
        if base == pre + "/" and method == "DELETE":
            return (200, "text/plain", "")

    # --- fortiweb: Authorization-header-sensitive fabric endpoint ---
    for app, vuln in (("forti-vuln", True), ("forti-fixed", False)):
        if base == PREFIX + "/" + app + "/api/fabric/device/status":
            auth = _hget(headers, "Authorization")
            low = auth.lower()
            if vuln and ("'" in auth or "union" in low):
                return (200, "application/json",
                        '{"serial": "FGVM123", "device_name": "fw1", '
                        '"device_type": "fortiweb", "fabric": "ok"}')
            return (401, "application/json", '{"error": "unauthorized"}')

    # --- nextjs: X-Middleware-Subrequest bypass flip on / ---
    if base == PREFIX + "/nextjs-vuln/":
        if _hget(headers, "X-Middleware-Subrequest"):
            return (200, "text/html", "<html><body>ok</body></html>")
        return (403, "text/plain", "Forbidden")

    # --- freepbx: query-agnostic fallback (harness may strip the query) ---
    if base == PREFIX + "/freepbx-vuln/admin/ajax.php":
        return (200, "text/html",
                "XPATH syntax error near '' ; check user freepbxuser@localhost")
    if base == PREFIX + "/freepbx-fixed/admin/ajax.php":
        return (200, "text/html", "no records found for model")

    # --- kentico: quote-differential on the SyncServer envelope ---
    for app, vuln in (("kentico-vuln", True), ("kentico-fixed", False)):
        if base == PREFIX + "/" + app + "/CMSPages/Staging/SyncServer.asmx":
            if method != "POST":
                return (200, "text/xml", _VULN_SOAP_OK)
            if vuln and "checkfirst'" in text:
                return (500, "text/xml", _VULN_SQL_ERR)
            return (200, "text/xml", _VULN_SOAP_OK)

    return None


CASES = [
    ("cve-2025-24813_tomcat.py",
     ["-u", "{BASE}/fx/b/tomcat-vuln"],
     ["-u", "{BASE}/fx/b/tomcat-fixed"]),
    ("cve-2025-25257_fortiweb.py",
     ["-u", "{BASE}/fx/b/forti-vuln"],
     ["-u", "{BASE}/fx/b/forti-fixed"]),
    ("cve-2025-29927_nextjs.py",
     ["-u", "{BASE}/fx/b/nextjs-vuln"],
     ["-u", "{BASE}/fx/b/nextjs-fixed"]),
    ("cve-2025-32432_craftcms.py",
     ["-u", "{BASE}/fx/b/craft-vuln"],
     ["-u", "{BASE}/fx/b/craft-fixed"]),
    ("cve-2025-3248_langflow.py",
     ["-u", "{BASE}/fx/b/langflow-vuln"],
     ["-u", "{BASE}/fx/b/langflow-fixed"]),
    ("cve-2025-53690_sitecore.py",
     ["-u", "{BASE}/fx/b/sitecore-vuln"],
     ["-u", "{BASE}/fx/b/sitecore-fixed"]),
    ("cve-2025-55182_react2shell.py",
     ["-u", "{BASE}/fx/b/react-vuln"],
     ["-u", "{BASE}/fx/b/react-fixed"]),
    ("cve-2025-57819_freepbx.py",
     ["-u", "{BASE}/fx/b/freepbx-vuln"],
     ["-u", "{BASE}/fx/b/freepbx-fixed"]),
    ("cve-2025-8489_kingaddons.py",
     ["-u", "{BASE}/fx/b/king-vuln"],
     ["-u", "{BASE}/fx/b/king-fixed"]),
    ("cve-2025-2746_kentico.py",
     ["-u", "{BASE}/fx/b/kentico-vuln"],
     ["-u", "{BASE}/fx/b/kentico-fixed"]),
]

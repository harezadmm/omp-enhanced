"""Fixture module E (PREFIX /fx/e) for the lab drill harness.

Covers: cve-2026-61979_miniorange, cve-2026-63030_wpcore_batch,
cve-2026-65883_aimy, cve-2026-72898_metabase, cve-2026-75816_frontendadmin,
cve-2026-86426_librenms, cve-2026-9198_langflow, cve-gravityforms_upload,
js_miner.
OMIT (manual-drill, undrillable on the shared fixture server):
- cve-2026-81578_papercut: papercut_base() drops the URL path (port-only base),
  so vuln/fixed prefixes are indistinguishable on one server.
- cve-2026-9082_drupal_sqli: single-target mode never writes an output file and
  the script has no --timeout flag, so it cannot pass the drill scoreboard.
- rate_probe.py: main() always writes the output file (even for NO-LIMIT), so
  vuln vs fixed runs cannot be told apart via output file presence.
"""

PREFIX = "/fx/e"

_MO_README_VULN = (
    "=== miniOrange SAML 2.0 Single Sign On ===\n"
    "Stable Tag: 5.4.3\n"
)
_MO_README_FIXED = (
    "=== miniOrange SAML 2.0 Single Sign On ===\n"
    "Stable Tag: 5.4.5\n"
)
_MO_METADATA = (
    '<?xml version="1.0"?>\n'
    '<EntityDescriptor entityID="https://example.com/saml" '
    'xmlns="urn:oasis:names:tc:SAML:2.0:metadata">'
    '<SPSSODescriptor/></EntityDescriptor>'
)

_CB_WPJSON_VULN = '{"namespaces":["wp/v2"],"generator":"WordPress 6.9.2"}'
_CB_WPJSON_FIXED = '{"namespaces":["wp/v2"],"generator":"WordPress 6.9.5"}'
_CB_BATCH_OK = '{"responses":[{"status":200,"body":"{\\"id\\":\\"post\\"}","headers":{}}]}'
_CB_BATCH_NO_ROUTE = (
    '{"code":"rest_no_route","message":"No route was found matching the URL",'
    '"data":{"status":404}}'
)

_AY_FORM = (
    '<html><body><h1>Joomla registration</h1>'
    '<form action="/index.php" method="post">'
    '<input type="text" name="username"/>'
    '<input type="hidden" name="clfgd" value="1"/>'
    '<p>Protected by Aimy Captcha-Less Form Guard %s</p>'
    '</form></body></html>'
)

_MB_HOME_VULN = (
    "<html><head><title>Metabase</title></head><body>"
    "<p>Powered by metabase v0.60.3 analytics dashboard</p></body></html>"
)
_MB_HOME_FIXED = (
    "<html><head><title>Metabase</title></head><body>"
    "<p>Powered by metabase v0.57.3 analytics dashboard</p></body></html>"
)
_MB_CTRL = '{"message":"Invalid token"}'
_MB_ECHO = (
    '{"errors":{"token":["should be a string"]},'
    '"debug":"query token echo {:select 1}"}'
)

_FA_README_VULN = "=== Frontend Admin ===\nStable tag: 3.29.10\n"
_FA_README_FIXED = "=== Frontend Admin ===\nStable tag: 3.29.13\n"

_LN_HOME_VULN = (
    "<html><head><title>LibreNMS</title></head><body>"
    "<p>LibreNMS 26.7.0 network monitor</p></body></html>"
)
_LN_HOME_FIXED = (
    "<html><head><title>LibreNMS</title></head><body>"
    "<p>LibreNMS 26.8.0 network monitor</p></body></html>"
)
_LN_DEVICES = '{"devices":[{"id":1,"hostname":"core-sw"}],"status":"ok"}'

_LF_TOKEN = '{"access_token":"drill-fixture-token","token_type":"bearer"}'
_LF_ABSENT = '{"detail":"Not Found"}'

_GF_HOME_VULN = (
    '<html><head><title>Shop</title></head><body>'
    '<script src="/wp-content/plugins/gravityforms/js/frontend.min.js?ver=2.9.10">'
    "</script>"
    '<form class="gform" method="post" enctype="multipart/form-data">'
    '<input type="file" name="gform_fileupload"/>'
    "</form></body></html>"
)
_GF_HOME_FIXED = (
    '<html><head><title>Shop</title></head><body>'
    '<script src="/wp-content/plugins/gravityforms/js/frontend.min.js?ver=3.0.3">'
    "</script>"
    '<form class="gform" method="post">'
    '<input type="text" name="email"/>'
    "</form></body></html>"
)

_JS_HOME_VULN = (
    '<html><head><title>App</title></head><body>'
    '<script src="/fx/e/js-vuln/static/app.js"></script>'
    "</body></html>"
)
_JS_APP = 'const u = fetch("/api/v1/widgets");\nu.then(r => r.json());\n'
_JS_HOME_FIXED = "<html><head><title>App</title></head><body><p>hello</p></body></html>"

ROUTES = {
    ("GET", PREFIX + "/mo-vuln/wp-content/plugins/miniorange-saml-20-single-sign-on/readme.txt"): (
        200, "text/plain", _MO_README_VULN),
    ("GET", PREFIX + "/mo-fixed/wp-content/plugins/miniorange-saml-20-single-sign-on/readme.txt"): (
        200, "text/plain", _MO_README_FIXED),
    ("GET", PREFIX + "/cb-vuln/wp-json/"): (200, "application/json", _CB_WPJSON_VULN),
    ("GET", PREFIX + "/cb-fixed/wp-json/"): (200, "application/json", _CB_WPJSON_FIXED),
    ("GET", PREFIX + "/ay-vuln/index.php"): (200, "text/html", _AY_FORM % "19.2.0"),
    ("GET", PREFIX + "/ay-fixed/index.php"): (200, "text/html", _AY_FORM % "21.1.0"),
    ("GET", PREFIX + "/mb-vuln/"): (200, "text/html", _MB_HOME_VULN),
    ("GET", PREFIX + "/mb-fixed/"): (200, "text/html", _MB_HOME_FIXED),
    ("GET", PREFIX + "/fa-vuln/wp-content/plugins/acf-frontend-form-element/readme.txt"): (
        200, "text/plain", _FA_README_VULN),
    ("GET", PREFIX + "/fa-fixed/wp-content/plugins/acf-frontend-form-element/readme.txt"): (
        200, "text/plain", _FA_README_FIXED),
    ("GET", PREFIX + "/ln-vuln/"): (200, "text/html", _LN_HOME_VULN),
    ("GET", PREFIX + "/ln-fixed/"): (200, "text/html", _LN_HOME_FIXED),
    ("GET", PREFIX + "/ln-vuln/api/v0/devices"): (200, "application/json", _LN_DEVICES),
    ("GET", PREFIX + "/ln-fixed/api/v0/devices"): (
        401, "application/json", '{"message":"Unauthenticated."}'),
    ("GET", PREFIX + "/lf-vuln/api/v1/auto_login"): (200, "application/json", _LF_TOKEN),
    ("GET", PREFIX + "/lf-fixed/api/v1/auto_login"): (404, "application/json", _LF_ABSENT),
    ("GET", PREFIX + "/gf-vuln/"): (200, "text/html", _GF_HOME_VULN),
    ("GET", PREFIX + "/gf-fixed/"): (200, "text/html", _GF_HOME_FIXED),
    ("GET", PREFIX + "/js-vuln/"): (200, "text/html", _JS_HOME_VULN),
    ("GET", PREFIX + "/js-fixed/"): (200, "text/html", _JS_HOME_FIXED),
    ("GET", PREFIX + "/js-vuln/static/app.js"): (
        200, "application/javascript", _JS_APP),
}


def handle(method, path, headers, body):
    """Dynamic routes: query-sensitive metadata, batch differential, metabase."""
    raw = path
    stripped = raw.split("?", 1)[0]
    query = raw.split("?", 1)[1] if "?" in raw else ""
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")
    if not stripped.startswith(PREFIX + "/"):
        return None
    # miniOrange benign SAML metadata presence probe.
    if method == "GET" and "mosaml_metadata" in query and (
            stripped == PREFIX + "/mo-vuln" or stripped == PREFIX + "/mo-fixed"
            or stripped == PREFIX + "/mo-vuln/" or stripped == PREFIX + "/mo-fixed/"):
        return (200, "application/xml", _MO_METADATA)
    # WP core batch route-casing differential.
    if method == "POST" and stripped in (
            PREFIX + "/cb-vuln/wp-json/batch/v1", PREFIX + "/cb-fixed/wp-json/batch/v1"):
        req_path = ""
        try:
            import json as _json
            data = _json.loads(body or "{}")
            reqs = data.get("requests") or []
            if reqs and isinstance(reqs[0], dict):
                req_path = str(reqs[0].get("path", ""))
        except Exception:
            req_path = ""
        upper = req_path != req_path.lower()
        if stripped.endswith("/cb-vuln/wp-json/batch/v1"):
            if upper:
                return (207, "application/json", _CB_BATCH_NO_ROUTE)
            return (207, "application/json", _CB_BATCH_OK)
        return (207, "application/json", _CB_BATCH_OK)
    # Metabase reset_password step-1 differential.
    if method == "POST" and stripped in (
            PREFIX + "/mb-vuln/api/session/reset_password",
            PREFIX + "/mb-fixed/api/session/reset_password"):
        if stripped.startswith(PREFIX + "/mb-vuln") and '"select"' in (body or ""):
            return (400, "application/json", _MB_ECHO)
        return (400, "application/json", _MB_CTRL)
    return None


CASES = [
    ("cve-2026-61979_miniorange.py",
     ["-u", "{BASE}/fx/e/mo-vuln"], ["-u", "{BASE}/fx/e/mo-fixed"]),
    ("cve-2026-63030_wpcore_batch.py",
     ["-u", "{BASE}/fx/e/cb-vuln"], ["-u", "{BASE}/fx/e/cb-fixed"]),
    ("cve-2026-65883_aimy.py",
     ["-u", "{BASE}/fx/e/ay-vuln"], ["-u", "{BASE}/fx/e/ay-fixed"]),
    ("cve-2026-72898_metabase.py",
     ["-u", "{BASE}/fx/e/mb-vuln"], ["-u", "{BASE}/fx/e/mb-fixed"]),
    ("cve-2026-75816_frontendadmin.py",
     ["-u", "{BASE}/fx/e/fa-vuln"], ["-u", "{BASE}/fx/e/fa-fixed"]),
    ("cve-2026-86426_librenms.py",
     ["-u", "{BASE}/fx/e/ln-vuln"], ["-u", "{BASE}/fx/e/ln-fixed"]),
    ("cve-2026-9198_langflow.py",
     ["-u", "{BASE}/fx/e/lf-vuln"], ["-u", "{BASE}/fx/e/lf-fixed"]),
    ("cve-gravityforms_upload.py",
     ["-u", "{BASE}/fx/e/gf-vuln"], ["-u", "{BASE}/fx/e/gf-fixed"]),
    ("js_miner.py",
     ["-u", "{BASE}/fx/e/js-vuln"], ["-u", "{BASE}/fx/e/js-fixed"]),
]

"""Fixture module D for the lab drill harness (PREFIX /fx/d).

Covers: cve-2026-27604_fossbilling, cve-2026-3180_contestgallery,
cve-2026-55040_sharepoint, cve-2026-48908_sppagebuilder,
cve-2026-56291_balbooa, cve-2026-58138_conductor, cve-2026-60137_wpcore_sqli.
OMIT cve-2026-31431_copy_fail_kernel: local-kernel privesc with no HTTP probe surface (manual-drill).
OMIT cve-2026-32202_ntlmv2_lnk_coercion: offline .lnk file generator with no network target (manual-drill).
OMIT cve-2026-39987_marimo: ws_handshake hardcodes absolute GET /terminal/ws (no fixture prefix), so one shared server cannot discriminate vuln vs fixed runs.
OMIT cve-2026-41940_cpanel_auth_bypass: exploit proof requires a Set-Cookie response header and handle() returns a headerless (status, ctype, body) 3-tuple.
OMIT cve-2026-29000_pac4j_jwt_bypass: single-target mode never writes the -o output file (mass mode only), so file-hit cannot discriminate.
OMIT cors_matrix: it writes output rows for every reachable target regardless of verdict, so file-hit cannot discriminate vuln from fixed.
"""

import urllib.parse

PREFIX = "/fx/d"

_JSON = "application/json"

# --- contest-gallery boolean-blind bodies (length differential only) ---
_CG_TRUE = "mail queue: resent 1 message(s) to the subscriber, token refreshed ok"
_CG_FALSE = "ok"

# --- wordpress core boolean-arithmetic bodies (item-count differential) ---
_WP_BASE = '[{"id":1}]'
_WP_TRUE = '[{"id":1},{"id":2}]'
_WP_FALSE = '[]'
_WP_UNION = '[{"id":7},{"id":8},{"id":9}]'


def _s(body):
    if body is None:
        return ""
    if isinstance(body, bytes):
        return body.decode("utf-8", errors="replace")
    return str(body)


ROUTES = {
    # --- fossbilling: POST string_render evaluates {{ 7*7 }} iff vuln ---
    ("POST", PREFIX + "/foss-vuln/api/system/system/string_render"):
        (200, _JSON, '{"result":"49"}'),
    ("POST", PREFIX + "/foss-fixed/api/system/system/string_render"):
        (401, _JSON, '{"error":"Authentication Failed"}'),
    ("GET", PREFIX + "/foss-vuln/"):
        (200, "text/html", "<html><body>FOSSBilling</body></html>"),
    ("GET", PREFIX + "/foss-fixed/"):
        (200, "text/html", "<html><body>FOSSBilling</body></html>"),
    # --- sharepoint: fingerprint via body markers; lists open iff vuln ---
    ("GET", PREFIX + "/sp-vuln/"):
        (200, "text/html",
         "<html><body>SharePoint <script src=\"/_layouts/15/sp.js\"></script>"
         "</body></html>"),
    ("GET", PREFIX + "/sp-fixed/"):
        (200, "text/html",
         "<html><body>SharePoint <script src=\"/_layouts/15/sp.js\"></script>"
         "</body></html>"),
    ("GET", PREFIX + "/sp-vuln/_api/web/lists"):
        (200, _JSON, '{"d":{"results":[{"Title":"Shared Docs"}]}}'),
    ("GET", PREFIX + "/sp-fixed/_api/web/lists"):
        (401, _JSON, '{"error":"unauthorized"}'),
    # --- sp page builder: manifest version gate + open task iff vuln ---
    ("GET", PREFIX + "/spp-vuln/administrator/components/com_sppagebuilder/sppagebuilder.xml"):
        (200, "text/xml",
         '<?xml version="1.0"?><extension><version>6.5.0</version></extension>'),
    ("GET", PREFIX + "/spp-vuln/administrator/components/com_sppagebuilder/com_sppagebuilder.xml"):
        (200, "text/xml",
         '<?xml version="1.0"?><extension><version>6.5.0</version></extension>'),
    ("GET", PREFIX + "/spp-vuln/administrator/components/com_sppagebuilder/manifest.xml"):
        (200, "text/xml",
         '<?xml version="1.0"?><extension><version>6.5.0</version></extension>'),
    ("GET", PREFIX + "/spp-fixed/administrator/components/com_sppagebuilder/sppagebuilder.xml"):
        (200, "text/xml",
         '<?xml version="1.0"?><extension><version>6.6.2</version></extension>'),
    ("GET", PREFIX + "/spp-fixed/administrator/components/com_sppagebuilder/com_sppagebuilder.xml"):
        (200, "text/xml",
         '<?xml version="1.0"?><extension><version>6.6.2</version></extension>'),
    ("GET", PREFIX + "/spp-fixed/administrator/components/com_sppagebuilder/manifest.xml"):
        (200, "text/xml",
         '<?xml version="1.0"?><extension><version>6.6.2</version></extension>'),
    ("GET", PREFIX + "/spp-vuln/index.php"):
        (200, _JSON, '{"task":"asset.uploadCustomIcon","status":"ready"}'),
    ("GET", PREFIX + "/spp-fixed/index.php"):
        (403, _JSON, '{"error":"forbidden"}'),
    # --- balbooa: manifest version gate + .txt probe accepted iff vuln ---
    ("GET", PREFIX + "/balb-vuln/administrator/components/com_baforms/baforms.xml"):
        (200, "text/xml",
         '<?xml version="1.0"?><extension><version>2.3.9</version></extension>'),
    ("GET", PREFIX + "/balb-vuln/administrator/components/com_baforms/com_baforms.xml"):
        (200, "text/xml",
         '<?xml version="1.0"?><extension><version>2.3.9</version></extension>'),
    ("GET", PREFIX + "/balb-vuln/administrator/components/com_baforms/manifest.xml"):
        (200, "text/xml",
         '<?xml version="1.0"?><extension><version>2.3.9</version></extension>'),
    ("GET", PREFIX + "/balb-fixed/administrator/components/com_baforms/baforms.xml"):
        (200, "text/xml",
         '<?xml version="1.0"?><extension><version>2.4.1</version></extension>'),
    ("GET", PREFIX + "/balb-fixed/administrator/components/com_baforms/com_baforms.xml"):
        (200, "text/xml",
         '<?xml version="1.0"?><extension><version>2.4.1</version></extension>'),
    ("GET", PREFIX + "/balb-fixed/administrator/components/com_baforms/manifest.xml"):
        (200, "text/xml",
         '<?xml version="1.0"?><extension><version>2.4.1</version></extension>'),
    ("POST", PREFIX + "/balb-vuln/index.php"):
        (200, _JSON,
         '{"success":true,"message":"attachment uploaded"}'),
    ("POST", PREFIX + "/balb-fixed/index.php"):
        (403, _JSON, '{"error":"forbidden"}'),
    # --- conductor: metadata open (vuln) vs 401 (fixed); version in range ---
    ("GET", PREFIX + "/cond-vuln/api/metadata/workflow"):
        (200, _JSON, '[]'),
    ("GET", PREFIX + "/cond-vuln/api/version"):
        (200, _JSON, '{"name":"conductor","version":"3.28.0"}'),
    ("GET", PREFIX + "/cond-fixed/api/metadata/workflow"):
        (401, _JSON, '{"error":"unauthorized"}'),
    # --- wordpress core: generator version in range (vuln) vs out (fixed) ---
    ("GET", PREFIX + "/wp-vuln/wp-json/"):
        (200, _JSON,
         '{"generator":"WordPress 6.8.3","namespaces":["wp/v2","oembed/1.0"]}'),
    ("GET", PREFIX + "/wp-fixed/wp-json/"):
        (200, _JSON,
         '{"generator":"WordPress 6.8.6","namespaces":["wp/v2","oembed/1.0"]}'),
}


def handle(method, path, headers, body):
    """Dynamic routes: body-sensitive (contest-gallery), random-ID (conductor
    workflow probe), query-sensitive (wpcore posts differential)."""
    base = path.split("?", 1)[0]
    if not base.startswith(PREFIX + "/"):
        return None
    text = _s(body)

    # --- contest-gallery: TRUE vs FALSE mail bodies differ iff vuln ---
    for app, vuln in (("cg-vuln", True), ("cg-fixed", False)):
        if base == PREFIX + "/" + app + "/wp-admin/admin-ajax.php":
            if method != "POST":
                return (200, "text/plain", "ok")
            if not vuln:
                return (200, "text/plain", "ok")
            dec = urllib.parse.unquote_plus(text)
            if "post_cg1l_resend_unconfirmed_mail_frontend" in dec:
                if "1=2" in dec:
                    return (200, "text/plain", _CG_FALSE)
                return (200, "text/plain", _CG_TRUE)
            return (200, "text/plain", "ok")

    # --- conductor: benign nonexistent-workflow probe, any non-401/403
    # status with exposed metadata + in-range version reads as VULNERABLE ---
    if base.startswith(PREFIX + "/cond-vuln/api/workflow/nonexistent-"):
        return (404, _JSON, '{"message":"workflow not found"}')

    # --- wpcore: query-sensitive boolean-arithmetic differential; the
    # harness passes the raw path including the query string ---
    for app, vuln in (("wp-vuln", True), ("wp-fixed", False)):
        if base == PREFIX + "/" + app + "/wp-json/wp/v2/posts":
            if not vuln:
                return (200, _JSON, _WP_BASE)
            q = path if "?" in path else ""
            if "UNION" in q.upper():
                return (200, _JSON, _WP_UNION)
            if "1%3D1" in q or "1=1" in q:
                return (200, _JSON, _WP_TRUE)
            if "1%3D2" in q or "1=2" in q:
                return (200, _JSON, _WP_FALSE)
            return (200, _JSON, _WP_BASE)

    return None


CASES = [
    ("cve-2026-27604_fossbilling.py",
     ["-u", "{BASE}/fx/d/foss-vuln"],
     ["-u", "{BASE}/fx/d/foss-fixed"]),
    ("cve-2026-3180_contestgallery.py",
     ["-u", "{BASE}/fx/d/cg-vuln"],
     ["-u", "{BASE}/fx/d/cg-fixed"]),
    ("cve-2026-55040_sharepoint.py",
     ["-u", "{BASE}/fx/d/sp-vuln"],
     ["-u", "{BASE}/fx/d/sp-fixed"]),
    ("cve-2026-48908_sppagebuilder.py",
     ["-u", "{BASE}/fx/d/spp-vuln"],
     ["-u", "{BASE}/fx/d/spp-fixed"]),
    ("cve-2026-56291_balbooa.py",
     ["-u", "{BASE}/fx/d/balb-vuln"],
     ["-u", "{BASE}/fx/d/balb-fixed"]),
    ("cve-2026-58138_conductor.py",
     ["-u", "{BASE}/fx/d/cond-vuln"],
     ["-u", "{BASE}/fx/d/cond-fixed"]),
    ("cve-2026-60137_wpcore_sqli.py",
     ["-u", "{BASE}/fx/d/wp-vuln"],
     ["-u", "{BASE}/fx/d/wp-fixed"]),
]

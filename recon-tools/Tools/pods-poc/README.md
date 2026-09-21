- Exploit Author: Abdualhadi Khalifa (https://x.com/absholi7ly)
- Version: Pods Custom Content Types and Fields <= 3.3.9
- Tested on: WordPress + Pods 3.3.8 (Windows / Laragon / Apache)
- CVE: CVE-2026-19598
- Credits: Vulnerability discovered by Wordfence Threat Intelligence team
- Category: WebApps

A critical vulnerability in the Pods Custom Content Types and Fields WordPress plugin. It allows unauthenticated attackers to change any user's password and take full control of the site.

The root cause is that the `pods_error()` function does not terminate the request when permission checks fail, allowing administrative actions to be executed via `admin-ajax.php`.

### Basic usage (target user ID 1):
```bash
python pods.py http://localhost/wp
```

### Target a specific user (e.g., ID 5):
```bash
python exploit.py https://example.com --id 5
```
# Poc
[![Poc](https://img.youtube.com/vi/pZMdEOIFjhU/maxresdefault.jpg)](https://www.youtube.com/watch?v=pZMdEOIFjhU)

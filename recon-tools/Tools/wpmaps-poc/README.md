# CVE-2026-8732 - WordPress WP Google Map Pro Mass Scanner & Auto Admin Creator

[![Python 2.7](https://img.shields.io/badge/Python-2.7-blue.svg)](https://www.python.org/downloads/release/python-2718/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 📌 Description

This tool exploits **CVE-2026-8732**, a vulnerability in the **WP Google Map Pro** plugin for WordPress. The vulnerability allows an unauthenticated attacker to obtain a valid `wpmp_token` via an AJAX endpoint (`admin-ajax.php?action=wpgmp_temp_access_ajax`). Using this token, an attacker can access the WordPress admin panel and create a new administrator user.

The tool performs **mass scanning** from a list of domains, extracts the nonce and token, and automatically creates a hidden administrator account on vulnerable sites. Results are saved in real-time with full token details.

> **⚠️ DISCLAIMER:** This tool is for **educational and authorized security testing only**. Use only on systems you own or have explicit permission to test. The author is not responsible for any misuse.
> 
> More Disclaimer You Can see the disclaimer on the cover of Jenderal92. You can check it [HERE !!!](https://github.com/Jenderal92/)
> 

## 🔍 CVE Details

| Field | Value |
|-------|-------|
| **CVE ID** | CVE-2026-8732 (hypothetical for this plugin) |
| **Affected Plugin** | WP Google Map Pro (versions <= 1.5.0) |
| **Vulnerability Type** | Broken Access Control / Privilege Escalation |
| **Attack Vector** | Unauthenticated, Remote |
| **Impact** | Full site takeover via admin account creation |

## ✨ Features

- Multi-threaded scanning (adjustable thread count)
- Automatic nonce extraction from target homepage
- Token extraction from JSON response
- Real-time saving of vulnerable domains + full token
- Automatic administrator account creation (language‑agnostic)
- Saves created admin credentials to `admin_created.txt`
- Supports both `http://` and `https://`
- Configurable admin username, password, email

## 📦 Requirements

- Python 2.7
- `requests` library

Install the required library:

```bash
pip install requests
```

🚀 Installation

```bash
git clone https://github.com/Jenderal92/CVE-2026-8732.git
cd CVE-2026-8732
```

🎯 Usage

Prepare a target list file (one domain per line):

```text
example.com
https://target-website.com
http://vulnerable-site.org
```

Run the scanner:

```bash
python2 exploit.py targets.txt
```

Output Files

File Content
res.txt Vulnerable domains with full token and redirect URL (if any)
admin_created.txt Successfully created admin credentials (domain, username, password, email)

Example Output

```text
[*] Checking: https://example.com
[VULNERABLE] https://example.com -> Token found
[*] https://example.com -> Accessing redirect URL...
[+] https://example.com -> Admin created: securityaudit_1734567890 / StrongP@ssw0rd123!
```

⚙️ Configuration

Edit the following variables inside the script:

```python
TIMEOUT = 10               # Request timeout in seconds
JUMLAH_THREAD = 10         # Number of concurrent threads
OUTPUT_FILE = "res.txt"    # File for vulnerable results
ADMIN_FILE = "admin_created.txt"

BASE_USERNAME = "securityaudit"
NEW_PASSWORD = "StrongP@ssw0rd123!"
NEW_EMAIL = "audit@example.com"
```

🧠 How It Works

1. Nonce Extraction
      Sends a GET request to the target, extracts wpgmp_local or fc-call-nonce from HTML.
2. Token Exploitation
      Sends a POST to /wp-admin/admin-ajax.php with action=wpgmp_temp_access_ajax and the obtained nonce.
3. Admin Session
      Follows the redirect URL (if provided) to gain authenticated session cookies.
4. Admin Creation
      Accesses /wp-admin/user-new.php, extracts _wpnonce_create-user, and submits a POST to create a new administrator user.
5. Verification
      Checks for HTTP 302 redirect to users.php or searches for the new username in the users list to confirm success.

🛡️ Mitigation

· Update WP Google Map Pro to the latest patched version.
· Disable the AJAX action wpgmp_temp_access_ajax via custom code or firewall.
· Use a Web Application Firewall (WAF) to block malicious requests to admin-ajax.php.

⭐ Disclaimer

This software is provided "AS IS" without warranty of any kind. The entire risk as to the quality and performance of the software is with you. Use responsibly and only on systems you are authorized to test.

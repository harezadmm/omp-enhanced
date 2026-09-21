# CVE-2026-3844
PoC exploit for CVE-2026-3844, a critical unauthenticated file upload vulnerability in the WordPress Breeze plugin leading to RCE.
<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=700&size=26&pause=1000&color=FF0000&center=true&vCenter=true&width=800&lines=CVE-2026-3844+%7C+Breeze+Cache+WordPress+Plugin;Unauthenticated+Arbitrary+File+Upload+%E2%86%92+RCE;CVSS+9.8+CRITICAL+%7C+CWE-434;PoC+Exploit+by+Tausif+Zaman" alt="CVE-2026-3844 Typing SVG" />

<br/>

[![CVE ID](https://img.shields.io/badge/CVE-2026--3844-red?style=for-the-badge&logo=hackthebox&logoColor=white)](https://nvd.nist.gov/vuln/detail/CVE-2026-3844)
[![CVSS Score](https://img.shields.io/badge/CVSS-9.8%20Critical-critical?style=for-the-badge&logo=securityscorecard&logoColor=white)](https://nvd.nist.gov/vuln/detail/CVE-2026-3844)
[![CWE](https://img.shields.io/badge/CWE-434-orange?style=for-the-badge)](https://cwe.mitre.org/data/definitions/434.html)
[![Python](https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![WordPress](https://img.shields.io/badge/WordPress-Plugin-21759B?style=for-the-badge&logo=wordpress&logoColor=white)](https://wordpress.org/plugins/breeze/)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey?style=for-the-badge&logo=linux&logoColor=white)](https://github.com/tausifzaman/CVE-2026-3844)
[![PoC](https://img.shields.io/badge/PoC-Available-brightgreen?style=for-the-badge&logo=github)](https://github.com/tausifzaman/CVE-2026-3844/blob/main/CVE-2026-3844.py)
[![Author](https://img.shields.io/badge/Author-Tausif%20Zaman-orange?style=for-the-badge&logo=github)](https://tausifzaman.online)

<br/>


</div>

---

## 📌 Overview
<center>

**CVE-2026-3844** is a **CRITICAL** unauthenticated arbitrary file upload vulnerability in the **Breeze Cache WordPress plugin** (by Cloudways), affecting **all versions up to and including 2.4.4**.

This repository provides a **Proof of Concept (PoC) exploit** (`CVE-2026-3844.py`) for authorized security research, penetration testing, and responsible disclosure.

</center>

---

## One Line Code
```
git clone https://github.com/tausifzaman/CVE-2026-3844.git && cd CVE-2026-3844 && python3
```

---


## 📊 Vulnerability Summary

| Field                  | Details                                                                 |
|------------------------|-------------------------------------------------------------------------|
| **CVE ID**             | CVE-2026-3844                                                           |
| **Plugin**             | Breeze Cache (by Cloudways)                                             |
| **Affected Versions**  | All versions ≤ 2.4.4                                                    |
| **Patched Version**    | Breeze 2.4.5+                                                           |
| **Vulnerability Type** | CWE-434 — Unrestricted Upload of File with Dangerous Type               |
| **CVSS v3.1 Score**    | **9.8 (CRITICAL)**                                                      |
| **CVSS v2.0 Score**    | **10.0 (CRITICAL)**                                                     |
| **CVSS Vector**        | `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`                        |
| **Attack Vector**      | Network (Remote)                                                        |
| **Auth Required**      | ❌ None — Unauthenticated                                                |
| **Condition**          | "Host Files Locally – Gravatars" must be enabled (disabled by default) |
| **Impact**             | Confidentiality: HIGH · Integrity: HIGH · Availability: HIGH            |
| **Published**          | 2026-04-23                                                              |
| **Source**             | Wordfence / NVD / MITRE                                                 |
| **PoC**         | [Tausif Zaman](https://tausifzaman.online)                              |

---

## 🔍 Vulnerability Details

### Root Cause

The **Breeze Cache** plugin for WordPress fetches remote Gravatar images and stores them locally when the **"Host Files Locally – Gravatars"** feature is enabled. The vulnerable function `fetch_gravatar_from_remote` in `class-breeze-cache-cronjobs.php` (lines 89–119) performs **no file type or extension validation** on the fetched remote content.

```
class-breeze-cache-cronjobs.php
  └── fetch_gravatar_from_remote()   ← ❌ No file type validation
        └── Saves remote content directly to disk
              └── Attacker controls → uploads .php webshell → RCE
```

### Attack Flow

```
Attacker (Unauthenticated)
    │
    ▼
Craft malicious HTTP request with PHP webshell URL as Gravatar
    │
    ▼
Plugin fetches & saves the .php file without validation
    │
    ▼
Webshell stored on server (e.g., /wp-content/breeze-cache/evil.php)
    │
    ▼
Attacker accesses webshell → Full RCE achieved
```

### Impact

If successfully exploited, an attacker can:

- 🔴 Execute arbitrary operating system commands (RCE)
- 🔴 Upload persistent backdoors / webshells
- 🔴 Create rogue WordPress administrator accounts
- 🔴 Exfiltrate databases, credentials, and sensitive files
- 🔴 Deface the website or delete all content
- 🔴 Use the server to pivot to other systems on the same network
- 🔴 Recruit the server into a botnet

---

## ⚙️ Requirements

- Python 3.6+
- `requests` library
- Target site running **Breeze Cache ≤ 2.4.4** with **"Host Files Locally – Gravatars" enabled**

---

## 🚀 Installation & Setup

### 🐧 Linux / Termux (Android)

```bash
# Clone the repository
git clone https://github.com/tausifzaman/CVE-2026-3844.git && cd CVE-2026-3844 && python3 CVE-2026-3844.py

# Navigate into the directory
cd CVE-2026-3844

# Install dependencies
pip install -r requirements.txt

# Run the exploit
python3 CVE-2026-3844.py
```

### 🪟 Windows (CMD / PowerShell)

```cmd
git clone https://github.com/tausifzaman/CVE-2026-3844.git
cd CVE-2026-3844
pip install -r requirements.txt
python CVE-2026-3844.py
```

### 🍎 macOS

```bash
git clone https://github.com/tausifzaman/CVE-2026-3844.git
cd CVE-2026-3844
pip3 install -r requirements.txt
python3 CVE-2026-3844.py
```

### 🤖 Termux (One-Liner)

```bash
pkg install python git -y && git clone https://github.com/tausifzaman/CVE-2026-3844.git && cd CVE-2026-3844 && pip install -r requirements.txt && python3 CVE-2026-3844.py
```

### ☁️ Google Cloud Shell (No Setup Needed)

[![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://console.cloud.google.com/cloudshell/editor?project=&pli=1&shellonly=true)

```bash
git clone https://github.com/tausifzaman/CVE-2026-3844.git && cd CVE-2026-3844 && pip install -r requirements.txt && python3 CVE-2026-3844.py
```

---

## 💻 Usage

```bash
python3 CVE-2026-3844.py
```

### Options

```
usage: CVE-2026-3844.py [-h] -u URL [-t TIMEOUT] [-o OUTPUT] [-v]

CVE-2026-3844 — Breeze Cache WordPress Plugin Arbitrary File Upload PoC

optional arguments:
  -h, --help              Show this help message and exit
  -u URL, --url URL       Target URL (e.g. https://target.com)
  -t TIMEOUT              Request timeout in seconds (default: 10)
  -o OUTPUT               Save webshell path to output file
  -v, --verbose           Enable verbose/debug output
```

### Examples

```bash
# Basic usage
python3 CVE-2026-3844.py -u https://vulnerable-site.com

# Verbose mode
python3 CVE-2026-3844.py -u https://vulnerable-site.com -v

# Custom timeout
python3 CVE-2026-3844.py -u https://vulnerable-site.com -t 20 -v
```

---

## 🖥️ PoC Demo Output

```
╔══════════════════════════════════════════════════════╗
║          CVE-2026-3844 | Breeze Cache WP RCE        ║
║          Researcher: tausifzaman.online              ║
╚══════════════════════════════════════════════════════╝

[*] Target     : https://vulnerable-site.com
[*] CVE        : CVE-2026-3844
[*] Plugin     : Breeze Cache ≤ 2.4.4
[*] Type       : Unauthenticated Arbitrary File Upload → RCE
[*] Checking target...

[+] Breeze Cache plugin detected!
[+] "Host Files Locally – Gravatars" is ENABLED
[*] Uploading PHP webshell via fetch_gravatar_from_remote...
[+] File uploaded successfully!
[+] Webshell path: /wp-content/breeze-cache/avatar_a1b2c3.php
[*] Verifying RCE...
[+] RCE CONFIRMED!

[+] Command output (id):
    uid=33(www-data) gid=33(www-data) groups=33(www-data)

[+] Full server compromise achieved.
[*] Cleanup: Remove /wp-content/breeze-cache/avatar_a1b2c3.php after testing.
```

---

## 🔒 Mitigation & Remediation

### ✅ Immediate Action

> **Update Breeze Cache to version 2.4.5 or later** — this is the only complete fix.

```bash
# WordPress CLI — update Breeze plugin immediately
wp plugin update breeze
```

### 🛡️ Temporary Mitigations (If You Cannot Update Immediately)

1. **Disable** the "Host Files Locally – Gravatars" option in Breeze Cache settings
2. **Block the vulnerable endpoint** via WAF rule or `.htaccess`
3. **Deny PHP execution** in the uploads and cache directories:

```apache
# Add to /wp-content/uploads/.htaccess and /wp-content/cache/.htaccess
<FilesMatch "\.php$">
    deny from all
</FilesMatch>
```

4. **Scan for newly created/modified suspicious files:**

```bash
# Find recently modified PHP files in wp-content (possible webshells)
find /var/www/html/wp-content -name "*.php" -newer /var/www/html/wp-config.php -ls

# Search for common webshell indicators
grep -r "eval(base64_decode" /var/www/html/wp-content/
grep -r "system\|exec\|passthru\|shell_exec" /var/www/html/wp-content/cache/
```

5. **Block suspicious POST requests** targeting the Gravatar fetch functionality via your WAF
6. **Monitor access logs** for requests to `/wp-content/breeze-cache/*.php`

```bash
# Monitor Apache/Nginx access logs for webshell hits
grep "breeze-cache.*\.php" /var/log/apache2/access.log
grep "breeze-cache.*\.php" /var/log/nginx/access.log
```

### 🔍 Check If Already Compromised

```bash
# Check for unexpected PHP files in Breeze cache directory
find /var/www/html/wp-content/breeze-cache/ -name "*.php"

# Check for recently created files (last 7 days)
find /var/www/html/wp-content/ -name "*.php" -mtime -7

# Look for admin accounts created recently (run in wp-mysql)
SELECT user_login, user_registered FROM wp_users ORDER BY user_registered DESC LIMIT 10;
```

---

## 📚 References

| Source | Link |
|--------|------|
| 🔗 NVD (NIST) | [nvd.nist.gov/vuln/detail/CVE-2026-3844](https://nvd.nist.gov/vuln/detail/CVE-2026-3844) |
| 🔗 MITRE CVE | [cve.mitre.org – CVE-2026-3844](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2026-3844) |
| 🔗 Wordfence Advisory | [wordfence.com – Threat Intel](https://www.wordfence.com/threat-intel/vulnerabilities/id/e342b1c0-6e7f-4e2c-8a52-018df12c12a0?source=cve) |
| 🔗 WordPress Plugin Changelog | [plugins.trac.wordpress.org/changeset/3511463/breeze](https://plugins.trac.wordpress.org/changeset/3511463/breeze) |
| 🔗 Vulnerable Code (L89) | [class-breeze-cache-cronjobs.php#L89](https://plugins.trac.wordpress.org/browser/breeze/tags/2.4.1/inc/class-breeze-cache-cronjobs.php#L89) |
| 🔗 Vulnerable Code (L119) | [class-breeze-cache-cronjobs.php#L119](https://plugins.trac.wordpress.org/browser/breeze/tags/2.4.1/inc/class-breeze-cache-cronjobs.php#L119) |
| 🔗 GitHub Advisory | [GHSA-c529-q7mw-hq6j](https://github.com/advisories/GHSA-c529-q7mw-hq6j) |
| 🔗 PoC Repository | [github.com/tausifzaman/CVE-2026-3844](https://github.com/tausifzaman/CVE-2026-3844) |

---

## 👤 Author

<div align="center">

**Tausif Zaman**

🌐 [tausifzaman.online](https://tausifzaman.online) &nbsp;·&nbsp; 🐙 [GitHub @tausifzaman](https://github.com/tausifzaman)

*Security Researcher · Bug Bounty Hunter · Tool Developer*

Android · Python · PHP · Web Security · Penetration Testing

</div>

---

## ⚠️ Legal Disclaimer

This repository and the exploit code within are provided **strictly for educational purposes and authorized security research only**.

- ✅ You may use this tool on systems **you own** or have **explicit written permission** to test
- ❌ Unauthorized use against third-party systems is **illegal** under the Computer Fraud and Abuse Act (CFAA), the Computer Misuse Act, and equivalent laws worldwide
- The author accepts **zero liability** for misuse, damage, or illegal activity resulting from this tool

**Hack ethically. Report responsibly. Stay legal. 🛡️**

---

<div align="center">

⭐ **If this helped your research, star the repo!** ⭐

[![Star](https://img.shields.io/github/stars/tausifzaman/CVE-2026-3844?style=social)](https://github.com/tausifzaman/CVE-2026-3844)
&nbsp;
[![Follow](https://img.shields.io/github/followers/tausifzaman?style=social)](https://github.com/tausifzaman)
&nbsp;
[![Website](https://img.shields.io/badge/Visit-tausifzaman.online-blue?style=flat-square)](https://tausifzaman.online)

</div>

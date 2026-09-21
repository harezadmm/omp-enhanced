"""Search the bulk exploit index (Tools/exploit_index.jsonl).

Usage:
  python3 Tools/index_search.py --cve CVE-2024-3400
  python3 Tools/index_search.py -q wordpress --type webapps --limit 20
  python3 Tools/index_search.py -q rce --severity critical --has-scanner
  python3 Tools/index_search.py -q langflow --json -o hits.jsonl

Filters combine with AND. Text query matches id/title/tags/CVE (case-insensitive).
Stdlib only.
"""
import argparse
import json
import os
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(TOOLS, "exploit_index.jsonl")


def load():
    rows = []
    with open(INDEX, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main():
    ap = argparse.ArgumentParser(description="Search bulk exploit index")
    ap.add_argument("-q", "--query", default="", help="keyword (id/title/tags/CVE)")
    ap.add_argument("--cve", default="", help="CVE id filter")
    ap.add_argument("--src", default="", choices=["", "nuclei", "edb"],
                    help="source filter")
    ap.add_argument("--type", default="", dest="etype",
                    help="EDB type filter (webapps/remote/local/dos)")
    ap.add_argument("--severity", default="", help="severity filter")
    ap.add_argument("--access", default="", help="access filter")
    ap.add_argument("--has-scanner", action="store_true",
                    help="only rows with a local Tools scanner")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--json", action="store_true", help="JSONL output")
    ap.add_argument("-o", "--output", default="")
    args = ap.parse_args()

    q = args.query.lower()
    cve = args.cve.upper()
    rows = load()
    hits = []
    for r in rows:
        if cve and cve not in r.get("cve", []):
            continue
        if args.src and r.get("src") != args.src:
            continue
        if args.etype and (r.get("extra") or {}).get("type") != args.etype:
            continue
        if args.severity and (r.get("severity") or "") != args.severity.lower():
            continue
        if args.access and (r.get("access") or "") != args.access:
            continue
        if args.has_scanner and not r.get("has_scanner"):
            continue
        if q:
            hay = " ".join([r.get("id", ""), r.get("title", ""),
                            " ".join(r.get("cve", [])),
                            (r.get("extra") or {}).get("tags", "")]).lower()
            if q not in hay:
                continue
        hits.append(r)
        if len(hits) >= args.limit:
            break

    if args.json:
        text = "\n".join(json.dumps(h, ensure_ascii=False) for h in hits)
    else:
        lines = []
        for h in hits:
            lines.append("%s | %s | %s | %s | %s%s | %s" % (
                h.get("id"), ",".join(h.get("cve", [])[:2]) or "-",
                (h.get("severity") or "-"), h.get("access"),
                "[SCANNER] " if h.get("has_scanner") else "",
                h.get("title", "")[:80], h.get("poc_url", "")))
        text = "\n".join(lines)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text + ("\n" if text else ""))
        print("wrote %d hits -> %s" % (len(hits), args.output))
    else:
        print(text if text else "no hits")
        print("[%d hits]" % len(hits), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

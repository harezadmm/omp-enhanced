"""Bulk exploit indexer: nuclei-templates + Exploit-DB metadata -> JSONL index.

Sources (harvested separately, see Usage):
  /tmp/bulk/nt                 nuclei-templates sparse checkout (http/cves, http/exposures, http/misconfiguration)
  /tmp/bulk/edb/files_exploits.csv + files_shellcodes.csv

Usage:
  python3 Tools/build_index.py --nt /tmp/bulk/nt --edb /tmp/bulk/edb -o Tools/exploit_index.jsonl

Row schema (one JSON per line):
  {src, id, cve[], title, severity, access, poc_url, check_hint, has_scanner,
   extra{platform, type, verified, date, template}}

- access: nuclei -> from metadata / EDB -> type-based hint (webapps/remote =
  network; local = local; dos = dos). Both authorized AND unauthorized are
  indexed; access is a tag, not a filter.
- has_scanner: true when the CVE appears in a Tools/cve-*.py filename or the
  EDB-ID matches a known folder PoC (breeze/cf7/ninjaforms/pix/wpmaps/wpvivid/
  elementor/pods). Rebuilt from disk every run — no hardcoded list.
- check_hint: first endpoint-ish string found (nuclei path: / template word,
  EDB title keywords). Best-effort triage seed, not a verified probe.
Stdlib only.
"""
import argparse
import csv
import json
import os
import re
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))

CVE_RE = re.compile(r"CVE-\d{4}-\d{4,7}", re.IGNORECASE)
EDB_RE = re.compile(r"EDB-ID:?(\d+)", re.IGNORECASE)


def arsenal_cves():
    found = set()
    for fn in os.listdir(TOOLS):
        for m in CVE_RE.findall(fn):
            found.add(m.upper())
    return found


def parse_nuclei(path, rel):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            txt = f.read(6000)
    except OSError:
        return None
    m = re.search(r"^id:\s*([^\s#]+)", txt, re.MULTILINE)
    if not m:
        return None
    tid = m.group(1).strip()
    name = re.search(r"^\s*name:\s*(.+)$", txt, re.MULTILINE)
    sev = re.search(r"^\s*severity:\s*([a-z]+)", txt, re.MULTILINE | re.IGNORECASE)
    desc = re.search(r"^\s*description:\s*(.+)$", txt, re.MULTILINE)
    cves = sorted(set(c.upper() for c in CVE_RE.findall(txt[:4000])))
    # first endpoint-ish hint: path: lines, then request method+path
    hint = ""
    pm = re.search(r"^\s*path:\s*\[?([^\]\n]+)", txt, re.MULTILINE)
    if pm:
        hint = pm.group(1).strip().strip("'\"")[:120]
    sev_v = sev.group(1).lower() if sev else ""
    access = "auth" if re.search(r"auth|login|credential|token",
                                 (desc.group(1) if desc else "") + tid,
                                 re.IGNORECASE) else "network"
    return {
        "src": "nuclei",
        "id": tid,
        "cve": cves,
        "title": (name.group(1).strip()[:200] if name else tid),
        "severity": sev_v or None,
        "access": access,
        "poc_url": "https://raw.githubusercontent.com/projectdiscovery/"
                   "nuclei-templates/main/" + rel,
        "check_hint": hint or None,
        "has_scanner": False,  # filled in pass 2
        "extra": {"template": rel},
    }


def iter_nuclei(nt_root):
    n = 0
    for base in ("http/cves", "http/exposures", "http/misconfiguration"):
        root = os.path.join(nt_root, *base.split("/"))
        for dirpath, _, files in os.walk(root):
            for fn in files:
                if not fn.endswith((".yaml", ".yml")):
                    continue
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, nt_root)
                row = parse_nuclei(full, rel)
                n += 1
                if row:
                    yield row
    sys.stderr.write("nuclei templates scanned: %d\n" % n)


EDB_TYPE_ACCESS = {
    "remote": "network", "webapps": "network", "dos": "network",
    "local": "local", "shellcode": "local",
}


def iter_edb(csv_path, kind):
    with open(csv_path, encoding="utf-8", errors="replace", newline="") as f:
        rdr = csv.DictReader(f)
        n = 0
        for r in rdr:
            n += 1
            try:
                eid = str(int(r.get("id") or 0))
            except (ValueError, TypeError):
                continue
            if eid == "0":
                continue
            codes = r.get("codes") or ""
            cves = sorted(set(c.upper() for c in CVE_RE.findall(codes)))
            title = (r.get("description") or "")[:200]
            typ = (r.get("type") or "").strip()
            plat = (r.get("platform") or "").strip()
            ver = (r.get("verified") or "").strip()
            yield {
                "src": "edb",
                "id": "EDB-" + eid,
                "cve": cves,
                "title": title,
                "severity": None,
                "access": EDB_TYPE_ACCESS.get(typ, typ or "unknown"),
                "poc_url": "https://www.exploit-db.com/exploits/" + eid,
                "check_hint": None,
                "has_scanner": False,
                "extra": {
                    "platform": plat, "type": typ, "verified": ver,
                    "date": r.get("date_published") or "",
                    "file": r.get("file") or "",
                    "tags": r.get("tags") or "",
                },
            }
        sys.stderr.write("edb %s rows scanned: %d\n" % (kind, n))


def main():
    ap = argparse.ArgumentParser(description="Bulk exploit indexer -> JSONL")
    ap.add_argument("--nt", required=True, help="nuclei-templates checkout root")
    ap.add_argument("--edb", required=True, help="exploitdb checkout root")
    ap.add_argument("-o", "--output", default=os.path.join(TOOLS, "exploit_index.jsonl"))
    args = ap.parse_args()

    covered = arsenal_cves()
    sys.stderr.write("arsenal CVEs: %d\n" % len(covered))

    count = 0
    with open(args.output, "w", encoding="utf-8") as out:
        for row in iter_nuclei(args.nt):
            if row["cve"] and covered.intersection(row["cve"]):
                row["has_scanner"] = True
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
        for csv_name, kind in (("files_exploits.csv", "exploits"),
                               ("files_shellcodes.csv", "shellcodes")):
            p = os.path.join(args.edb, csv_name)
            if not os.path.exists(p):
                sys.stderr.write("missing %s, skipped\n" % p)
                continue
            for row in iter_edb(p, kind):
                if row["cve"] and covered.intersection(row["cve"]):
                    row["has_scanner"] = True
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                count += 1
    size = os.path.getsize(args.output)
    print("wrote %d rows -> %s (%d bytes)" % (count, args.output, size))
    return 0


if __name__ == "__main__":
    sys.exit(main())

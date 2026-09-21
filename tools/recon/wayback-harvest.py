#!/usr/bin/env python3
"""Wayback Machine endpoint harvester.
Usage: python3 wayback-harvest.py target.com [--filter js|json|php|xml|txt]"""
import sys, json, urllib.request, re
TARGET = sys.argv[1] if len(sys.argv) > 1 else sys.exit("Usage: wayback-harvest.py target.com [--filter ext1,ext2]")
FILTER = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else None
try:
    url = f"https://web.archive.org/cdx/search/cdx?url=*.{TARGET}/*&output=json&fl=original,timestamp&collapse=urlkey&filter=statuscode:200&limit=50000"
    resp = urllib.request.urlopen(url, timeout=60)
    data = json.loads(resp.read())
except Exception as e:
    sys.exit(f"ERROR: {e}")
seen = set()
for entry in data[1:]:
    url = entry[0]
    if FILTER:
        ext_match = re.search(r'\.(\w+)(?:[?#]|$)', url)
        if not ext_match or ext_match.group(1).lower() not in FILTER:
            continue
    if url not in seen:
        seen.add(url)
        print(url)

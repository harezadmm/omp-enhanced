"""Deterministic in-memory dataset and blind oracle for the blind-SQLi lab.

The single unescaped quote in the sku filter is the intended vulnerability.
The flag is a synthetic committed lab constant; never copy this construction
into production code.
"""
import sqlite3
import threading

FLAG = "T3MP3ST{bl1nd_or4cl3_d4t4}"
MAX_SKU = 200

_CONN = sqlite3.connect(":memory:", check_same_thread=False)
_LOCK = threading.Lock()
_CONN.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, sku TEXT, qty INTEGER)")
_CONN.executemany(
    "INSERT INTO items VALUES (?, ?, ?)",
    [(i, f"SKU-{i:04d}", (i * 7) % 19 + 1) for i in range(1, 21)],
)
_CONN.execute("CREATE TABLE secrets (id INTEGER PRIMARY KEY, name TEXT, value TEXT)")
_CONN.execute("INSERT INTO secrets VALUES (1, 'flag', ?)", (FLAG,))
_CONN.commit()


def oracle(sku: object) -> tuple[bool, int]:
    """Run the intentionally vulnerable sku filter.

    Returns (found, count); the row count is the only observable result and
    no column value is ever echoed back to the caller.
    """
    payload = str(sku)[:MAX_SKU]
    query = f"SELECT id, sku, qty FROM items WHERE sku = '{payload}'"
    with _LOCK:
        try:
            rows = _CONN.execute(query).fetchall()
        except sqlite3.Error:
            return False, 0
    return len(rows) > 0, len(rows)

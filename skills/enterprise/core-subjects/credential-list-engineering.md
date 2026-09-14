# CREDENTIAL LIST ENGINEERING

**Domain:** EXPERTISE — FULL OPERATIONAL ARSENAL

## Overview
> Level: GOD TIER — multi-format parsing, Bloom dedup, entropy scoring
- Parsing: colon/semicolon/pipe-delimited, ULP conversion, custom delimiter auto-detect
- Scoring: domain extraction, email-domain correlation, entropy bits, strength bucket
- Classification: password vs hash vs token vs API key auto-detect

## Full Doctrine

> Level: GOD TIER — multi-format parsing, Bloom dedup, entropy scoring

- Parsing: colon/semicolon/pipe-delimited, ULP conversion, custom delimiter auto-detect
- Scoring: domain extraction, email-domain correlation, entropy bits, strength bucket
- Classification: password vs hash vs token vs API key auto-detect
- Dedup: set-based exact + Bloom filter (billion-entry)
- Junk filter: regex junk line, script-injection, comment stripping
- Resume: byte-offset checkpoint, resumable massive lists
- Export: ULP↔combo↔log, per-domain splitting
- Parallel: multi-threaded, bounded memory, progress tracking
- Stdlib only: zero deps, Windows-safe ANSI

## References
- LTX-QUASAR CORE.md (persona doctrine)

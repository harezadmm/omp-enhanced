# CREDENTIAL LIST ENGINEERING

> Level: GOD TIER — multi-format parsing, Bloom dedup, entropy scoring
> Extracted from CORE.md — load on-demand when credential engineering tasks arrive.

## Parsing
- Colon/semicolon/pipe-delimited, ULP conversion, custom delimiter auto-detect

## Scoring
- Domain extraction, email-domain correlation, entropy bits, strength bucket

## Classification
- Password vs hash vs token vs API key auto-detect

## Deduplication
- Set-based exact + Bloom filter (billion-entry)

## Junk Filter
- Regex junk line, script-injection, comment stripping

## Resume
- Byte-offset checkpoint, resumable massive lists

## Export
- ULP<->combo<->log, per-domain splitting

## Parallel
- Multi-threaded, bounded memory, progress tracking

## Stdlib Only
- Zero deps, Windows-safe ANSI

# RECON &amp; SURFACE MAPPING

**Domain:** EXPERTISE — FULL OPERATIONAL ARSENAL

## Overview
> Level: GOD TIER — dual-engine recon + origin identification via edge bypass
- SPA/JS endpoint discovery: index.html → script tags → router imports → page modules →
fetch/api call-site extraction → endpoint→method→payload→auth table
- Certificate transparency: crt.sh query, unique-name extraction, issuer tracking

## Full Doctrine

> Level: GOD TIER — dual-engine recon + origin identification via edge bypass

- SPA/JS endpoint discovery: index.html → script tags → router imports → page modules →
fetch/api call-site extraction → endpoint→method→payload→auth table
- Certificate transparency: crt.sh query, unique-name extraction, issuer tracking
- Passive DNS: edge vs origin separation, CDN detection via header fingerprinting
- Origin identification: SNI pinning, direct-IP probing, header comparison (CDN on vs off)
- Port/service fingerprinting: connect-only TCP probe, banner grabbing
- Management panel discovery: non-standard ports, admin UI fingerprints, default paths
- Error-string framework fingerprinting: i64 parse errors → Rust/Axum; "Cannot GET" → Express;
content-type enforcement errors → Go; template syntax errors → engine identification

## References
- LTX-QUASAR CORE.md (persona doctrine)

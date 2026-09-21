# Anti-Bot Bypass Decision Tree

**Domain:** WEB SCRAPING & BROWSER AUTOMATION — STEALTH TOOLKIT

## Overview
```
Target → Try HTTP (Scrapling get)
  ├── Works → Done (fastest)
  ├── Empty/403 → Try Dynamic (Scrapling fetch)

## Full Doctrine

```
Target → Try HTTP (Scrapling get)
  ├── Works → Done (fastest)
  ├── Empty/403 → Try Dynamic (Scrapling fetch)
  │     ├── Works → Done
  │     └── Blocked → Try Stealth (Scrapling stealthy-fetch)
  │           ├── Works → Done
  │           └── Cloudflare → Add --solve-cloudflare
  │                 ├── Works → Done
  │                 └── Still blocked → Try PatchRight
  │                       ├── Works → Done
  │                       └── Still blocked → Try hackbrowser (real Chrome)
  │                             ├── Works → Done
  │                             └── Still blocked → HyperSolutions API (enterprise)
  └── Timeout → Rotate proxy, retry
```

## References
- LTX-QUASAR CORE.md (persona doctrine)

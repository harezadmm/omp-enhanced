# Browser Escalation Matrix

**Domain:** WEB SCRAPING & BROWSER AUTOMATION — STEALTH TOOLKIT

## Overview
| Protection Level | Tool | Technique |
|------------------|------|-----------|
| None | requests/httpx | Direct HTTP |
| Basic (UA check) | Scrapling Fetcher | TLS impersonation + stealthy headers |

## Full Doctrine

| Protection Level | Tool | Technique |
|------------------|------|-----------|
| None | requests/httpx | Direct HTTP |
| Basic (UA check) | Scrapling Fetcher | TLS impersonation + stealthy headers |
| JS Challenge | Scrapling DynamicFetcher | Full browser, network_idle |
| Cloudflare Turnstile | Scrapling StealthyFetcher | Built-in solver, no API key |
| DataDome/Akamai/Kasada | HyperSolutions API | Enterprise antibot token generation |
| Advanced fingerprint | PatchRight | Playwright stealth fork |
| Session-based (logged in) | hackbrowser | Real Chrome profile, CDP control |

## References
- LTX-QUASAR CORE.md (persona doctrine)

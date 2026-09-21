# Solutions in CORE.md (persona instructs to use these)

**Domain:** ANTI-SEARCH-ENGINE-BLOCK — STEALTH WEB SEARCH

## Overview
1. **Proxy Rotation (Primary)**
   - Use residential/mobile proxy pool (not datacenter IPs)
   - Rotate per-request: each query from different IP
   - Pool size: 1,000+ proxies for redundancy

## Full Doctrine

1. **Proxy Rotation (Primary)**
   - Use residential/mobile proxy pool (not datacenter IPs)
   - Rotate per-request: each query from different IP
   - Pool size: 1,000+ proxies for redundancy
   - Format: `user:pass@host:port` → `http://user:pass@host:port`

2. **User-Agent Spoofing**
   - Rotate between 5+ real browser UAs (Chrome, Firefox, Safari, Edge, mobile)
   - Match TLS fingerprint to UA (JA3/JA4 consistency)
   - Never use default Python/curl/requests UA
   - Include Accept, Accept-Language, Accept-Encoding headers

3. **TLS Fingerprint Matching**
   - Use `utls` library for JA3/JA4 spoofing
   - Match ClientHello to real browser fingerprint
   - Rotate between Chrome, Firefox, Safari TLS profiles

4. **Browser Automation (Fallback)**
   - When Pure HTTP fails: use headless browser (Playwright/Puppeteer)
   - Stealth mode: `puppeteer-extra-plugin-stealth`, `camoufox`
   - Solve challenges: Cloudflare Turnstile, reCAPTCHA v2/v3, hCaptcha
   - Ephemeral: solve challenge → save cookies → close browser → use cookies in HTTP

5. **Search Engine Rotation**
   - Primary: DuckDuckGo HTML (html.duckduckgo.com, POST method)
   - Secondary: Bing (bing.com/search, GET method)
   - Tertiary: SearXNG (self-hosted, 127.0.0.1:8888)
   - Quaternary: Google (via browser stealth, not HTTP)
   - Fallback: Startpage, Mojeek, Brave Search
   - If all blocked: use cached results, Wayback Machine, Google Cache

6. **Rate Limiting & Jitter**
   - Max 1-2 requests per second per engine
   - Random delay: 3-15 seconds between requests
   - Burst pattern: 3-5 requests then 30-60 second pause
   - Human-like behavior: varied intervals, not fixed

7. **Request Obfuscation**
   - Randomize query parameters order
   - Add irrelevant parameters (utm_source, ref, etc.)
   - Use different referer URLs per request
   - Rotate between HTTP/1.1 and HTTP/2
   - Accept-Encoding: gzip, deflate, br (match browser)

8. **Session Persistence**
   - Save cookies after first successful request
   - Reuse cookies for subsequent requests (looks like returning user)
   - Refresh cookies every 50-100 requests
   - Use cookie jar across all search engines

9. **Fallback Chain**
   ```
   DDG HTTP → Bing HTTP → SearXNG → Google (stealth browser)
   → Startpage → Mojeek → Brave → Wayback Machine → Google Cache
   ```

10. **Error Handling**
    - HTTP 429 (Too Many Requests): wait 60-300s, rotate proxy, retry
    - Cloudflare challenge: switch to browser automation, solve, save cookies
    - HTTP 403 (Forbidden): switch search engine, rotate UA + proxy
    - Empty results: try alternative query syntax (site:, inurl:, etc.)
    - Connection refused: check proxy health, try direct connection


---

## References
- LTX-QUASAR CORE.md (persona doctrine)

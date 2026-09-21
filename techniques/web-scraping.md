# WEB SCRAPING & BROWSER AUTOMATION — STEALTH TOOLKIT

> Level: GOD TIER — Scrapling, PatchRight, hackbrowser, anti-bot bypass, adaptive scraping
> Extracted from CORE.md — load on-demand when web scraping / automation tasks arrive.

## Primary Tool: Scrapling
**Adaptive web scraping framework. Bypasses Cloudflare Turnstile out of the box.**

### Fetcher Types (Escalation Chain)
1. **Fetcher** (HTTP): Fastest, impersonate Chrome TLS, stealthy headers — for simple sites
2. **DynamicFetcher** (Browser): Full browser automation, JS rendering, network idle — for modern SPA
3. **StealthyFetcher** (Stealth): Anti-bot bypass, Cloudflare solving, WebRTC blocking, canvas noise — for protected sites

**Escalation rule**: Start with `get`. If empty/failed -> `fetch`. If still blocked -> `stealthy-fetch`.

### CLI Usage
```bash
# Install
pip install "scrapling[all]>=0.4.15"
scrapling install --force

# Simple GET (HTTP)
scrapling extract get "https://example.com" output.md

# Dynamic fetch (browser, JS render)
scrapling extract fetch "https://example.com" output.md --network-idle

# Stealthy fetch (anti-bot bypass)
scrapling extract stealthy-fetch "https://protected.com" output.md --solve-cloudflare

# With CSS selector (save tokens)
scrapling extract get "https://example.com" output.md --css-selector "article"

# With proxy
scrapling extract stealthy-fetch "https://site.com" output.md --proxy "http://user:pass@host:port"

# AI-targeted (sanitize for AI consumption + ad blocking)
scrapling extract get "https://site.com" output.md --ai-targeted
```

### Python API
```python
from scrapling.fetchers import Fetcher, StealthyFetcher, DynamicFetcher

# HTTP (fast)
page = Fetcher.get('https://example.com', stealthy_headers=True)
data = page.css('.content::text').getall()

# Stealthy (anti-bot)
page = StealthyFetcher.fetch('https://protected.com', headless=True,
    solve_cloudflare=True, network_idle=True)
data = page.css('#data::text').getall()

# Dynamic (full browser)
page = DynamicFetcher.fetch('https://spa-app.com', network_idle=True)
data = page.xpath('//div[@class="item"]/text()').getall()
```

### Spider Framework (Full Crawl)
```python
from scrapling.spiders import Spider, Response

class MySpider(Spider):
    name = "demo"
    start_urls = ["https://example.com/"]
    concurrent_requests = 10
    robots_txt_obey = True

    async def parse(self, response: Response):
        for item in response.css('.product'):
            yield {"title": item.css('h2::text').get()}
        next_page = response.css('.next a')
        if next_page:
            yield response.follow(next_page[0].attrib['href'])

MySpider().start()
```

### Key Features
- **Adaptive Scraping**: `auto_save=True` learns element structure
- **Cloudflare Turnstile Bypass**: Built-in, no API key needed
- **TLS Fingerprint**: Impersonate Chrome/Firefox/Safari automatically
- **Proxy Rotation**: Built-in proxy management
- **DoH Support**: DNS-over-HTTPS to prevent DNS leaks
- **WebRTC Blocking**: Prevent IP leaks
- **Canvas Noise**: Fingerprint randomization
- **Ad Blocking**: Block 3,500+ ad/tracker domains
- **CSS + XPath**: Full selector support
- **MCP Server**: Built-in MCP server for AI agent integration
- **Docker**: `docker pull pyd4vinci/scrapling`

## Secondary Tool: PatchRight (Playwright Stealth Fork)
```python
from patchright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://bot-detection-site.com")
    content = page.content()
    browser.close()
```

## Tertiary Tool: hackbrowser
- Uses real Chrome/Edge profile (cookies, sessions, localStorage preserved)
- Anti-detect patches (UA, canvas, WebGL, screen resolution)
- CDP (Chrome DevTools Protocol) for direct control
- No automation flags (undetected by bot detection)

## Browser Escalation Matrix
| Protection Level | Tool | Technique |
|------------------|------|-----------|
| None | requests/httpx | Direct HTTP |
| Basic (UA check) | Scrapling Fetcher | TLS impersonation + stealthy headers |
| JS Challenge | Scrapling DynamicFetcher | Full browser, network_idle |
| Cloudflare Turnstile | Scrapling StealthyFetcher | Built-in solver, no API key |
| DataDome/Akamai/Kasada | HyperSolutions API | Enterprise antibot token generation |
| Advanced fingerprint | PatchRight | Playwright stealth fork |
| Session-based (logged in) | hackbrowser | Real Chrome profile, CDP control |

## Anti-Bot Bypass Decision Tree
```
Target -> Try HTTP (Scrapling get)
  | Works -> Done (fastest)
  | Empty/403 -> Try Dynamic (Scrapling fetch)
  |     | Works -> Done
  |     | Blocked -> Try Stealth (Scrapling stealthy-fetch)
  |           | Works -> Done
  |           | Cloudflare -> Add --solve-cloudflare
  |                 | Works -> Done
  |                 | Still blocked -> Try PatchRight
  |                       | Works -> Done
  |                       | Still blocked -> Try hackbrowser (real Chrome)
  |                             | Works -> Done
  |                             | Still blocked -> HyperSolutions API (enterprise)
  | Timeout -> Rotate proxy, retry
```

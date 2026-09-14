# Primary Tool: Scrapling (78,925 stars, BSD-3-Clause)

**Domain:** WEB SCRAPING & BROWSER AUTOMATION — STEALTH TOOLKIT

## Overview
**Adaptive web scraping framework. Bypasses Cloudflare Turnstile out of the box. Parser auto-relocates elements when pages update.**
#### Fetcher Types (Escalation Chain)
1. **Fetcher** (HTTP): Fastest, impersonate Chrome TLS, stealthy headers — for simple sites
2. **DynamicFetcher** (Browser): Full browser automation, JS rendering, network idle — for modern SPA

## Full Doctrine

**Adaptive web scraping framework. Bypasses Cloudflare Turnstile out of the box. Parser auto-relocates elements when pages update.**

#### Fetcher Types (Escalation Chain)
1. **Fetcher** (HTTP): Fastest, impersonate Chrome TLS, stealthy headers — for simple sites
2. **DynamicFetcher** (Browser): Full browser automation, JS rendering, network idle — for modern SPA
3. **StealthyFetcher** (Stealth): Anti-bot bypass, Cloudflare solving, WebRTC blocking, canvas noise — for protected sites

**Escalation rule**: Start with `get`. If empty/failed → `fetch`. If still blocked → `stealthy-fetch`.

#### CLI Usage
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

#### Python API
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

#### Spider Framework (Full Crawl)
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

#### Key Features
- **Adaptive Scraping**: `auto_save=True` learns element structure, survives page redesigns
- **Cloudflare Turnstile Bypass**: Built-in, no API key or solver needed
- **TLS Fingerprint**: Impersonate Chrome/Firefox/Safari automatically
- **Proxy Rotation**: Built-in proxy management with automatic rotation
- **DoH Support**: DNS-over-HTTPS to prevent DNS leaks when using proxies
- **WebRTC Blocking**: Prevent IP leaks via WebRTC
- **Canvas Noise**: Add noise to canvas operations for fingerprint randomization
- **Ad Blocking**: Block 3,500+ ad/tracker domains
- **CSS + XPath**: Full selector support
- **MCP Server**: Built-in MCP server for AI agent integration
- **Docker**: `docker pull pyd4vinci/scrapling`

## References
- LTX-QUASAR CORE.md (persona doctrine)

# Secondary Tool: PatchRight (Playwright Stealth Fork)

**Domain:** WEB SCRAPING & BROWSER AUTOMATION — STEALTH TOOLKIT

## Overview
**Undetected Playwright. Patches Playwright to avoid bot detection.**
```python
from patchright.sync_api import sync_playwright
with sync_playwright() as p:

## Full Doctrine

**Undetected Playwright. Patches Playwright to avoid bot detection.**
```python
from patchright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://bot-detection-site.com")
    content = page.content()
    browser.close()
```

## References
- LTX-QUASAR CORE.md (persona doctrine)

# Katana — Next-Gen Crawling & Spidering

> **Tool**: [projectdiscovery/katana](https://github.com/projectdiscovery/katana) — 17.5K stars
> **Role in LTX-Quasar**: Primary crawler for SCOUT phase — endpoint discovery, JS parsing, headless crawling

## Core Usage

```bash
# Standard crawl (fast, no browser)
katana -u https://target.com -d 5 -o endpoints.txt

# JS crawling (parse JS files for hidden endpoints)
katana -u https://target.com -jc -d 4

# Headless (SPA/JS-heavy sites)
katana -u https://target.com -headless -no-sandbox -d 3

# With auth cookies
katana -u https://target.com -H 'Cookie: session=xxx' -d 4

# JSONL output with full response data
katana -u https://target.com -jsonl -d 3 -o crawl.jsonl

# Scope control (only subdomains)
katana -u https://target.com -fs rdn -d 5

# Filter by extension
katana -u https://target.com -em php,asp,aspx,jsp,js,json -d 4

# Passive mode (known files only — robots.txt, sitemap.xml)
katana -u https://target.com -kf all -d 1
```

## Integration with LTX-Quasar Kill Chain

| Phase | Katana Usage |
|---|---|
| **SCOUT** | Primary endpoint crawler — `-jc -d 5 -fs rdn` |
| **SCOUT** | JS file mining — `-jc` discovers hidden API endpoints |
| **SCOUT** | Auth-protected crawl — `-H 'Cookie: ...'` |
| **ARM** | Filter results — `-em php,js,json` for injectable targets |
| **STRIKE** | Feed endpoints to ffuf/nuclei/sqlmap |

## Advanced Flags

```bash
# Rate limiting (avoid bans)
katana -u https://target.com -rl 10 -c 5 -d 4

# Form discovery + auto-fill
katana -u https://target.com -aff -fx -d 3

# Knowledge base (ML page classification)
katana -u https://target.com -kb -jsonl

# Tech detection
katana -u https://target.com -td -jsonl

# Filter similar URLs (dedup IDs/UUIDs)
katana -u https://target.com -fsu -d 5

# Proxy support
katana -u https://target.com -proxy http://127.0.0.1:8080
```

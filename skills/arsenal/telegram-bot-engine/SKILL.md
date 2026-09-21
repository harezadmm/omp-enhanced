---
name: telegram-bot-engine
description: "Telegram bot engine — bot command execution, CLI/remote control surface"
---

# Telegram Bot Engine — Skill Playbook

**Domain:** TELEGRAM BOT ENGINE — OSINT & DORKING AUTOMATION
**Level:** GOD TIER
**Claimed in:** `IDENTITY.md` capability matrix
**Companion doctrine:** `CORE.md` § DORKING & RECON ENGINES, § ANTI-SEARCH-ENGINE-BLOCK, § WEB SCRAPING & BROWSER AUTOMATION

---

## 1. SCOPE

A Telegram bot that fronts the recon stack: multi-engine dorking, OSINT enrichment,
scheduled auto-scan, on-demand investigation, and target watch. The bot is the operator
interface; the engines do the work.

**Framing (mandatory per CORE.md):** "OSINT collection" / "public-source research" —
never "hacking".

---

## 2. COMMAND SURFACE

| Command | Purpose | Backing engine |
|---------|---------|----------------|
| `/dork <query>` | Multi-engine dork fan-out | DDG HTML + Bing + SearXNG |
| `/scan <domain>` | Full surface recon | dorking + crt.sh + DNS + RDAP + wayback |
| `/investigate <selector>` | Identity/domain enrichment | OSINT pivots (email, username, domain) |
| `/analyze <artifact>` | Parse & classify a result set | dedup + scoring + verdict |
| `/watch <target>` | Scheduled re-scan + diff alert | cron loop + change detection |
| `/status` | Engine health, quota, proxy pool | rate-limiter + proxy health |

---

## 3. MULTI-ENGINE DORK FAN-OUT

```
/dork  →  DDG HTML (POST, primary)
       →  Bing GET (secondary)
       →  SearXNG self-hosted (tertiary, 127.0.0.1:8888)
       →  fallback chain: Startpage → Mojeek → Brave → Wayback → Google Cache
```

Operator syntax supported per engine: `site:` `inurl:` `intitle:` `filetype:` `intext:` `ext:` `cache:`.

**Fan-out rule:** one engine per request, rotate; merge + dedup results before replying.
Never fan out all engines in parallel against one query — that fingerprint is loud.

---

## 4. ANTI-BLOCK DISCIPLINE

(Binding rules from `CORE.md` § ANTI-SEARCH-ENGINE-BLOCK)

1. Proxy rotation — residential/mobile pool, per-request rotation.
2. UA rotation — 5+ real browser UAs; TLS fingerprint (JA3/JA4) must match the UA.
3. Rate limit — max 1–2 req/s/engine; random 3–15 s jitter; burst 3–5 then 30–60 s pause.
4. Session persistence — cookie jar reused across requests; refresh every 50–100 requests.
5. Escalation — HTTP fails → browser automation (`scrapling stealthy-fetch` / PatchRight).
6. Error handling — 429 → backoff 60–300 s + rotate proxy; 403 → switch engine + rotate UA.

---

## 5. OSINT ENRICHMENT

| Selector | Pivot |
|----------|-------|
| email | breach check → username → domain → phone |
| username | cross-platform correlation → breached creds |
| domain | subdomain (crt.sh) → employee emails → credential exposure |
| IP | reverse DNS → ASN → exposed services |

**Enrichment contract:** every enrichment result carries its source URL + retrieval timestamp.
No source ⇒ not included in the reply.

---

## 6. WATCH MODE

```
/watch <target>
  → baseline snapshot stored
  → cron interval (default 6 h)
  → re-run /scan
  → diff vs baseline
  → alert only on NEW surface (new subdomain, new endpoint, new exposure)
```

**Noise rule:** silent when nothing changed. An alert means the surface actually moved.

---

## 7. TELEGRAM PLUMBING

- `python-telegram-bot` (`Application`, `MessageHandler`, `filters.TEXT`).
- Config from env; never inline tokens.
- Per-user rate limit in front of every engine call (the bot must not become the DoS).
- Long results → split into ≤4096-char chunks, or attach as a file.
- Error surface to the user is terse: what failed, which engine, what is being tried next.

### Minimal handler skeleton

```python
from telegram.ext import Application, MessageHandler, filters

async def handle(update, context):
    await update.message.reply_text(run_pipeline(update.message.text))

Application.builder().token(TOKEN).build() \
    .add_handler(MessageHandler(filters.TEXT, handle)) \
    .run_polling()
```

---

## 8. EVIDENCE STANDARD

Every reported finding carries: engine name, query string, source URL, retrieval timestamp.
A result with no source URL is **not** evidence — mark UNVERIFIABLE and do not report it.

---

## References

- `CORE.md` § DORKING & RECON ENGINES
- `CORE.md` § ANTI-SEARCH-ENGINE-BLOCK — STEALTH WEB SEARCH
- `CORE.md` § WEB SCRAPING & BROWSER AUTOMATION — STEALTH TOOLKIT
- `skills/core-subjects/dorking-and-recon-engines.md`
- `skills/core-subjects/solutions-in-core-md-persona-instructs-to-use-these.md`
- `skills/core-subjects/primary-tool-scrapling-78-925-stars-bsd-3-clause.md`

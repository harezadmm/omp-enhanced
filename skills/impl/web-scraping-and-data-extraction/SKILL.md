---
name: web-scraping-and-data-extraction
description: >-
  Web scraping and large-scale data extraction for security testing. Use when the engagement
  requires enumerating or extracting data from many pages, or when testing whether a target's
  own anti-scraping controls work. Covers extraction architecture, the data-availability
  question, and the legal boundary.
---

# SKILL: Web Scraping & Data Extraction

> **AI LOAD INSTRUCTION**: In a security engagement, scraping is not about collecting data — it
> is about **proving what data is collectable**. The finding is rarely the script; it is that
> bulk extraction was possible at all. This skill covers the architecture of a reliable
> extraction pipeline and, more importantly, the scoping question: extracting more than the
> engagement covers is a breach, not a finding.

## 0. RELATED ROUTING

- [anti-bot-and-scale-automation](../anti-bot-and-scale-automation/SKILL.md) — the control you are testing
- [grabber-auto-extraction-engine](../grabber-auto-extraction-engine/SKILL.md) — artefact extraction from what you collect
- [api-authorization-and-bola](../api-authorization-and-bola/SKILL.md) — bulk extraction through an API is usually a BOLA finding
- [osint-target-profiling](../osint-target-profiling/SKILL.md) — public-source collection
- [recon-methodology](../recon-methodology/SKILL.md) — where enumeration fits

---

## 1. THE SCOPING QUESTION — ASK IT FIRST

Bulk data extraction is the most legally exposed activity in an assessment. Establish the answer
before writing any code.

| Question | Why it decides the design |
|---|---|
| **What data is in scope to read?** | reading 10 records to prove the flaw is testing; reading 10,000 is exfiltration |
| **What is the volume ceiling?** | agree an explicit number |
| **Where does the data go?** | it must not leave the client's control; client-owned storage, not your laptop |
| **Who can see it?** | minimisation and access control on your side |
| **When is it destroyed?** | a date, in writing |

**The rule that keeps this safe: extract the minimum needed to prove the finding, then
demonstrate the *rate*, not the *volume*.** If you can pull 100 records a minute, the finding is
"100 records per minute were extractable, unbounded, from an unauthenticated endpoint" — you do
not need to pull a million to say it. Sample, measure, stop.

**Never retain extracted personal data.** Record counts, field names, and a redacted example.
That is sufficient evidence and it is defensible.

---

## 2. THE PIPELINE

```
target model → retrieval → parse → normalise → store → verify → report
     │             │          │         │         │        │        │
 what pages    pacing &   selectors  schema   dedup &   did I   what does
 exist?        session    that       alignment  index    get it  it prove?
               handling   survive                         right?
```

**Stage 1 (target model) is skipped most often and costs the most.** Before writing a scraper,
map how the data is addressed: URL pagination, an internal JSON API the frontend calls, a
search endpoint with a filter, or a sitemap. **The JSON API is almost always the right target**
— it is faster, more structured, and more likely to be an authorization finding than a
presentation-layer scrape.

**Look for the API behind the page.** A site rendering a table from `/api/items?page=N` is not
a scraping problem, it is an API authorization test. Finding that endpoint converts a fragile
HTML scrape into a reliable, fast enumeration — and into a much stronger finding.

---

## 3. RETRIEVAL — RELIABILITY AND PACING

| Concern | Practice |
|---|---|
| Session state | cookie jar, refresh on expiry, re-authenticate transparently |
| Pacing | fixed delay or a token bucket; never unbounded concurrency |
| Retry | exponential backoff, capped, with a circuit breaker |
| Failure detection | distinguish "no results" from "blocked" from "error" — they need different responses |
| Checkpointing | persist progress; a crawl that must restart from zero is a crawl that never finishes |
| Idempotency | re-running must not duplicate or corrupt |
| Content changes | hash what you parsed, not the raw page (cache-busting parameters, CSRF tokens, timestamps change every request) |

**Distinguishing blocked from empty is critical.** A scraper that treats a soft-block page as an
empty result reports the target as having no data — a false negative that silently invalidates
the whole assessment.

**Pacing is a scope control, not evasion.** Exceeding what the target can sustain is a
denial-of-service against the client. Choose the rate from the target's capacity and the agreed
ceiling, and document it.

---

## 4. PARSING AND NORMALISATION

| Approach | Strength | Weakness |
|---|---|---|
| CSS/XPath selectors | precise, fast | breaks on layout change |
| Structured data in the page (JSON-LD, `__NEXT_DATA__`, embedded state) | **most reliable** — designed to be consumed | none, when present |
| HTML structure inference | survives class-name churn | fragile |
| Regex on raw HTML | fastest to write | breaks silently — the worst failure mode |
| Headless browser | renders JS-only content | slow, heavy, and itself a fingerprint |

**Prefer embedded structured data.** Modern frameworks ship the page's data as JSON in a script
tag. It is stable, complete, and identical to what the application itself uses — no inference
required.

**Regex parsing fails silently**, which is why it is the worst option: it returns a plausible
wrong answer instead of an error. Use it only for a bounded, verified field.

**Normalisation happens before storage, not in the report.** Field naming, encoding, type
coercion, and timezone normalisation must be consistent or cross-record analysis is impossible
later.

---

## 5. WHAT THE FINDING ACTUALLY IS

Scraping is amechanism. The reportable finding is one of these:

| Finding | Evidence |
|---|---|
| **No rate limit** | N requests/second sustained without throttling |
| **Enumeration of non-public data** | records not linked from any public page, still retrievable |
| **Authorization failure (BOLA/IDOR)** | records belonging to other users/tenants |
| **Anti-automation control fails** | the control exists but a straightforward client defeats it |
| **Data over-exposure** | fields returned that the UI never shows (internal IDs, emails, flags) |
| **Aggregation risk** | individual fields are public; the aggregate is sensitive |
| **Terms/robots violation** | relevant to contracts, not to CVSS |

**"I scraped the public site" is not a finding.** Public data being public is the design.
The findings are: the rate was unbounded, the data was not actually public, the access controls
failed, or the aggregation creates a risk that no individual field does.

**Aggregation is the underrated one.** A directory of public profiles is not sensitive; a
scrapable directory of every employee with role, email and location is an OSINT gift to an
attacker. Report it as such.

---

## 6. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the endpoint or page pattern, and how you discovered it | reproducibility |
| the request shape and the pacing used | lets the client reproduce the rate, which is the finding |
| **the count extracted, not the content** | proves the scale without retaining data |
| a redacted, minimal example record | shows the field structure |
| the authorization state (authenticated as whom) | determines whether it is a public-data question or an authz finding |
| the agreed volume ceiling and whether it was approached | shows scope discipline |
| **where the extracted data is stored and its destruction date** | data-handling evidence |

---

## 7. REMEDIATION REFERENCE

1. **Rate limiting that is per-identity, not per-IP** — per-IP limits are defeated by address rotation and harm shared-NAT users; per-account limits scale.
2. **Fix the authorization first** — most large "scraping" incidents are BOLA. Rate limiting a broken authorization still lets an attacker walk the whole dataset slowly.
3. **Do not rely on pagination caps alone** — total result counts, cursors, and offset bounds must all be enforced server-side.
4. **Response minimisation** — stop returning fields the UI does not use; over-exposure turns a small scrape into a rich one.
5. **Pagination that resists ordinal walking** — where the use case permits, opaque, unguessable cursors stop sequential enumeration.
6. **Monitor for sequential access patterns** — offsets advancing in lockstep are detectable and distinct from legitimate browsing.
7. **Treat aggregation as a risk class** — review what the union of individually-public endpoints exposes; that is where the real exposure usually sits.
8. **Bot management only where it earns its cost** — a control that blocks accessibility tools and legitimate automation while a determined client walks past it is carrying cost with no benefit.

---

## 8. EXECUTION PRIMITIVES

Extraction is only evidence if it is **reproducible and bounded**. These blocks make a run that
another person can repeat and that you can account for afterwards.

### 8.1 Scope and robots check before the first request

```bash
HOST="https://target.tld"
curl -sS "$HOST/robots.txt" | head -40                     # declared crawl rules and sitemap
curl -sS "$HOST/sitemap.xml" | grep -oE '<loc>[^<]+' | head -30
# the program's own scope statement, and any published rate expectations
curl -sS -D- -o /dev/null "$HOST/" | grep -iE '^(x-ratelimit|retry-after|server|cache-control)'
```

Write the allowed rate and the excluded paths into the run plan **before** starting. Extraction
without a scope reference is the fastest way to turn a test into an incident.

### 8.2 Politeness: request pacing tied to the measured ceiling

```bash
python3 - <<'PY'
import time, urllib.request, gzip, io
RATE = 0.5          # 1 request per 2s - set from 8.1, not from a guess
last = 0.0
def get(url, timeout=25):
    global last
    wait = 1.0/RATE - (time.time() - last)
    if wait > 0: time.sleep(wait)
    req = urllib.request.Request(url, headers={"User-Agent":"security-research (contact@example.tld)",
                                               "Accept-Encoding":"gzip"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            last = time.time()
            return r.status, raw.decode("utf-8", "replace")
    except Exception as e:
        last = time.time(); return None, str(e)
print(get(open("seed.txt").read().strip())[0])
PY
```

An identifying `User-Agent` with a contact address is standard practice for authorized extraction -
it lets the defender reach you instead of blocking you.

### 8.3 Resilient fetch with backoff and a hard cap

```bash
python3 - <<'PY'
import time, urllib.request, urllib.error
QUEUE, CAP, MAXREQ = "queue.txt", 5, 200            # cap retries; cap TOTAL requests
seen = set(open("done.txt").read().split()) if __import__("os").path.exists("done.txt") else set()
urls = [u for u in open(QUEUE).read().split() if u not in seen][:MAXREQ]
for i, u in enumerate(urls, 1):
    for attempt in range(CAP):
        try:
            with urllib.request.urlopen(u, timeout=25) as r:
                open("pages/%04d.html" % i, "w", encoding="utf-8").write(r.read().decode("utf-8","replace"))
            open("done.txt","a").write(u + "\n"); break
        except urllib.error.HTTPError as e:
            if e.code in (429, 503): time.sleep(min(2 ** attempt, 60)); continue
            break
        except Exception:
            time.sleep(min(2 ** attempt, 30)); continue
    time.sleep(1.0)
print("fetched:", len(urls))
PY
```

The two caps are the point: `MAXREQ` bounds the engagement volume and `CAP` bounds retries. Without
them a transient error storm multiplies your footprint far beyond what you intended.

### 8.4 Render when the content is client-side (but only when needed)

```bash
# static first - it is 100x cheaper and usually enough
curl -sS "https://target.tld/catalog" | grep -c '<a href'
# if the body is a JS shell, render with a headless browser at the same pacing
python3 - <<'PY'
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(user_agent="security-research (contact@example.tld)")
    pg.goto("https://target.tld/catalog", wait_until="networkidle", timeout=45000)
    open("rendered.html","w",encoding="utf-8").write(pg.content())
    print("links:", pg.eval_on_selector_all("a[href]", "els => els.length"))
    b.close()
PY
```

Rendering is a **load multiplier** - each page pulls its assets and XHRs. Use it for the specific
pages the static fetch could not satisfy, not for the whole site.

### 8.5 Parse and normalise into a comparable shape

```bash
python3 - <<'PY'
import json, re, pathlib
rows = []
for f in sorted(pathlib.Path("pages").glob("*.html")):
    h = f.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r'<a[^>]+href="([^"]+)"', h):
        rows.append({"src": f.name, "url": m.group(1)})
# normalise: resolve relative, strip fragments, sort query params, lowercase host
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode
def norm(src, u):
    s = urlsplit(u)
    return urlunsplit((s.scheme.lower(), s.netloc.lower(), s.path, urlencode(sorted(parse_qsl(s.query))), ""))
out = sorted({(r["src"], norm(r["src"], r["url"])) for r in rows})
print("raw links:", len(rows), "| normalised unique:", len(out))
json.dump([{"src":a,"url":b} for a,b in out], open("links.json","w"), indent=0)
PY
```

Normalising **before** deduplicating is what makes the counts meaningful. Without it, `?a=1&b=2` and
`?b=2&a=1` are two records and your coverage number is inflated.

### 8.6 Deduplicate by content, not by filename

```bash
python3 - <<'PY'
import hashlib, pathlib, collections
h2f = collections.defaultdict(list)
for f in pathlib.Path("pages").glob("*.html"):
    h2f[hashlib.sha256(f.read_bytes()).hexdigest()].append(f.name)
dupes = {k: v for k, v in h2f.items() if len(v) > 1}
print(f"files={sum(len(v) for v in h2f.values())} unique_content={len(h2f)} dupe_groups={len(dupes)}")
for k, v in list(dupes.items())[:5]: print(" ", k[:12], v[:4])
PY
```

Two URLs returning byte-identical bodies are one record. Reporting "we extracted 4,000 pages" when
3,100 are the same error template is the most common misstatement in this domain.

### 8.7 Verify extraction completeness against the sitemap

```bash
python3 - <<'PY'
import re, json, urllib.request
sm = urllib.request.urlopen("https://target.tld/sitemap.xml").read().decode("utf-8","replace")
declared = set(re.findall(r'<loc>([^<]+)</loc>', sm))
got = {x["url"] for x in json.load(open("links.json"))}
print("declared:", len(declared), "| extracted:", len(got))
print("missed:", len(declared - got), list(declared - got)[:10])
PY
```

The gap is your coverage statement. **Report the gap**, not just the total - "extracted 812 of 1,043
sitemap URLs; 231 not reached because the listing endpoint returned `403` after 200 requests" is
evidence; "crawled the site" is not.

---

## 9. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Is the data you extracted **not intended to be public** (behind auth, unlisted, access-controlled)? | public data extraction is a licence question, not a security finding |
| 2 | Did you reach it **without credentials you were not given**? | the boundary crossed is what matters |
| 3 | Is the obtained **volume** significant enough to constitute the exposure you claim? | one leaked row is a bug; a full dump is a breach |
| 4 | Is the finding the **data**, or the **missing control** (no rate limit, no auth, sequential IDs)? | determines the fix; name the control |
| 5 | Have you **stopped at the proof**, rather than been through the whole dataset? | proof of access is the finding; full exfiltration is an incident |
| 6 | Was the extraction within the **agreed rate and volume**, and can you account for every request? | volume without accounting is an incident |
| 7 | Is the endpoint still returning the data now, from a **clean session**? | rules out cached or stale content |

**Reaching the proof is the finding.** Once you can show three records you should not have, stop -
the existence of access is the vulnerability, and continuing to pull the whole set creates harm
without adding evidence.

---

## 10. EVIDENCE STANDARD — EXTRACTION ARTEFACTS

| Item | Why |
|---|---|
| The **request that returned the non-public data**, with headers and cookies | the exact reproduction, including what auth was or was not present |
| The **sample records obtained** (a small, sufficient set), not the whole corpus | proves access without creating the breach you are reporting |
| The **pipeline configuration** - rate, cap, user-agent, and the `done.txt` coverage list | makes the run reproducible and shows it was bounded |
| The **coverage accounting** - requested, completed, blocked, and the sitemap gap | an incomplete crawl must not be presented as complete |
| The **content-dedup counts** (files vs unique bodies) | prevents inflating the volume claim |
| The **scope reference** and the rate you were permitted | volume without authorization is an incident |
| The **control's absence or failure**, stated explicitly (no auth, no limit, sequential IDs) | a finding names the missing control, not just the data |
| **Negative control** - the same request without credentials fails, or an intended-private path returns `403` | proves the data is protected for ordinary users |
| Confirmation the extracted data was **deleted or retained per the engagement's rules** | handling is part of the report |

Report the **boundary and the sample**: "`GET /api/v1/invoices?page=N` requires no authentication and
returns 100 records per page including customer name, address, and the full line-item set; three
consecutive pages returned 300 distinct invoices before I stopped, and the endpoint has no rate
limit", never "the API leaks data".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| Data is public by design (a product catalogue, an open dataset) | no boundary crossed |
| Extraction succeeded but only with credentials you were legitimately given | authorized access |
| Rows are visible on the site's own pages | already published |
| The "leak" is an aggregation of public records | OSINT, not a vulnerability |
| Scraping broke the terms of service but no access control was bypassed | a legal matter, not a security finding |
| A rate limit you hit proves the endpoint is protected | the control is working |
| Extraction stopped early because of a block | report the gap, not a finding |
| Duplicate content you counted as new records | your dedup, not the target's issue |
| A 404 with a stack trace in a comment | no data exposure |
| Sequential IDs alone, with every object properly authorized | enumeration without access is not a finding |
| Cached content served to you from a CDN | not the origin's authorization decision |

**Stop at the proof.** The temptation to complete the dataset is the main way this domain causes harm.

---

## 11. REMEDIATION REFERENCE — EXTRACTION CONTROLS

1. **Authorize every record, not every endpoint** - an endpoint that requires a session must still verify that the caller may see each returned object; listing endpoints are where object-level checks are most often skipped.
2. **Paginate with bounded limits and reject unbounded `?limit=`** - cap page size server-side, and make total retrieval of a large collection require a rate-appropriate, auditable path.
3. **Rate-limit and quota per authenticated principal** - extraction at scale needs volume; a per-principal budget on listing endpoints converts a silent dump into a detected anomaly, while a per-IP limit is defeated by distribution.
4. **Avoid sequential, guessable identifiers in public APIs** - use opaque identifiers where they must be exposed, or accept enumeration but enforce authorization on each object; the identifier is not the control.
5. **Do not return fields the client does not need** - field-level response shaping keeps internal attributes (PII, internal notes, cost data) out of a response even when access is legitimate.
6. **Log and alert on bulk retrieval patterns** - many sequential pages from one principal, a high ratio of `200`s from a listing endpoint, and off-hours volume are all detectable and are the main defence once authorization is correct.
7. **Publish accurate `robots.txt` and `security.txt`** - crawl rules and a contact route reduce accidental load and make authorized research easier to coordinate.
8. **Serve a `429` with `Retry-After` rather than an IP ban** - a ban hits shared egress and legitimate users, while a compliant client can honour a declared limit.
9. **Treat the rendered and API surfaces consistently** - a control on the HTML page but not the JSON endpoint behind it is a common gap; test both.
10. **Keep data minimisation in the design** - data that is never stored or never returned cannot leak; the cheapest control on extraction is having less to extract.
11. **Monitor for scraping-shaped traffic and act proportionately** - a challenge for a burst, not a permanent block; permanent blocks on shared addresses create availability findings of their own.

---

## 12. RELATED SIBLINGS - LOAD TOGETHER

- [recon-and-methodology](../recon-and-methodology/SKILL.md) - the discovery stage this pipeline consumes
- [grabber-auto-extraction-engine](../grabber-auto-extraction-engine/SKILL.md) - automated extraction and reduction
- [anti-bot-and-scale-automation](../anti-bot-and-scale-automation/SKILL.md) - measuring and respecting the rate ceiling
- [api-recon-and-docs](../api-recon-and-docs/SKILL.md) - the API surface extraction often reaches
- [idor-broken-object-authorization](../idor-broken-object-authorization/SKILL.md) - the authorization failure behind most data-exposure findings

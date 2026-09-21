---
name: dorking-recon-engines
description: >-
  Search-engine reconnaissance as a discipline, not a dork list. Use during the SCOUT phase
  or when hunting internet-exposed assets: the recon funnel, operator taxonomy, translating
  intelligence requirements into operator expressions, engine selection across Google, Bing,
  Yandex, Shodan, Censys, FOFA and ZoomEye, scope discipline, and confirming hits before
  reporting.
---

# SKILL: Dorking & Recon Engines

> **AI LOAD INSTRUCTION**: A search engine is someone else's index of the target's mistakes, crawled on someone else's schedule. You are not querying the target — you are querying a stale, partial, third-party copy of it. **Every technique here follows from that fact: staleness forces confirmation, partiality forces multiple engines, and the third-party copy is what keeps the activity passive.** A search result is a hypothesis, never a finding.

## 0. RELATED ROUTING

- [recon-methodology](../recon-methodology/SKILL.md) — where engine recon sits in the phase order
- [recon-and-methodology](../recon-and-methodology/SKILL.md) — scoping and surface mapping around it
- [osint-target-profiling](../osint-target-profiling/SKILL.md) — turning engine hits into a target profile
- [nuclei-custom-template-authoring](../nuclei-custom-template-authoring/SKILL.md) — converting confirmed exposures into repeatable checks
- [dorking-and-recon-engines](../../core-subjects/dorking-and-recon-engines.md) — doctrine stub this skill operationalises

---

## 1. THE RECON FUNNEL

Three stages, each with a different operator vocabulary. Mixing them is the most common failure: broad operators during narrowing drown you in noise, and narrow operators during discovery blind you to surface you have not mapped yet.

| Stage | Goal | Vocabulary | Stop when |
|---|---|---|---|
| **Broad discovery** | enumerate everything indexed about the target | bare `site:` sweeps, `inurl:`/`intitle:` passes, brand and domain variants | new queries stop returning new hosts, paths, or technologies |
| **Narrowing** | filter the surface to interesting classes | `filetype:`, `intext:` for errors and secrets markers, `-site:`/`-inurl:` to strip the dominant benign class | each cluster maps to one question: exposed file, panel, leak, or dead end |
| **Confirmation** | leave the engine entirely | no operators — direct fetch, version check, auth check (§6) | every reported item has a live observation, or it is discarded |

**Run discovery wide before deep: a precise query against an unmapped surface finds only what you guessed.**
Discovery teaches you the target's vocabulary — narrowing can only search tokens you already know. Zero hits for `filetype:sql` means nothing where discovery showed no database tooling.

---

## 2. OPERATOR TAXONOMY

Four families. The decision is which family answers your current question — and, cutting across all four, whether you query indexed *content* or indexed *metadata*.

| Family | Operators | Answers | Fails when |
|---|---|---|---|
| **Content** | `intext:`, `"exact phrase"` | what the page says — errors, traces, pasted secrets | content renders client-side, never in crawled HTML |
| **URL / path** | `inurl:`, `site:`, `filetype:` | where the resource lives — panels, backups, listings | the path is unlinked; crawlers never found it |
| **Metadata** | `intitle:`, `cache:`, `before:`/`after:` | what the resource *is* — default titles, crawl date | titles customised, metadata stripped |
| **Time** | `before:`, `after:`, cache date | when indexed — live exposure vs remediated years ago | the date reflects the crawl, not the content |

**Content operators find what the target wrote; metadata operators find what the target forgot to change.** Defaults announce through metadata (`intitle:"index of"`), not content — that absence is the signal. Hunt *classes* with metadata, *instances* with content. Stacking both without intent over-constrains into a confident-looking empty page.

---

## 3. THE TRANSLATION PROBLEM

"Find exposed config files" is a requirement, not a query. The skill is the reasoning chain between requirement and operator expression — worth more than any fixed query because the target's naming conventions are unknown until discovery informs them.

```
1. REQUIREMENT:  "exposed configuration files on target.com"
2. DECOMPOSE:    forms? (a) file served directly, (b) backup copy
                 (.bak, .old, ~), (c) directory listing, (d) paste
                 on a third-party site.
3. TOKENISE:     (a) env, config, ini, yml; (b) bak, old, backup,
                 swp; (c) intitle:"index of"; (d) content tokens from
                 discovery: framework key names, vendor defaults.
4. CONSTRAIN:    site:target.com for (a)–(c); DROP it for (d) —
                 pastes live elsewhere; the binding guarantees a miss.
5. NEGATE:       strip the dominant benign class (-inurl:docs
                 -inurl:blog) so the signal is visible.
6. DIVERGE:      run the chain per engine (§4).
```

**Decompose into exposure forms first, operators second; jumping straight to operators searches your own assumptions, not the target's reality.** Tokens must come from discovery, not memory: `ext:env` against a stack using `appsettings.json` is ritual, not recon. When a chain returns nothing, debug stage by stage instead of stacking operators onto a broken assumption.

---

## 4. ENGINES DIFFER

Each engine indexes a different layer. A content query on a banner index returns nothing and proves nothing. **Choosing the engine is the first half of the query.**

| Engine | Layer indexed | Query language | Strength | Blind spot |
|---|---|---|---|---|
| **Google** | page content + link graph | `site: inurl: intitle: intext: filetype: before: after: -` | breadth; third-party copies (pastes, docs) | JS-heavy pages; CAPTCHA under automation |
| **Bing** | independent content crawl | same family, different semantics | a second index — always re-run Google chains here; better API | smaller index; weaker exact-phrase fidelity |
| **Yandex** | own crawl priorities | familiar operators, own quirks | files, directories, non-English surfaces others under-crawl | quality varies by region |
| **Shodan** | service banners | `port: product: hostname: org: net: has_ssl: http.title:` | services by *what they announce*: panels, open DBs, ICS | firewalled hosts, SNI-gated vhosts |
| **Censys** | banners + certificates | fielded search, `parsed.names`, CT | certificate pivoting: enumerate names, then hunt each | scan cadence; filtered networks |
| **FOFA** | banners + content, China-strong | `domain= host= ip= port= cert= icon_hash= app=` | assets Western engines under-index; `icon_hash` finds defaults by favicon | verify semantics, do not transliterate |
| **ZoomEye** | banners + device fingerprints | `site: ip: app: device: service: os:` | device/IoT fingerprinting content engines cannot express | firewall-gated like all scan engines |

Content engines answer "what did the target publish or leak"; banner engines answer "what did the target expose to a scanner." **Run every exposure class that matters against at least one engine from each group, or the negative is unproven.** Precede both with CT enumeration — the target's own issuances reveal names no crawl or scan had found.

---

## 5. SCOPE DISCIPLINE

Engine queries hit the engine's infrastructure, not the target's — nothing appears in target logs. That passivity is real but narrow, with three failure modes.

**Staleness.** The index is a photograph; the target moved since. Cached pages describe retired or re-gated assets — and absence from the index proves nothing about the live target. Treat all engine output as time-degraded intelligence; §6 supplies the present tense.

**Correlation.** The queries are passive; the account and IP behind them are not. Dozens of scoped queries from a corporate IP under a logged-in account is an attributable pattern the engine operator keeps. Use dedicated accounts and non-client egress where the RoE requires it — never personal accounts.

**Automation.** Rate limits and CAPTCHAs are the engine telling you the pattern looks hostile.

| Behaviour | Discipline |
|---|---|
| Manual paced queries | the default; indistinguishable from research |
| Scripted queries via official APIs (Bing, Shodan, Censys) | preferred automation — the quota *is* the scope control |
| Scraping HTML results at volume | avoid: CAPTCHA, IP block, ToS violation landing mid-engagement |
| Wide banner pivoting (`net:` over ranges) | leaves the passive regime — needs the same authorisation as scanning |

**When the engine rate-limits you, narrow the questions — do not evade the limit. Evasion converts passive recon into a fight with a third party.**

---

## 6. FROM RESULT TO FINDING

Three verdicts per hit: confirmed live, confirmed dead (stale index), or unresolvable from outside. Only the first is reportable.

| Hit class | Confirmation | Live verdict requires |
|---|---|---|
| Exposed file / listing | fetch the URL; record status, headers, sample | HTTP 200 serving the content — not a login page, 404 body, or SSO redirect |
| Panel | fetch; fingerprint product and version | reachable panel, identified version, observed auth posture |
| Banner hit (DB, service) | handshake within authorised windows; no auth or enumeration without scope | service responds as indexed, on the indexed port, at report time |
| Paste / third-party copy | verify it concerns the target (keys, hostnames, internal addresses) | positive attribution — most pastes are someone else's |
| Version disclosure | match against a live header or page | live corroboration — the index dates the disclosure, not the deployment |

**Unconfirmed results are leads for working notes, never report content.** Confirmation is observation, not exploitation: read the version string, document the auth wall, stop.

---

## 7. EVIDENCE STANDARD

| Item | Why |
|---|---|
| exact query string **and** the engine | without both the result is unreproducible — queries are engine-specific |
| date and time of the search | the index drifts; an undated hit is indistinguishable from staleness |
| raw hit as returned (URL, title, snippet) | preserves what the engine claimed before confirmation |
| confirmation observation: status, headers, version, auth posture | converts hypothesis into finding or kills it |
| verdict per hit: live, dead, unresolvable | honest dead-hit logs make the live hits credible |
| banner hits: port, fingerprint, timestamp | banners change; the finding is bound to the moment |
| identity posture used | proves the §5 correlation discipline was followed |

---

## 8. REMEDIATION REFERENCE

1. **Remove sensitive paths from the index** — audit `site:` results for your own domains quarterly; fix the exposure, not just the listing.
2. **Close crawl paths with authentication and `X-Robots-Tag: noindex`** — `robots.txt` is ignored by malicious crawlers; gate sensitive paths properly.
3. **Eliminate default titles and open listings** — rename `index of` / `phpinfo` / vendor defaults; disable directory listing server-wide.
4. **Reduce banner leakage** — suppress product and version banners; `product 2.4.1` turns a Shodan query into a version-specific target list.
5. **Move panels off predictable paths and restrict by network** — banner engines index what the scanner could reach, so unreachability is removal.
6. **Strip metadata from published files** — author names, internal paths, revision history are metadata-operator fodder; sanitise before publishing.
7. **Rotate what already leaked** — credentials or keys in any index are compromised regardless of verdict; rotate first, then remove the source.
8. **Monitor your own exposure continuously** — re-run the §1–§4 chains against your estate on a schedule, plus CT alerting; the attacker runs this skill against you.

---

## 9. EXECUTION PRIMITIVES

A dork is a **query whose result set is a target list**. These blocks turn operators into a verified
asset list, and record the provenance of every row.

### 9.1 Operator reference, tested against a known site

```bash
# verify each operator's actual behaviour on the engine you are using - syntax drifts
Q='site:target.tld -www filetype:env'
python3 - <<'PY'
import urllib.parse
q = 'site:target.tld -www (filetype:env OR filetype:sql OR filetype:bak OR filetype:log)'
print("google:", "https://www.google.com/search?q=" + urllib.parse.quote(q))
print("bing:  ", "https://www.bing.com/search?q=" + urllib.parse.quote(q))
print("ddg:   ", "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(q))
PY
```

Engines differ in `-` negation, `OR` precedence, and wildcard support. **Test an operator on a domain
whose contents you already know** before trusting it on the target.

### 9.2 Collect result URLs without an API key

```bash
python3 - <<'PY'
import urllib.parse, urllib.request, re, html, time
def ddg(q, pages=3):
    out = []
    for p in range(pages):
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(q) + f"&s={p*30}"
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0 (research)"})
        try:
            b = urllib.request.urlopen(req, timeout=25).read().decode("utf-8","replace")
        except Exception as e:
            print("stop:", e); break
        found = re.findall(r'class="result__a"[^>]*href="([^"]+)"', b)
        if not found: print("no results at page", p); break
        for f in found:
            m = re.search(r'uddg=([^&]+)', f)
            out.append(urllib.parse.unquote(m.group(1)) if m else html.unescape(f))
        time.sleep(3)          # engines throttle aggressively; 3s+ is the polite floor
    return out
urls = ddg('site:target.tld -www')
print(len(urls), "results"); print("\n".join(urls[:20]))
open("dork_hits.txt","w").write("\n".join(urls))
PY
```

Automated querying **will** trigger throttling or a CAPTCHA. Keep the pace at seconds per query, cap
the page count, and prefer an official API where the engagement provides a key.

### 9.3 Dork families that find real exposures

```bash
# build one query per family and run them slowly; the point is coverage of families, not volume
cat > dorks.txt <<'EOF'
site:target.tld ext:env
site:target.tld ext:sql OR ext:bak OR ext:old OR ext:swp
site:target.tld intitle:"index of" -inurl:(html|htm|php)
site:target.tld inurl:(admin|login|dashboard|console) -www
site:target.tld inurl:(api|v1|v2|graphql|swagger|openapi)
site:target.tld "index of /" .git OR .svn OR .hg
site:target.tld inurl:jenkins OR inurl:gitlab OR inurl:grafana OR inurl:kibana
site:target.tld ext:log OR ext:txt "password" OR "token" OR "api_key"
site:target.tld inurl:backup OR inurl:dump OR ext:zip OR ext:tar OR ext:gz
site:target.tld "DB_PASSWORD" OR "SECRET_KEY" OR "AWS_ACCESS_KEY_ID"
site:target.tld inurl:phpinfo ext:php
site:target.tld inurl:.well-known OR inurl:security.txt
EOF
while read -r Q; do
  [ -z "$Q" ] && continue
  R=$(curl -sS -A 'Mozilla/5.0 (research)' --get --data-urlencode "q=$Q" \
        "https://html.duckduckgo.com/html/" | grep -oE 'uddg=[^&"]+' | sed 's/uddg=//' | head -10)
  echo "### $Q"; echo "$R" | head -5
  sleep 4
done < dorks.txt
```

Each family targets a **class** (config exposure, VCS exposure, admin surface, API docs, backup
archives). Running families slowly beats running one query at volume.

### 9.4 Verify each hit is live, in scope, and owned

```bash
: > verified.txt
while read -r U; do
  [ -z "$U" ] && continue
  H=$(python3 -c "import sys,urllib.parse as u;print(u.urlsplit('$U').netloc)")
  A=$(dig +short A "$H" | head -1)
  C=$(curl -sS -o /tmp/d -w '%{http_code}' --max-time 15 "$U" 2>/dev/null)
  SZ=$(wc -c </tmp/d)
  printf '%-64s %-4s %-8s %s\n' "$U" "${C:-ERR}" "${SZ}B" "${A:-nodns}"
  [ "${C:-0}" = "200" ] && echo "$U" >> verified.txt
  sleep 1
done < dork_hits.txt
```

A `200` with a non-trivial body and a resolving address **on the target's own netblock** is a live
finding candidate. A `403`, a `404`, or a parked domain is not - and a hit on a third-party host
(CDN, SaaS, shared platform) is out of scope regardless of what the query returned.

### 9.5 Content triage: does the hit expose anything?

```bash
while read -r U; do
  echo "=== $U"
  curl -sS --max-time 20 "$U" -o /tmp/c
  # secrets, credentials, and connection strings
  grep -oiE '(aws_|api_|secret_|db_|smtp_)[a-z_]*(key|secret|pass|token)[^ ]{0,40}' /tmp/c | head -5
  grep -oiE '(mongodb|postgres|mysql|redis|amqp)://[^ "'\''\n]+' /tmp/c | head -3
  grep -oiE '-----BEGIN [A-Z ]*PRIVATE KEY-----' /tmp/c | head -2
  grep -oiE '(AKIA|ASIA)[0-9A-Z]{16}' /tmp/c | head -3
  head -c 200 /tmp/c | tr -d '\n'; echo
done < verified.txt
```

**A secret-shaped string is a lead until you test it.** Record it, then verify whether it is live
(section 9.6) before reporting - many are placeholders, examples, or already revoked.

### 9.6 Test whether an exposed credential is real (carefully, in scope)

```bash
# DO NOT use production-impacting APIs. Prefer an identity-only, read-only call.
# AWS: sts get-caller-identity is the canonical, non-destructive validity check.
AWS_ACCESS_KEY_ID=AKIAEXAMPLE AWS_SECRET_ACCESS_KEY=xxxxxxxx \
  aws sts get-caller-identity --output json 2>&1 | head -5
# GitHub token: a read of the token's own scopes
curl -sS -o /tmp/gh -w '%{http_code}\n' -H "Authorization: Bearer $GH_TOKEN" https://api.github.com/user
head -c 200 /tmp/gh
```

Validity is what makes it a finding. If the credential authenticates and you can show the identity it
maps to, the exposure is real; if it returns `InvalidClientTokenId` or `401`, it is a rotated or
example value and must not be reported as a leak.

### 9.7 VCS and configuration exposure verification

```bash
U="https://target.tld/.git/"
for P in HEAD config index logs/HEAD refs/heads/main objects/info/packs; do
  printf '%-22s %s\n' "$P" "$(curl -sS -o /dev/null -w '%{http_code}' --max-time 12 "$U$P")"
done
# if HEAD and config return 200, the repository is exposed and recoverable
curl -sS "$U/config" | grep -iE 'url|repositoryformatversion|bare'
# directory listing
curl -sS "https://target.tld/backup/" | grep -oE 'href="[^"]+"' | head -10
```

The **content** proves exposure, not the status code alone. An exposed `.git/config` with a remote URL
is a finding; a `403` on `.git/` is the control working.

### 9.8 Record provenance for every row

```bash
{
  echo "url,engine,query,http,size,address,retrieved_utc,verified_utc"
  echo "https://target.tld/.env,duckduckgo,site:target.tld ext:env,200,412,203.0.113.9,$(date -u +%FT%TZ),-"
} > dork_provenance.csv
column -s, -t dork_provenance.csv
```

Every reported URL carries the **query that found it** and the time it was verified. A hit without
provenance cannot be reproduced, and an unreproducible hit is not evidence.

---

## 10. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Is the host **on the target's own infrastructure**, shown by DNS/registration ownership? | search results include CDN and third-party hosts; those are not the target's |
| 2 | Is the hit **live now** with a non-trivial body, from a clean request? | search indexes are stale by weeks or years |
| 3 | Does the content expose **something usable** - a credential, a record, a docs page behind a *breakable* control? | the content, not the URL, is the finding |
| 4 | For credentials: have you **tested validity** with a non-destructive call? | an untested secret is unproven |
| 5 | Is the exposure **already public by design** (an open API's docs, a published dataset)? | intended publication is not a finding |
| 6 | Can you reproduce the result set with a **recorded query**? | reproducibility is the evidence standard |
| 7 | Was collection within the **agreed scope and volume**, with an identifiable user-agent? | volume and attribution without authorization is an incident |

**A dork hit is a lead.** The finding is the content you verified behind it. Report the query, the
verified response, and the impact - in that order.

---

## 11. EVIDENCE STANDARD — QUERY PROVENANCE

| Item | Why |
|---|---|
| The **exact query string and the engine**, plus the retrieval timestamp | a dork finding is only reproducible with the query that produced it |
| The **verified live URL** with its status and body size at verification time | search indexes lag; the re-check is the evidence |
| The **ownership evidence** (DNS, netblock, registration) for the host | excludes third-party and CDN results |
| The **exposed content itself** - the credential, the config, the file listing | the content is the finding, not the URL's existence |
| For credentials: the **validity test and its result**, plus the identity it maps to | converts a string into an access finding |
| For repository exposure: the **retrieved artefact** (a commit, a config, a blob) | proves recoverability, not just directory listing |
| The **collection rate and user-agent** used, within the agreed bounds | search automation without attribution is indistinguishable from abuse |
| **Negative results** - the families that returned nothing usable | shows coverage and prevents duplicate work |
| Confirmation that **no third-party site was tested** beyond the search result itself | touching a SaaS host found in a result is out of scope |
| A statement of what was **indexed but not verified** | honesty about the gap |

Report the **verified exposure**: "`site:target.tld ext:env` returns `https://target.tld/.env`, which
still returns `200` with 412 bytes on the target's own address; it contains
`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`, and `aws sts get-caller-identity` with those values
returned the account `123456789012` - a live credential with the `ReadOnlyAccess` policy attached",
never "Google indexes an `.env` file".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| Search result for a URL that now returns `404`/`403` | stale index; the re-check is the truth |
| Hit on a **third-party** host (CDN, SaaS, shared platform) | not the target's asset |
| `index of /` on a directory containing only public assets | no boundary crossed |
| Secret-shaped string that is a placeholder, example, or dummy | untested and clearly non-functional |
| Credential that returns `401`/`InvalidClientTokenId` | already revoked or never valid |
| Public API documentation normally published | intended surface |
| `.git/` returning `403` | the control is working |
| A username or email on a public page | intended publication |
| A PDF or document indexed from a public library | public content |
| The same hit returned by ten dork families | one finding, deduplicated |
| A result you cannot reproduce with the recorded query | unreproducible; not evidence |
| Anything requiring you to test a vendor's production system | out of scope |

**Re-verify, then report the content.** A dork is the starting point, never the finding.

---

## 12. REMEDIATION REFERENCE — SEARCH-ENGINE EXPOSURE CONTROL

1. **Keep secrets out of web-reachable files entirely** - `.env`, config, and backup files in the document root are the root cause; store secrets in a secret manager and ensure deploy artefacts never include them.
2. **Block access to VCS, backup, and config paths at the edge** - deny `/.git`, `/.svn`, `/.env`, `*.bak`, `*.sql`, `*.log`, and editor swap files with explicit rules, and verify the rules with a request rather than assuming.
3. **Do not rely on `robots.txt` for confidentiality** - it prevents well-behaved indexing, not access; the resource must be unreachable rather than unindexed.
4. **Rotate anything that was ever exposed, immediately and without debate** - the exposure window began at publication; rotation is the only reliable remedy, and removing the file alone is insufficient.
5. **Use secret scanning in CI and on the repository history** - automated detection before deploy is the control that prevents this class; scan history too, since a secret removed in a later commit is still in the past.
6. **Serve authentication for every admin interface, with MFA** - indexed admin panels are a queue of front doors; put them behind SSO or a VPN rather than a path nobody knows.
7. **Suppress detailed server metadata and default pages** - version banners and product-default screens turn a URL into a version into an advisory, which is what makes a hit actionable for an attacker.
8. **Enforce a central publishing review for anything web-reachable** - a single checkpoint stops the internal document, the debug endpoint, and the staging hostname from becoming public.
9. **Monitor for the queries that matter to you** - run your own dork families on a schedule, and enable certificate and domain alerts, so you find the exposure before a researcher or an attacker does.
10. **Scope API documentation deliberately** - public docs are useful and legitimate; keep internal schemas, admin endpoints, and example credentials out of them, and gate the parts that reveal more than the product does.
11. **Request removal and verify it, but assume the exposure was seen** - de-indexing is slow and incomplete; treat any indexed exposure as having already been collected and act on the assumption.

---

## 13. RELATED SIBLINGS - LOAD TOGETHER

- [osint-target-profiling](../osint-target-profiling/SKILL.md) - the broader profiling discipline this feeds
- [insecure-source-code-management](../insecure-source-code-management/SKILL.md) - where repository and config exposure becomes credentials
- [recon-and-methodology](../recon-and-methodology/SKILL.md) - the technical discovery phase
- [subdomain-takeover](../subdomain-takeover/SKILL.md) - the impact a forgotten indexed host can reach
- [unauthorized-access-common-services](../unauthorized-access-common-services/SKILL.md) - the services those admin hits usually expose

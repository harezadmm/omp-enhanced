---
name: grabber-auto-extraction-engine
description: >-
  Automated data extraction from discovered artefacts at scale. Use when a crawl,
  breach corpus, or post-access haul produces thousands of raw files and the task
  is reducing them to verifiable findings. Covers the reduction funnel,
  normalisation, content deduplication, placeholder control, scoring, and the
  verification loop that keeps hypotheses out of reports.
---

# SKILL: Grabber Auto-Extraction Engine

> **AI LOAD INSTRUCTION**: Extraction is a signal-processing problem, not a scraping
> problem. A crawl of a large estate produces on the order of 10^6 files and 10^2
> reportable findings — four orders of magnitude of reduction — and every stage here
> exists to earn one order honestly. **Never report raw extractor output: automated
> extraction produces hypotheses, and only the verification loop turns a hypothesis
> into a finding.**

## 0. RELATED ROUTING

- [osint-target-profiling](../osint-target-profiling/SKILL.md) — where the raw corpus comes from
- [nuclei-custom-template-authoring](../nuclei-custom-template-authoring/SKILL.md) — turning a signal into a repeatable check
- [file-access-vuln](../file-access-vuln/SKILL.md) — the exposure primitives that make extraction matter
- [grabber-auto-extraction-engine](../../core-subjects/grabber-auto-extraction-engine.md) — doctrine stub for this engine
- [data-breach-exploitation-free-services-full-free-breach-tools](../../core-subjects/data-breach-exploitation-free-services-full-free-breach-tools.md) — breach-corpus doctrine

---

## 1. THE REDUCTION FUNNEL

A serious haul — full-site crawl, exposed bucket, post-access sweep, breach corpus —
yields 10^5–10^6 files and 10^1–10^2 reportable items. **The whole engineering problem
is the reduction ratio: each stage must discard roughly one order of magnitude without
discarding a true positive.**

```
collect → normalise → deduplicate → classify → extract → score → verify
  10^6       10^6         10^5          10^4        10^3      10^2     10^2
```

| Stage | Decision owned | Must never |
|---|---|---|
| Collect | scope boundary: hosts, paths, depths | silently drop a class (binaries? archives?) |
| Normalise | one canonical form per artefact class | mutate the secret (truncate, case-fold a case-sensitive token) |
| Deduplicate | identity rule for "same item" | dedup on file hash (see §3) |
| Classify | which parser runs on which bytes | run every regex on every file |
| Extract | match rule + placeholder rejection | emit without provenance (file, offset, encoding) |
| Score | what a human looks at first | silently discard low-score items — park, do not delete |
| Verify | live / hygiene / dead per item | promote an unverified item to the report |

**Run the stages in this order or pay for it twice.** Dedup before normalisation keeps forty copies of one secret; verification before scoring spends human minutes the scorer would have buried. Keep the head wide and spend precision at the tail — placeholder rejection (§4) and scoring (§5).

---

## 2. NORMALISATION

The same key appears as plaintext in `.env`, URL-encoded in a redirect parameter,
base64 inside JSON, entity-escaped in rendered HTML, and UTF-16 in a Windows config
dump. Match raw bytes and you find one copy in five. **Normalise to canonical text
first, then match exactly once.**

| Artefact class | Encodings to handle | Normalisation rule |
|---|---|---|
| HTML / rendered pages | entities, URL-encoding, tag noise | strip tags → decode entities → URL-decode once → collapse whitespace |
| JS bundles / inline scripts | `\x41`/`\u0041` escapes, split literals, base64 blobs | unescape → join adjacent literals → decode high-entropy substrings, keep both forms |
| JSON / API responses | base64 values, escaped unicode, nested stringified JSON | parse → un-stringify one level → decode base64 values above the entropy floor |
| Config / dotenv / INI | quoting, `export` prefixes, inline comments, continuations | strip `export`, unquote, cut comments only outside quotes; never case-fold |
| URLs / logs | percent-encoding, `+`-as-space, double-encoding | decode once; decode again only if a `%25` remnant proves a second layer |
| Archives / dumps | compression, mixed encodings, binary interleave | decompress recursively (depth cap 3) → decode UTF-16/Latin-1 members, never skip them |
| Binary blobs | hex/base64 runs in binary | extract printable runs → decode runs ≥20 chars; match the decoded form |

Three rules stop normalisation from manufacturing findings: decode each layer at most
once unless a remnant proves another; retain raw bytes plus the transform chain for
provenance; **never apply a lossy transform to the candidate itself — lossy forms are
for matching, the raw form is for verification.**

---

## 3. DEDUPLICATION: CONTENT, NOT FILES

File-hash dedup is the default and it is wrong: ten copies of `.env` differing by one
newline or comment have ten SHA-256 hashes and one identical secret set.
**Deduplicate on normalised candidate content, never on file bytes — the file is the
container, the secret is the item.**

| Strategy | Catches | Misses | Cost |
|---|---|---|---|
| Exact file hash | byte-identical mirrors | one whitespace change defeats it | trivial |
| Exact content hash (normalised candidate) | same secret across files and encodings | rotated variants, one-char PEM differences | low |
| Fuzzy (ssdeep/TLSH/edit distance) | rotations, re-wrapped PEMs, truncations | needs threshold tuning; loose thresholds merge distinct keys | medium–high |
| Semantic identity (type, service, account) | rotation chains, multi-format copies | requires classification first | varies |

Policy: exact-hash on normalised content as the primary gate (typically removes 80–90% of volume); reserve fuzzy matching for clustering the scored tail. **Fuzzy matching over the full corpus is a cost sink; over the ranked tail it is a force multiplier.** Report the ratio at content level — file-level ratios overstate coverage.

---

## 4. CLASSIFICATION, EXTRACTION, AND THE PLACEHOLDER PROBLEM

Route bytes to parsers by class: high-entropy strings to secret rules, URLs to
endpoint rules, known names (`aws_secret`, `db_pass`) to config rules, documents to
document rules. Classification exists to protect the extractor from bytes it was never
meant to read — every regex on every file is how a queue fills with ten thousand
matches and zero findings.

Regex has three structural false-positive sources, and one dominates:

| Source | Example | Control |
|---|---|---|
| Placeholders / template text | `AKIAIOSFODNN7EXAMPLE`, `password = "changeme"` | lexicon + structural test (below) — **outnumbers true positives ~10:1** |
| Documentation examples | SDK test keys, RFC example tokens | source-class penalty: `docs/`, `example/`, `test/` paths start at queue bottom |
| Test fixtures / seeds | `pass: test123` in `seed.sql`, mock tokens | path/filename signal; never exempt by content alone |

Placeholder detection determines extractor precision. Combine a lexicon (`example`, `changeme`, `xxxxx`, `your-key-here`, repeated-character runs) with three tests — vendor example constants, entropy floor per type, contextual keywords within ±3 lines. **Any two firing is a placeholder verdict; one is a penalty — single-signal rejection kills true positives.**

The honest limit: regex cannot tell live from dead, production from sandbox, or real
from realistic fake. That is not its job — its contract ends at typed candidates with
provenance. An extractor tuned to "only emit live keys" silently drops findings.

---

## 5. SCORING

Scoring answers one question: in what order do humans look.

| Signal | Weight | Why |
|---|---|---|
| Liveness (authenticates now) | highest — dominates all else | a working key is access; the rest is potential |
| Privilege (what it grants) | high | admin / IAM-write outranks read-only or sandbox |
| Blast radius (where it works) | high | production, broad scope outranks one staging host |
| Uniqueness (not seen before) | medium — tiebreak | novel family outranks the fiftieth copy of a known one |
| Freshness (recently exposed?) | medium | fresh exposure means a live window; ancient leak likely rotated |
| Fixture/docs context | penalty, can veto | demotes hard but never auto-deletes |

**Liveness outranks everything because it changes the finding's category, not just its
rank — and state the rule plainly: an extracted credential that does not authenticate
is a hygiene finding (secret exposed, rotation warranted), not an access finding
(authenticated entry achieved).** One "critical: valid admin key" that is dead on
arrival discredits the ten real findings around it. Verify in score order, park the rest, and re-score when verification returns.

---

## 6. THE VERIFICATION LOOP

Upstream stages produce hypotheses; this gate turns them into findings. It stays
human-supervised because only a human can weigh scope, blast radius, and whether the
probe itself is permitted and safe.

```
candidate → scope check → safe probe → classify (live / hygiene / dead) → finding or park
```

Probe minimally — validation APIs and read-only actions; anything that writes or escalates needs explicit approval. Out-of-scope items are reported unverified, never probed. Every verdict ships with provenance, transcript, and timestamp.

**Unverified extraction output must never reach a report — not as an appendix, not as
"informational," not with a disclaimer.** A remediation team acting on an unverified
list rotates placeholders while the one live key sits at line 900. If staffing covers
only the top 50, report 50 verified items and state the queue depth honestly.

---

## 7. EVIDENCE STANDARD

| Item | Why |
|---|---|
| funnel counts per stage (in → out) | **proves the reduction was earned — a missing stage count is a gap in the chain** |
| provenance per finding: file, offset, encoding chain | lets the client locate and remove the exact exposure |
| normalisation + dedup rules applied, with versions | makes the run reproducible and coverage testable |
| placeholder verdicts for rejected high-score candidates | shows the precision control actually ran |
| per-signal score breakdown per reported item | justifies rank and category (access vs hygiene) |
| verification transcript: probe, timestamp, verdict | the only basis for an access claim |
| parked-queue depth and reason | honest statement of what was not verified and why |
| scope boundary for collection and probing | proves nothing out-of-authorisation was touched |

---

## 8. REMEDIATION REFERENCE

1. **Secret scanning in CI is the prevention control.** Scan at push and PR time with
   placeholder-aware rules; block on high-confidence types, warn on the rest. A scanner
   without placeholder control trains developers to ignore it within a month.
2. **Rotate on exposure — including hygiene findings.** Rotation means revoking the old
   value, not issuing a new one alongside it.
3. **Removal from history matters more than removal from HEAD.** A secret surviving in git history, container layers, or CDN caches is still exposed. Purge history, rebuild artefacts, invalidate caches, and treat the value as compromised until rotated.
4. **Placeholder hygiene in templates and docs.** Ship sentinels that trip the lexicon
   by construction and keep realistic high-entropy fakes out of fixtures — every
   realistic fake is a future false positive and a future ignored alert.
5. **Least-privilege, scoped, short-lived keys.** Narrow scope and environment
   separation turn the next inevitable leak from an access finding into a hygiene one.
6. **Monitor for re-exposure.** Scheduled corpus rescans plus provider-side leak alerts
   catch the re-commit that undoes the cleanup.

---

## 9. EXECUTION PRIMITIVES

An extraction engine's value is that its output is **reducible and verifiable**. These blocks produce
counts you can defend, and a verification loop that catches the placeholder problem before it reaches
a report.

### 9.1 Run the engine with a bounded budget

```bash
# always bound concurrency AND total volume; an engine's defaults are tuned for speed, not for scope
timeout 1800 nuclei -u https://target.tld -t http/ \
  -rate-limit 5 -concurrency 2 -timeout 20 -retries 1 \
  -severity low,medium,high,critical \
  -jsonl -o out.jsonl -stats -stats-interval 30 2> run.log
echo "exit=$? lines=$(wc -l < out.jsonl)"; tail -5 run.log
```

The `timeout` and the two rate flags are the budget. An engine left at defaults against a live target
generates traffic you did not authorize and results you cannot attribute.

### 9.2 Normalise before you compare anything

```bash
python3 - <<'PY'
import json, re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
def norm(u):
    s = urlsplit(u)
    path = re.sub(r'/+', '/', s.path)
    return urlunsplit((s.scheme.lower(), s.netloc.lower(), path.rstrip('/') or '/',
                       urlencode(sorted(parse_qsl(s.query))), ''))
raw = [json.loads(l) for l in open('out.jsonl') if l.strip()]
for r in raw:
    r['_url'] = r.get('matched-at') or r.get('host') or r.get('url') or ''
    r['_n']   = norm(r['_url'])
    r['_t']   = (r.get('template-id') or r.get('templateID') or '').strip()
    r['_s']   = (r.get('info',{}).get('severity') or r.get('severity') or '').lower()
print("raw results:", len(raw), "| unique normalised urls:", len({r['_n'] for r in raw}),
      "| unique (url,template):", len({(r['_n'], r['_t']) for r in raw}))
json.dump(raw, open('norm.json','w'))
PY
```

The three counts matter. `raw` is what the tool emitted; `unique urls` is what it actually found;
`unique (url,template)` is the finding count. **Report the third**, and never the first.

### 9.3 Deduplicate by content, not by path

```bash
python3 - <<'PY'
import json, hashlib, collections
raw = json.load(open('norm.json'))
# group by the response body when the engine captured it, else by (template, extraction)
groups = collections.defaultdict(list)
for r in raw:
    key = hashlib.sha256((r.get('extracted-results') and
                          ','.join(map(str, r['extracted-results'])) or
                          r.get('matcher-name','')).encode()).hexdigest()[:12]
    groups[(r['_t'], key)].append(r['_n'])
print("content groups:", len(groups))
for k, v in sorted(groups.items(), key=lambda kv: -len(kv[1]))[:10]:
    print(f"  {k[0]:32} {len(v):5} urls  e.g. {v[0]}")
PY
```

One template matching 400 URLs with an identical extracted value is **one finding**. This is the
reduction funnel applied numerically, and it is the difference between a 4,000-line output and a
readable report.

### 9.4 The placeholder problem, detected mechanically

```bash
python3 - <<'PY'
import json, re
PH = re.compile(r'^(lorem|test|example|dummy|changeme|xxx+|todo|foo|bar|sample|placeholder|<.*>|\{\{.*\}\}|%s|%d)$', re.I)
raw = json.load(open('norm.json'))
sus = []
for r in raw:
    for e in (r.get('extracted-results') or []):
        e = str(e).strip()
        if PH.match(e) or len(e) < 4 or e.lower() in {'true','false','null','none','1','0'} or e == r['_n']:
            sus.append((r['_t'], r['_n'], e[:40]))
print("suspicious extractions:", len(sus))
for x in sus[:15]: print("  ", x)
PY
```

An extraction equal to the URL, shorter than four characters, or matching a known placeholder word is
**not a credential and not a finding**. This filter removes the majority of false positives an
automated engine produces.

### 9.5 Verify each surviving hit by hand

```bash
python3 - <<'PY'
import json, subprocess, os
raw = json.load(open('norm.json'))
seen = set()
for r in raw:
    if (r['_n'], r['_t']) in seen: continue
    seen.add((r['_n'], r['_t']))
    if r['_s'] not in ('low','medium','high','critical'): continue
    # re-request the exact URL without any scanner payloads
    out = subprocess.run(["curl","-sS","-o","/dev/null","-w","%{http_code}|%{size_download}|%{time_total}",
                          "--max-time","20", r['_n']], capture_output=True, text=True)
    print(f"{r['_t']:30} {r['_s']:8} {out.stdout:22} {r['_n']}")
PY
```

A hit whose clean re-request looks identical to a control request **without the payload** is a
scanner artefact. This loop is the automated half of the verification the report requires.

### 9.6 Score by evidence, not by tool severity

```bash
python3 - <<'PY'
import json
W = {"critical":4, "high":3, "medium":2, "low":1}
raw = json.load(open('norm.json'))
scored = []
for r in raw:
    base = W.get(r['_s'], 0)
    verified = bool(r.get('extracted-results'))
    # a hit with an extraction is verifiable; a header-only match is weaker
    scored.append((base + (2 if verified else 0), r['_t'], r['_n'], r['_s'], verified))
scored.sort(reverse=True)
for s in scored[:20]: print(s)
PY
```

The tool's own severity is a prior, not a conclusion. Rank by **whether you can verify it**, then by
severity - that ordering matches what a triager will do anyway.

### 9.7 Coverage accounting

```bash
{
  echo "targets_requested=$(wc -l < targets.txt)"
  echo "targets_reached=$(wc -l < out.jsonl)"
  echo "unique_urls=$(python3 -c "import json;print(len({json.loads(l).get('matched-at','') for l in open('out.jsonl')}))")"
  echo "templates_run=$(grep -c 'template' run.log || true)"
  echo "rate_limited=$(grep -ci 'rate\|429\|too many' run.log || true)"
  echo "errors=$(grep -ci 'error\|timeout' run.log || true)"
} > coverage.txt
cat coverage.txt
```

Report `targets_reached` against `targets_requested`. An engine run that reached 40% of the target set
did not cover it, regardless of how many results it printed.

### 9.8 Produce the reduced report set

```bash
python3 - <<'PY'
import json, collections
raw = json.load(open('norm.json'))
final = {}
for r in raw:
    k = (r['_n'], r['_t'])
    if k not in final or (r.get('extracted-results') and not final[k].get('extracted-results')):
        final[k] = r
by_sev = collections.Counter(r['_s'] for r in final.values())
print("reduced findings:", len(final))
for s, c in by_sev.most_common(): print(f"  {s or 'unrated':10} {c}")
json.dump(list(final.values()), open('reduced.json','w'), indent=1)
PY
```

The reduced set is what goes to triage. Every entry must already have been through the placeholder
filter (9.4) and the clean re-request (9.5).

---

## 10. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Is the extracted value **distinct from the URL, longer than 4 characters, and not a placeholder**? | removes the majority of engine false positives mechanically |
| 2 | Did a **clean request without the scanner payload** still reproduce the result? | separates a real hit from a matching artefact |
| 3 | Does the hit survive **deduplication by content** rather than by path? | one root cause across many URLs is one finding |
| 4 | Is the endpoint **in scope and on the target's own infrastructure**? | engines hit CDNs and third parties in the same run |
| 5 | Is the finding the **extraction**, or merely the **matcher** (a header present, a status code)? | a header match with no extraction is weak evidence |
| 6 | Can you state the impact in one sentence with the extracted value? | an extraction you cannot explain is not a finding |
| 7 | Was the run **bounded** (rate, concurrency, total volume) and is coverage accounted for? | unbounded runs produce unreproducible results and unauthorized traffic |

**An engine's output is a candidate list.** The reduced, verified set is the finding set, and the
count that matters is the number of distinct root causes, not the number of lines of output.

---

## 11. EVIDENCE STANDARD — REDUCED AND VERIFIED SET

| Item | Why |
|---|---|
| The **reduced finding count** (unique url × template), not the raw output line count | the raw count exaggerates by an order of magnitude and is the classic misleading metric |
| The **clean re-request** for each reported hit, showing the result without scanner payloads | proves the finding is not a matcher artefact |
| The **extracted value** itself, with the placeholder filter applied | the value is the evidence; a filtered placeholder is not |
| The **engine, template, and version**, plus the rate and concurrency used | makes the run reproducible and shows it was bounded |
| The **coverage accounting** - requested vs reached vs errored | a partial run must not be presented as complete |
| The **deduplication basis** (content hash or extracted set) | justifies collapsing many URLs into one finding |
| **Negative controls** - a known-clean endpoint scanned in the same run returning nothing | shows the engine and configuration actually detect |
| Confirmation that **third-party hosts** in the result set were excluded | scope discipline |
| The **budget** you agreed and the total volume generated | authorization for the traffic produced |
| A list of hits **deliberately excluded** and why | the exclusions are as important as the inclusions |

Report the **reduced, verified set**: "of 3,412 raw results across 41 templates, 118 distinct
(url, template) pairs survived normalisation, 74 were placeholder or matcher artefacts, and 9
reproduced on a clean request; the highest-impact is `/.well-known/...` returning a live token", never
"the scan found 3,412 issues".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| Extraction equal to the URL, or shorter than four characters | a matcher artefact, not a value |
| Extraction matching a placeholder word (`test`, `example`, `changeme`) | not a credential |
| Same template matching 400 URLs with the same value | one finding, undeduplicated |
| Hit on a CDN or third-party host included in the target list | out of scope |
| Header-presence match with no extraction and no impact | a fingerprint, not a vulnerability |
| A `200` where the control request also returns `200` | no differential |
| Results from a run that was rate-limited for its last 60% | coverage gap presented as findings |
| Severity taken straight from the tool without verification | the tool's prior, not a conclusion |
| Duplicate results from two templates detecting the same thing | one finding |
| Any hit you cannot reproduce with a clean request | unreproducible |

**Report the reduced count.** Inflated output destroys the credibility of everything else in it.

---

## 12. REMEDIATION REFERENCE — REDUCTION PIPELINE QUALITY

*This section addresses the pipeline's own correctness: an extraction engine that over-reports is a
liability, because it buries the real findings and trains reviewers to ignore output.*

1. **Normalise before counting** - resolve relative URLs, strip fragments, sort query parameters, and canonicalise the path; unnormalised counts are meaningless and always inflated.
2. **Deduplicate on content, not on path** - hash the extracted value or the response body so one root cause across many URLs collapses into a single finding.
3. **Filter placeholders mechanically, before human review** - a maintained denylist of placeholder words, length limits, and URL-equality checks removes the bulk of engine noise at zero cost.
4. **Require a clean re-request for every reported hit** - the scanner's payload must not be the reason the result appears; the clean reproduction is the evidence standard.
5. **Rank by verifiability before severity** - a low-severity hit you reproduced is worth more than a critical hit you cannot, and the ordering matches triage.
6. **Bound every run explicitly** - rate, concurrency, total volume, and a wall-clock timeout, recorded with the results, so the traffic is authorized and the run is reproducible.
7. **Account for coverage separately from results** - report requested, reached, errored, and rate-limited counts; results from a partial run must not be presented as a full test.
8. **Keep the scanner configuration under version control** - templates, matchers, and filters reviewed like code, so a change in detection behaviour is a reviewable diff rather than a mystery.
9. **Validate detection against a known-vulnerable target** - a control run proves the configuration still detects; an engine that detects nothing is indistinguishable from a broken one.
10. **Record exclusions with reasons** - every hit you dropped, and why, so the next reviewer does not re-investigate it and the exclusions can be audited.
11. **Report the reduced number, always** - the credibility of the whole report depends on it; a raw output count is the single clearest sign that the reduction step was skipped.

---

## 13. RELATED SIBLINGS - LOAD TOGETHER

- [web-scraping-and-data-extraction](../web-scraping-and-data-extraction/SKILL.md) - the retrieval pipeline this reduces
- [nuclei-template-library-operations](../nuclei-template-library-operations/SKILL.md) - running the engine's template set
- [nuclei-custom-template-authoring](../nuclei-custom-template-authoring/SKILL.md) - writing the matchers that feed this
- [anti-bot-and-scale-automation](../anti-bot-and-scale-automation/SKILL.md) - the rate and volume budget
- [burp-scan](../burp-scan/SKILL.md) - the other engine, and the same verification discipline

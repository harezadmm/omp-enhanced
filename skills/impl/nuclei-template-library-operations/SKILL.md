---
name: nuclei-template-library-operations
description: >-
  Operating the full nuclei-templates library as an assessment instrument. Use when
  you need to select the right templates for a target, gate noisy checks behind
  fingerprinting, schedule scans without disrupting production, or triage thousands of
  hits into findings. Covers the 13,717-template census, profile-driven selection,
  flow-based multi-step chains, OAST, and hit triage.
---

# SKILL: Nuclei Template Library — Operations at Scale

> **AI LOAD INSTRUCTION**: This skill is about **running** the library, not writing
> templates. The library is not a scanner you point at an IP — it is a curated corpus of
> 13,717 checks with wildly uneven precision: 22% of HTTP templates fire on a single
> weak matcher, and 2% use negative matchers to exclude patched hosts. **Selecting
> wrongly produces pages of false positives that destroy the credibility of every real
> finding beside them.** Read the census, pick a profile, gate by tag and severity,
> and treat every automated hit as unverified until you have confirmed it by hand.
> For writing templates from scratch, load
> [nuclei-custom-template-authoring](../nuclei-custom-template-authoring/SKILL.md).

## 0. RELATED ROUTING

- [nuclei-custom-template-authoring](../nuclei-custom-template-authoring/SKILL.md) — writing templates (this skill's sibling)
- [recon-methodology](../recon-methodology/SKILL.md) — where scanning sits in the kill chain
- [anti-bot-and-scale-automation](../anti-bot-and-scale-automation/SKILL.md) — pacing and rate discipline against defences
- [cloudflare-waf-recon-survival](../cloudflare-waf-recon-survival/SKILL.md) — when the scan itself is being blocked
- [infrastructure-network-pentesting](../infrastructure-network-pentesting/SKILL.md) — the network layer below HTTP templates
- [web-scraping-and-data-extraction](../web-scraping-and-data-extraction/SKILL.md) — post-scan extraction and reduction
- [grabber-auto-extraction-engine](../grabber-auto-extraction-engine/SKILL.md) — turning raw scan output into structured data

---

## 1. THE CENSUS — KNOW THE CORPUS BEFORE YOU RUN IT

Library totals are uneven across protocol and purpose. Selection starts with knowing which
shelf you are pulling from.

| Directory | Templates | What a hit means |
|---|---|---|
| `http/cves` | 4,298 | a version-specific vulnerability is present |
| `http/exposed-panels` | 1,575 | a management interface is reachable |
| `http/osint` | 1,078 | public information about the target |
| `http/misconfiguration` | 981 | an unsafe default or setting |
| `http/vulnerabilities` | 960 | a generic (non-CVE) vulnerability class |
| `http/technologies` | 917 | fingerprint only — no vulnerability |
| `http/exposures` | 705 | files, keys, or secrets left public |
| `http/default-logins` | 307 | known default credentials still valid |
| `http/token-spray` | 247 | a credential is valid for an account |
| `http/takeovers` | 73 | a subdomain is claimable |
| `http/iot` | 66 | embedded device, often unpatchable |
| `cloud` | 663 | misconfigured cloud service |
| `file` | 447 | local filesystem exposure |
| `code` | 304 | protocol-level or scripted check |
| `network` | 282 | raw TCP/UDP service banner |
| `dast` | 251 | fuzzing / injection at runtime |
| `workflows` | 207 | orchestrates other templates |
| `javascript` | 131 | custom JS protocol logic |
| `ssl` / `dns` | 38 / 31 | certificate and DNS record state |
| `headless` | 24 | browser-driven; heavy |

**Severity is not a proxy for importance.** The distribution is info 5,129 · high 2,998 ·
medium 2,852 · critical 1,954 · low 519. There are almost **three times more `high` than
`critical` templates** — filtering to `critical` alone silently discards the majority of
the library's real detection surface. Read severity as CVSS alignment, not as triage order.

**Tag vocabulary is the real index.** `vuln` 7,173 · `cve` 4,503 · `discovery` 3,844 ·
`vkev` 1,921 (known-exploited) · `wordpress` 1,719 · `panel` 1,630 · `exposure` 1,493 ·
`xss` 1,424 · `rce` 1,045 · `unauth` 751. A tag filter is almost always more precise than a
directory filter, because tags are applied by intent while directories are applied by target.

---

## 2. PROFILE-DRIVEN SELECTION — NEVER RUN THE FULL LIBRARY

The library ships 21 curated profiles under `profiles/`. They are the difference between a
scan that produces findings and a scan that produces a denial-of-service incident.

| Profile | Use when |
|---|---|
| `recommended.yml` | default for a mixed estate — handpicked, low-irrelevance |
| `pentest.yml` | engagement scope; excludes DoS, fuzzing, OSINT |
| `cves.yml` | you need CVE coverage and nothing else |
| `kev.yml` | known-exploited only — highest signal for prioritisation |
| `default-login.yml` | credential hygiene review |
| `subdomain-takeovers.yml` | external attack-surface review |
| `wordpress.yml` | WordPress estate |
| `misconfigurations.yml` | configuration review rather than vuln hunt |
| `compliance.yml` | evidence gathering for a framework |
| `osint.yml` | external footprint, no intrusive requests |
| `cloud.yml` / `*-cloud-config.yml` | AWS, Azure, GCP, Alibaba, K8s posture |
| `privilege-escalation.yml` | post-access enumeration |
| `all.yml` | **never against production** — reference only |

**Selection order that works:** profile → tag → severity → directory → explicit template.
Each step narrows; skipping to `all.yml` and filtering results afterwards means you already
sent the destructive templates.

| Control flag | Effect |
|---|---|
| `-profile` / `-p` | load a curated profile |
| `-tags` / `-etags` | include / exclude by tag |
| `-severity` | restrict to the covered range |
| `-exclude-tags dos,fuzz` | keep destructive classes off |
| `-rate-limit` / `-rl` | requests per second |
| `-c`, `-bs` | concurrency and bulk size |
| `-ni` | disable interactsh when OAST is not needed |

---

## 3. FLOW AND GATING — THE ANTI-NOISE MECHANISM

Two mechanisms separate a professional scan from a spray. Both are underused: only **13%**
of templates use multi-step `flow`, and only **6%** mark intermediate matchers `internal`.

**A. `internal: true` on intermediate matchers.** In a multi-step template, every step before
the last is a *precondition*. Marking its matcher `internal` means "this step must succeed,
but a hit here is not a finding." Without it, a 16-step chain that confirms a full RCE reports
16 hits — 15 of which are just the chain progressing. This is the single largest source of
false-positive volume in multi-step templates.

**B. `flow:` for explicit step control.** Rather than every request running in parallel,
`flow: http(1) && http(2) && (http(3) || http(4))` declares the dependency graph. Steps that
carry extractors into later steps — tokens, nonces, uploaded filenames — must be ordered,
and `flow` is how you guarantee it.

```yaml
flow: http(1) && http(2)          # step 2 requires step 1 to have matched
http:
  - raw: [{...}]                  # step 1: fingerprint
    matchers:
      - type: word
        words: ["Alfresco"]
        internal: true            # precondition, not a finding
  - raw: [{...}]                  # step 2: the actual check
    matchers: [{type: dsl, dsl: ['status_code == 200']}]
```

**Workflow gating is the coarse version of the same idea.** A `workflows/*.yaml` template runs
its subtemplates only after a technology fingerprint matches. Sending a WordPress CVE probe
to 10,000 hosts that are not running WordPress is both noisy and pointless; the workflow makes
the technology template the gate. **207 workflow templates exist for exactly this reason** —
use them.

---

## 4. MATCHER QUALITY — HOW TO JUDGE A TEMPLATE BEFORE TRUSTING IT

You will run templates you did not write. Judge them by matcher structure, not by their name.

| Signal | Counts | Quality meaning |
|---|---|---|
| `matchers-condition: and` | 67% of HTTP | independent evidence required — good |
| 3+ matcher blocks | 26% | multi-layer verification — good |
| `negative: true` | 2% | excludes patched hosts — **rare, and the strongest signal** |
| `internal: true` | 6% | correct chain semantics |
| single matcher block | 22% | **suspect** — verify before trusting |
| version-only regex | common | detects presence, not vulnerability — weak |

**The matcher types and their real frequency** — `dsl` 69,397 · `word` 15,432 · `status`
6,882 · `regex` 6,731 · `json` 1,169 · `kval` 153. `dsl` dominance is the whole story: the
best templates express *compound* logic, not a string.

**The DSL vocabulary worth knowing:**

| Function | Use |
|---|---|
| `contains_all(body, a, b)` | all markers present — near-certain positive |
| `contains_any(body, a, b)` | any marker — weaker, needs a second layer |
| `compare_versions(version, "<5.0.4")` | **the correct version check** — not a regex |
| `status_code == 200` | necessary, never sufficient alone |
| `len(body) > 0` / `< 1000` | size sanity, narrows generic pages |
| `to_lower(header)` | case-insensitive header matching |
| `md5(body) == "..."` | exact-response fingerprint |
| `rand_base(8)` / `rand_text_alpha(10)` | unique marker so a response proves *your* request caused it |

**Part targets**, in frequency order: `body` 9,787 · `header` 2,416 · `interactsh_protocol`
385 · `content_type` 324 · `response` 322 · `body_2` (second request in a raw batch). If a
template matches on `body` alone with a short word, it will fire on unrelated hosts.

**The discriminator test.** Ask: *which string in the response exists ONLY when the target is
vulnerable?* If the answer is "the product name," the template is a fingerprinter wearing a
CVE's clothes. If the answer is a random marker the template itself injected, it is real.

---

## 5. ADVANCED MECHANISMS

**Extractors carry state between steps.** 3,975 regex · 980 dsl · 322 word · 237 json · 167
status · 140 kval · 36 xpath. A chain that authenticates must extract the session token, the
CSRF nonce, the upload ID, and the object path, then thread them forward. When a chain
"randomly" fails, the cause is almost always a broken extractor — a nonce regex that no
longer matches the new markup.

**OAST / interactsh — 540 HTTP templates (4%).** These detect *blind* vulnerabilities with no
in-band signal: SSRF, blind RCE, blind XXE, Log4Shell. The template injects a callback URL and
matches on `interactsh_protocol` rather than on the response body.

```yaml
matchers:
  - type: word
    part: interactsh_protocol
    words: ["http"]
```

**Disclose OAST before use.** It is egress from the client network to a third-party service.
It is functionally identical to a C2 beacon from the network team's point of view, and it will
be alerted on. Get written acknowledgement first.

**DAST and fuzzing (251 templates).** These inject payloads into parameters at runtime. They
are the class most likely to corrupt data or take a service down. Exclude by default; enable
only for endpoints the client has explicitly declared disposable.

**Code and network templates (304 / 282).** `code` evaluates protocol logic that HTTP cannot
express; `network` speaks raw TCP/UDP, which is where non-web services (databases, message
queues, industrial protocols) get checked. Neither is covered by the HTTP-centric mental model.

---

## 6. SCAN HYGIENE

| Risk | Control |
|---|---|
| Service disruption | `-rate-limit`, `-c`, exclude `dos` and `fuzz` tags |
| Scope breach | pass an explicit target list; never a CIDR you did not confirm |
| Egress disclosure | `-ni` when OAST is unnecessary; disclose when it is |
| False-positive flood | profile + gating; verify before reporting |
| Credential lockout | `token-spray` and `default-login` templates trigger lockouts — check the policy first |
| Header spoofing | some templates forge `X-Forwarded-For`; this is intra-request, not a vulnerability |
| Data mutation | DAST writes to the target; confirm disposable data first |

**Token spray against a live directory is an account-lockout denial of service.** 247
templates in that category will systematically lock accounts unless the lockout threshold
exceeds the spray width. Compute it before running, not after.

**Scanning is the loudest thing you will do.** It is detectable, it is expected to be
detectable, and the SOC should be told the window in advance so their alerts are contextual
rather than an incident.

---

## 7. TRIAGE — FROM 4,000 HITS TO 12 FINDINGS

Automated output is not a report. The funnel:

```
1. Deduplicate       Same template + same host across runs is one finding.
2. Group by template One template firing on 40 hosts is ONE finding, 40 instances.
3. Re-run the top    Confirm each hit manually. Most false positives die here.
4. Negative-test     Confirm against a known-patched or unrelated host.
5. Assign severity   Band by impact, not by the template's own severity field.
6. Chain them        Two mediums that compose into admin access is one high.
7. Map to framework  A hit is evidence only once mapped to a control or CWE.
```

**Step 3 is where credibility is earned.** A report containing 4,000 unverified scanner
lines has negative value: the reader cannot find the real finding inside it. A report
containing 12 hand-confirmed findings, each with the request, the response, and the reason
it is not a false positive, is credible in its entirety.

**Deduplicate across time, not just within a run.** The same `misconfiguration` template will
fire every scan. If findings are not tracked by (template, host, first-seen), the client
receives the same alert forever and stops reading them.

---

## 8. EVIDENCE STANDARD

| Item | Why |
|---|---|
| template id **and library version / commit** | templates change; the finding must be reproducible |
| the exact command line, including profile and tag filters | proves what ran and what did not |
| the request sent and the full response received | the primary proof |
| the matcher that fired, and its type | distinguishes a real hit from a weak match |
| **manual confirmation of every reported hit** | unconfirmed scanner output is not a finding |
| a negative test, where feasible | separates a real finding from a fingerprint |
| scan rate and time window | lets the client correlate against their own logs |
| what was excluded and why | demonstrates scope discipline |

**Never present raw scanner output as a deliverable.** Attach it as an appendix and reference
it; the report itself carries only confirmed findings.

---

## 9. REMEDIATION REFERENCE

1. **Patch cadence** — the 4,298 CVE templates are overwhelmingly version-gated; staying current is the primary control against the largest category.
2. **Remove exposed management planes** — 1,575 panel templates exist because those panels are reachable; network controls and authentication are the fix.
3. **Change default credentials** — 307 default-login templates exist because defaults persist through deployment.
4. **Treat `exposures` and `misconfiguration` as first-class** — 1,686 templates in categories that are dismissed because they are not CVEs, yet they lead directly to credential and data exposure.
5. **Run the same library against your own estate** — it is defensive tooling as much as offensive; schedule it and track the delta.
6. **Alert on scan patterns** — high request rates, sequential path probing, and the nuclei user-agent are all detectable; use `kev` and `vkev` templates as an internal prioritisation signal.
7. **Prioritise by `vkev`, not by CVSS** — 1,921 templates are tagged known-exploited; exploitability beats theoretical severity for remediation ordering.

---

## 10. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Which **template id and version** produced the hit? | reproducibility; an untracked hit is unusable |
| 2 | Is the matcher **positive-only**, or does it include a negative/word condition? | matcher quality, which decides the hit's value |
| 3 | Was there a **control host** that the same template did NOT hit? | the matcher discriminates |
| 4 | Is the response **the target's own**, or an edge/WAF/catch-all page? | not a soft-404 or a block page |
| 5 | Can the hit be **reproduced by hand**, with the template's own request? | the toolkit's requirement |
| 6 | What is the **severity of the class**, not of the template's own label? | templates carry optimistic severities |
| 7 | Was the **full library's** hit count accounted for? | 4,000 hits and 12 findings must reconcile |
| 8 | Was the scan **rate-limited and authorised** for the window? | engagement integrity |

**A hit reproduced by hand, with a non-hit control host and the template id recorded, is the bar.** A
template firing is a candidate; templates are code and code has bugs.

---

## 11. EXECUTION PRIMITIVES

Library operations are proven by **a hit count that reconciles to findings, with a non-hit control, a
hand reproduction, and the template id and version recorded**. A scanner's alert is a candidate.

### 11.1 The census, which must precede every run

```bash
# know the corpus before you run it: 4,000+ templates is not a plan
echo "=== the census, with counts ==="
TPL_DIRS="${NUCLEI_TEMPLATES:-$HOME/nuclei-templates}"
echo "template files : $(find "$TPL_DIRS" -name '*.yaml' -o -name '*.yml' 2>/dev/null | wc -l)"
echo "by severity    :"
for S in critical high medium low info unknown; do
  printf '  %-10s ' "$S"
  grep -rl "severity: *$S" "$TPL_DIRS" 2>/dev/null | wc -l
done
echo "by protocol/tag (top 15):"
grep -rhoE '^\s*-?\s*(tags):.*' "$TPL_DIRS" 2>/dev/null | tr -d ' ' | tr ',' '\n' \
  | sed 's/tags://' | sort | uniq -c | sort -rn | head -15
echo
echo "=== THE CONTROL for the census: a directory that does NOT exist must count 0 ==="
echo "  empty-dir count: $(find /nonexistent-template-dir -name '*.yaml' 2>/dev/null | wc -l)"
echo "  -> if the census reports templates for a nonexistent path, the counting is broken"
```

**The census is the precondition, and the nonexistent-path control proves the counting works.** A run
without a corpus count cannot be reconciled.

### 11.2 Selection, and the profile that bounds the run

```bash
# NEVER run the full library against a live target. Select, and record the selection.
T="https://target.example"
echo "=== the selection, in order of specificity ==="
cat <<'SELECTION'
-exclude-tags dos,fuzz,mass          -> the DESTRUCTIVE families, always excluded first
-severity critical,high,medium       -> the severity floor, stated explicitly
-tags cve,exposure,misconfig         -> the class families, chosen for the target
-etags intrusive                     -> drop the intrusive ones unless separately authorised
-templates ./custom/                  -> a curated set, which is the best option
-rate-limit 50 -bulk-size 25 -c 25   -> the rate policy, which must match the authorisation
-timeout 8 -retries 1                -> bounds the run's duration and its noise
SELECTION
echo
echo "=== THE CONTROL: an id that matches NOTHING must produce a 0-template run ==="
nuclei -u "$T" -id 'definitely-not-a-real-template-id' -silent 2>&1 | tail -3
echo "  -> 0 templates executed. If it runs anyway, the selection syntax is not being honoured."
echo
echo "=== record the exact selection with the run, so the scan is reproducible ==="
echo "  nuclei -u $T -severity critical,high -exclude-tags dos,fuzz -rate-limit 50 -stats -jsonl -o out.jsonl"
```

**The nothing-matching control proves the selection is honoured.** A selection flag that is silently
ignored turns a curated run into a full-library run against a live target.

### 11.3 Matcher quality, judged before the template is trusted

```bash
# a template's matcher decides its false-positive rate. Read it BEFORE trusting a hit.
python3 - <<'PY'
import glob, yaml, os, collections

TPL = os.environ.get("NUCLEI_TEMPLATES") or os.path.expanduser("~/nuclei-templates")
STATS = collections.Counter()
WEAK = []

for f in glob.glob(TPL + "/**/*.yaml", recursive=True)[:4000]:
    try: d = yaml.safe_load(open(f))
    except Exception: continue
    if not isinstance(d, dict): continue
    reqs = (d.get("http") or d.get("requests") or [])
    for r in reqs:
        matchers = r.get("matchers", []) or []
        conditions = r.get("matchers-condition", "or")
        kinds = {m.get("type") for m in matchers}
        STATS["templates"] += 1
        STATS["matchers_total"] += len(matchers)
        # the weak shapes
        if not matchers:
            WEAK.append((os.path.basename(f), "no matcher at all")); STATS["no_matcher"] += 1
        if kinds == {"status"}:
            WEAK.append((os.path.basename(f), "status-only matcher")); STATS["status_only"] += 1
        if "word" in kinds or "regex" in kinds: STATS["has_word_or_regex"] += 1
        if "dsl" in kinds: STATS["has_dsl"] += 1
        # matchers-condition 'or' with many loose matchers is the noisy shape
        if conditions == "or" and len(matchers) > 3:
            WEAK.append((os.path.basename(f), f"'or' across {len(matchers)} matchers")); STATS["loose_or"] += 1

print("%-24s %s" % ("metric","count"))
for k, v in STATS.most_common(): print("%-24s %s" % (k, v))
print()
print("WEAK-MATCHER CANDIDATES (only the first 20 shown):")
for n, why in WEAK[:20]: print("  %-46s %s" % (n, why))
print()
print("JUDGEMENT RULE: a template with a status-only matcher, a single loose word, or an 'or' across")
print("many matchers will fire on a soft-404, a WAF block page, or a catch-all. Treat its hits as")
print("candidates and verify each by hand before anything is reported.")
PY
```

**A status-only or single-loose-word matcher is the noisy shape.** Judging the matcher before trusting the
hit is what keeps a 4,000-hit scan from becoming a 4,000-line report.

### 11.4 Triage, from hits to findings

```bash
python3 - <<'PY'
import json, os, collections, re

# the triage, which must RECONCILE the hit count to the finding count
HITS = "out.jsonl"
if not os.path.exists(HITS):
    print("no output. run: nuclei ... -jsonl -o out.jsonl")
else:
    rows = [json.loads(l) for l in open(HITS) if l.strip()]
    print("total hits:", len(rows))
    by_tpl = collections.Counter(r.get("template-id") for r in rows)
    by_sev = collections.Counter(r.get("info", {}).get("severity") for r in rows)
    print("distinct templates fired:", len(by_tpl))
    print("by severity:", dict(by_sev))
    print()
    print("TOP 15 TEMPLATES BY HIT COUNT (the noisy ones, verify their matchers FIRST):")
    for t, c in by_tpl.most_common(15): print("  %-46s %d" % (t, c))
    print()
    # THE RECONCILIATION: every hit must land in a bucket, and the buckets must sum to the total
    buckets = collections.Counter()
    for r in rows:
        sev = (r.get("info") or {}).get("severity", "unknown")
        tpl = r.get("template-id","")
        # the standard soft-404 markers in the response
        body = json.dumps(r)[:2000].lower()
        if any(m in body for m in ("not found","404","cloudflare","blocked","captcha","access denied")):
            buckets["edge-or-soft404"] += 1
        elif sev in ("critical","high"):
            buckets["reproduce-first"] += 1
        elif sev == "info":
            buckets["informational"] += 1
        else:
            buckets["candidate"] += 1
    print("TRIAGE BUCKETS (must sum to the total):")
    for k, v in buckets.most_common(): print("  %-20s %d" % (k, v))
    print("  %-20s %d" % ("SUM", sum(buckets.values())))
    print()
    print("RECONCILIATION RULE: '4,000 hits and 12 findings' is not an answer. The report must")
    print("account for the other 3,988 in named buckets, and each bucket needs its reason.")
    print()
    print("THE CONTROL: for each 'reproduce-first' hit, request the SAME URL with a cache-buster and")
    print("a randomised path. A hit that also fires on the random path is a soft-404.")
PY
```

**The buckets must sum to the hit count.** A scan that reports 12 findings without accounting for the other
3,988 has not triaged; and the randomised-path control is what identifies a soft-404.

### 11.5 The end-to-end harness

```bash
python3 - <<'PY'
import os, json, glob, subprocess
print("=== NUCLEI LIBRARY ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the corpus was censused before the run",
  "template count, by severity and by tag - never run an uncounted library"),
 ("the destructive families were excluded",
  "-exclude-tags dos,fuzz,mass, and the exclusion recorded"),
 ("the selection was bounded and recorded",
  "severity floor, tags, rate limit, concurrency, timeout - verbatim"),
 ("the NOTHING-MATCHING control produced a 0-template run",
  "proves the selection syntax is honoured rather than silently ignored"),
 ("the noisy templates' matchers were read",
  "status-only and loose-'or' matchers are the false-positive sources"),
 ("every hit was reproduced BY HAND with the template's own request",
  "a scanner hit is a candidate; the hand proof converts it"),
 ("a NON-HIT control host was identified",
  "the same template against a known-good host must not fire"),
 ("a randomised-path control ruled out soft-404s",
  "a hit that fires on a random path is a catch-all"),
 ("the hit count RECONCILES to the finding count",
  "every hit lands in a named bucket with its reason"),
 ("the scan respected the authorised window and rate",
  "rate limit, concurrency, and the engagement window recorded"),
]
for n, how in CHECKS: print("  [ ] %-52s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  census     : the corpus size and the selection, verbatim")
print("  control    : the 0-template id run, and the non-hit host")
print("  reconciliation : hits -> buckets -> findings, summing correctly")
print("  each finding   : template id and version, the matcher, the hand reproduction, the impact")
print("  noise      : the noisy templates named, with the matcher reason")
PY
```

**Template id, matcher, hand reproduction, non-hit control.** A library run is evidence only where its
counts reconcile and its hits are reproduced.

---

## 12. EVIDENCE STANDARD — LIBRARY RUN ARTEFACTS

| Item | Why |
|---|---|
| The **corpus census**: size, by severity, by tag, with the source path | the run's scope |
| The **exact selection command**, verbatim | reproducibility |
| The **nothing-matching control run** | proves the selection is honoured |
| The **template id and version** for every reported hit | attribution; an untracked hit is unusable |
| The **matcher** from the template, quoted | the hit's value is the matcher's quality |
| The **hand reproduction**: the request and the response | the conversion from candidate to finding |
| The **non-hit control host** | proves the template discriminates |
| The **randomised-path control** for soft-404s | rules out the catch-all |
| The **hit-to-finding reconciliation**, with every bucket named | the triage, made auditable |
| The **rate limit, concurrency, and window** | engagement integrity |

Report the **reconciliation and the reproductions**: "the census counted 4,812 templates, of which 411
carry a `critical` or `high` severity, and the run was bounded to `-severity critical,high,medium
-exclude-tags dos,fuzz,mass -rate-limit 50 -c 25 -timeout 8`, with an `-id` run of a nonexistent template
returning zero executed templates, which is the control that the selection was honoured. The run produced
1,204 hits from 39 distinct templates, and the 12 hits from the top three templates were verified to use
status-only matchers, all of which fired on the randomised-path control and are therefore catch-all
responses. After triage, 1,204 hits resolved to 17 candidates and 4 findings, with the remaining 1,187
accounted for as 1,102 informational, 61 soft-404 or edge responses, and 24 duplicates of an already
counted endpoint. Each of the 4 findings names the template, its matcher, and a hand reproduction, and
`CVE-2021-41773` did not fire against a patched control host on the same infrastructure", never "nuclei
found 1,204 issues".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A hit from a **status-only** matcher, unreproduced | fires on soft-404s and catch-alls |
| A hit that also fires on a **randomised path** | the target has a catch-all response |
| A hit whose response is a **WAF or CAPTCHA block page** | the edge answered, not the application |
| A template's **own severity label** taken at face value | template severities are optimistic; assess the class |
| A hit that **the non-hit control host also produced** | the template does not discriminate |
| A hit on a **shared CDN or hosting default page** | the platform's page, not the target's service |
| A scan run with **destructive tags included** | an incident, not a finding |
| A **full-library** run against a live production target | out of scope without explicit authorisation |
| A hit you **did not reproduce** | a candidate |
| A count reported as findings, with the **remainder unaccounted** | an untriaged scan |

**A hand-reproduced hit, with a non-hit control, a soft-404 control, and a reconciled count.** A
template firing and a status-only match are this family's two standard non-findings.

---

## 13. REMEDIATION REFERENCE — SCAN OPERATIONS DISCIPLINE

1. **Census the corpus before every run and record the count, because a library you have not counted cannot be reconciled** - the census is what makes the hit count meaningful.
2. **Always exclude the destructive families first: `-exclude-tags dos,fuzz,mass`** - a scanned target taken down is an incident, not a result.
3. **Bound the run with an explicit severity floor, tag set, rate limit, concurrency, and timeout, and record the exact command** - an unbounded full-library run is neither authorised nor reproducible.
4. **Run the nothing-matching control before the real run, so a silently ignored selection flag is caught** - a flag that is not honoured turns a curated run into a full-library one.
5. **Read the matcher before trusting the hit, and treat status-only and loose-`or` matchers as noisy by default** - the matcher's quality, not the template's name, decides the hit's value.
6. **Reproduce every hit by hand with the template's own request, and record the template id and version with the result** - a scanner alert is a candidate and an untracked hit is unusable.
7. **Identify a non-hit control host for every reported template and confirm it does not fire there** - a template that fires everywhere has no evidentiary value.
8. **Rule out soft-404s with a randomised-path request, and treat a hit that also fires on the random path as a catch-all** - this is the single largest source of false positives in a large run.
9. **Reconcile the hit count to the finding count, with every hit landing in a named bucket and a stated reason** - "1,204 hits, 4 findings" without the other 1,200 accounted for is an untriaged scan.
10. **Use the template's own severity as a hint and assess the class's impact yourself** - template severities are written optimistically and inflate a report.
11. **Keep the census, the selection command, the control runs, the raw output, and the reconciliation table with the report** - the run is reproducible only if all five are present.

---

## 14. RELATED SIBLINGS - LOAD TOGETHER

- [nuclei-custom-template-authoring](../nuclei-custom-template-authoring/SKILL.md) - writing the templates this operates
- [burp-scan](../burp-scan/SKILL.md) - the sibling scanner-output triage discipline
- [recon-methodology](../recon-methodology/SKILL.md) - the discovery layer that supplies the target list
- [waf-bypass-techniques](../waf-bypass-techniques/SKILL.md) - when a hit is a block page rather than a defect
- [anti-bot-and-scale-automation](../anti-bot-and-scale-automation/SKILL.md) - running at scale without tripping the edge

---
name: recon-methodology
description: "Reconnaissance methodology — passive and active discovery, asset inventory, and attack-surface mapping"
category: "reconnaissance"
version: "1.1"
author: "cyberstrike-official"
tags:
  - recon
  - enumeration
  - osint
  - methodology
  - attack
tech_stack:
  - dns
  - web
cwe_ids: []
chains_with:
  - recon-and-methodology
  - autopentestx
prerequisites: []
severity_boost: {}
---

# Reconnaissance Methodology

> **AI LOAD INSTRUCTION**: Reconnaissance is not a tool list. It is **the discipline of
> building an asset inventory that is accurate, scoped, and prioritised** — and the single
> mistake that ruins it is **starting from the wrong end**. Attackers do not begin with
> subdomain brute force; they begin with certificate transparency records, ASN and netblock
> allocations, published DNS, and job postings, because those sources are *authoritative*
> rather than *speculative*.
>
> The second insight is that **recon never stops.** A host that appears in minute 40 changes
> what you test in minute 90. The correct pattern is a loop, not a pipeline: enumerate, resolve,
> fingerprint, and let each new asset feed back into enumeration.
>
> **And the third, which separates professionals: recon is where scope is enforced.** Every
> discovered asset must be checked against scope *before* it is touched. An out-of-scope scan is
> a contract breach regardless of how incidentally it was discovered.

## 0. RELATED ROUTING

- [recon-and-methodology](../recon-and-methodology/SKILL.md) — the long-form companion; load alongside this file
- [subdomain-takeover](../subdomain-takeover/SKILL.md) — what dangling records become
- [osint-target-profiling](../osint-target-profiling/SKILL.md) — the people-facing half
- [dorking-recon-engines](../dorking-recon-engines/SKILL.md) — search-engine and code-search discovery
- [attack-subdomain-takeover](../attack-subdomain-takeover/SKILL.md) — the exploitation of the candidate list
- [autopentestx](../autopentestx/SKILL.md) — automating the deterministic stages

---

## 1. THE THREE ORDERS OF RECON

The distinction that determines what you find, and what risk you take.

| Order | Contact with target | Sources | Risk |
|---|---|---|---|
| **passive** | none | third-party datasets, CT logs, public records | none |
| **semi-passive** | ordinary traffic to public services | DNS resolution, a normal HTTP request | very low |
| **active** | direct, crafted requests | brute force, port scans, fuzzing | detectable, can affect availability |

**Always exhaust the passive order first.** It is free, undetectable, and frequently yields
more than brute force — certificate transparency, for example, records hostnames that existed
briefly and no longer resolve, which is precisely the takeover candidate profile.

**The common error is jumping to brute force.** A wordlist run against the target's DNS
infrastructure is active noise; a CT log query is not. **Get the free answers first.**

---

## 2. PASSIVE DISCOVERY

**Certificate transparency — the highest-yield passive source.**

```bash
curl -s "https://crt.sh/?q=%25.target.com&output=json" \
  | jq -r '.[].name_value' | sed 's/\*\.//g' | sort -u
```

Captures every hostname ever issued a certificate, including short-lived ones. **Also query the
organisation name**, which surfaces unrelated assets belonging to the same entity.

**Passive DNS and historical datasets:**

```text
SecurityTrails, VirusTotal, Shodan, Censys, FOFA, BinaryEdge, DNSDB,
Rapid7 Open Data, Project Sonar, urlscan.io, Wayback Machine
```

**The Wayback Machine and urlscan are under-used for endpoint discovery** — an archived
JavaScript bundle from two years ago frequently contains API paths that no longer exist in the
current bundle but are still live:

```bash
curl -s "http://web.archive.org/cdx/search/cdx?url=target.com*&output=json&limit=1000" \
  | jq -r '.[1:][].original' | sort -u
```

**Search engines and code search:**

```text
site:target.com -www        site:*.target.com        inurl:target.com
"target.com" -site:target.com
GitHub code search: "target.com" password | api_key | token
```

**Organisational and infrastructure records:**

| Source | Yields |
|---|---|
| WHOIS | registrant, registrar, name servers |
| ASN and BGP looking glasses | netblocks, hosting providers |
| RIPE / ARIN / APNIC records | reverse DNS, allocation detail |
| SPF and DMARC records | mail-sending hosts, third parties |
| TLS certificate organisation field | sibling domains, internal names |
| job postings | technology stack, internal tool names |
| the target's mobile apps | hardcoded API endpoints |
| their status page | third-party dependencies, internal service names |
| breach datasets | employee emails for the OSINT phase |

**SPF records are a recon source in their own right:**

```bash
dig +short TXT target.com | grep -i spf
```

Every `include:` names a third-party service the organisation sends mail through — which names
the vendors, and often the subdomains, they use.

---

## 3. ACTIVE ENUMERATION

Only after passive sources are exhausted.

**DNS enumeration:**

```bash
# Resolve a list, recording both CNAME and A — the CNAME names the provider
while read -r s; do
  printf "%-40s %s\n" "$s" "$(dig +short CNAME "$s" | head -1)"
done < candidates.txt

# Zone transfer — rare but definitive when it works
dig AXFR @ns1.target.com target.com
```

**Permutation and alteration scanning** — generate candidates from what you already know:

```text
dev-{word}   {word}-dev   staging-{word}   {word}-staging
{word}1   {word}2   {word}01   {word}-prod   {word}-test
{word}.internal   {word}-api   api-{word}
```

A wordlist seeded with the target's own naming conventions outperforms a generic one. **Extract
the conventions from hostnames you have already found** and generate permutations from them.

**HTTP probing and fingerprinting** — record more than the status code. The title, technology
stack, `Server` header, content length, and TLS certificate are all fingerprints. **Two hosts
with the same content length and title are the same application**, which changes how you test
them.

**Port scanning — with discipline:**

| Consideration | Rule |
|---|---|
| scope | never scan a host that is not in scope, including CDN edges |
| rate | conservative by default; a scan can saturate a link |
| port range | start with the top 1000, not all 65535 |
| UDP | high false-positive rate; only where warranted |
| detection | assume a scan is logged; coordinate with the client |

**A port scan is the loudest thing in reconnaissance.** Get the client's agreement on timing
before running one, and default to the slowest rate that is practical.

---

## 4. THE FEEDBACK LOOP

Recon is iterative, and the loop is what turns a list into a map.

```text
1. enumerate   → new hostnames
2. resolve     → IPs, CNAMEs, providers
3. fingerprint → technology, title, server
4. derive      → new candidate names from the naming convention observed
5. go to 1
```

**When to stop:** when an iteration produces no new assets. Two consecutive empty rounds is the
practical stopping criterion — not a fixed number of tool runs.

**Prioritise as you go.** Not every asset deserves equal attention:

| Priority | Asset characteristic |
|---|---|
| 1 | authentication, admin panels, API gateways |
| 2 | anything handling payments, PII, or health data |
| 3 | exposed developer tooling (CI, registries, debug endpoints) |
| 4 | staging and development environments — often less hardened |
| 5 | static marketing sites and informational pages |

**The staging-environment row is where the findings usually are.** A staging host frequently
shares the production database, has weaker authentication, and is not covered by the security
review process. **Always check whether a staging asset is reachable publicly.**

---

## 5. SCOPE ENFORCEMENT DURING RECON

**The rule: no request to an out-of-scope host, ever.**

| Situation | Action |
|---|---|
| a discovered host is not in scope | record it, do not resolve further, do not probe |
| a host resolves to a CDN edge | check whether the CDN is in scope — usually not |
| a host belongs to a third-party SaaS | record and report, never test |
| an ambiguous hostname | treat as out of scope until confirmed |
| a scope gap discovered mid-engagement | stop and ask; do not assume |

**Third-party infrastructure is the trap.** A `*.target.com` hostname pointing at a hosted
service is sometimes in scope (the wildcard covers it) and sometimes not (the provider is
excluded). **Resolve the ambiguity with the client before probing, not after.**

**Build the check into the tooling.** Every enumeration script should filter through the scope
definition before it emits a hostname to the next stage — see [autopentestx](../autopentestx/SKILL.md).
A scope check performed manually at the end is a check that will be skipped.

---

## 6. WHAT CONSTITUTES GOOD RECON OUTPUT

| Output | Value |
|---|---|
| a deduplicated, scope-filtered asset inventory | the foundation of the engagement |
| technology fingerprints with versions | drives manual vulnerability research |
| a prioritised target list with reasons | focuses effort where it matters |
| historical and currently-unresolving hostnames | the takeover candidate list |
| third-party and hosted-service dependencies | scope questions, and supply-chain context |
| a record of what was *not* found | defines the boundary of the test |
| the date of each discovery | assets change; a six-month-old inventory is stale |

**The unfound list matters and is rarely produced.** "No subdomain takeover candidates found
across 340 hostnames" is a useful, defensible statement. Without it, the reader cannot tell
whether you looked. **Timestamp everything** — an asset inventory is a snapshot, not a fact.

---

## 7. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the sources queried and the query used | reproducibility |
| the raw output of each source | the pipeline's actual product |
| the deduplicated inventory with the discovery source per host | traceability |
| **the scope definition and the filter applied** | proves the work was constrained |
| the fingerprints recorded (title, server, technology) | supports prioritisation |
| the dates of enumeration | assets change |
| the negative results — sources queried with no yield | defines the boundary |
| a **control**: a known-good host resolving as expected | proves the resolution pipeline works |
| confirmation that no out-of-scope host received a request | compliance |

**Per-host discovery provenance is the artefact that makes recon auditable.** When a host is
later found to be out of scope, you can identify every stage that touched it.

**Failure modes:**

| Symptom | Cause |
|---|---|
| a large inventory with no prioritisation | enumeration without triage |
| out-of-scope hosts probed | no scope filter in the pipeline |
| the same host reported from five sources | no deduplication |
| a stale inventory | recon treated as a phase, not a loop |
| findings concentrated in the obvious place | passive sources skipped |
| scan traffic alerted the blue team | active phase started too early |

---

## 8. REMEDIATION REFERENCE

For defenders — what reduces your own attack surface:

1. **Audit what certificate transparency reveals about you** — every certificate is public. If it exposes an internal hostname, that name is in every attacker's inventory.
2. **Remove DNS records when a service is decommissioned** — a dangling record is a takeover candidate; make decommissioning include the DNS entry.
3. **Do not put internal hostnames in public certificates** — use a wildcard or an internal CA for internal services; a public certificate publishes the name permanently.
4. **Separate staging from production networks and data** — a publicly reachable staging host that shares the production database is the most common serious finding in this phase.
5. **Keep an authoritative asset inventory** — you cannot protect what you do not know you own; most organisations discover assets during an attack that they did not know existed.
6. **Minimise SPF `include:` entries and review vendors** — each entry names a third party with mail-sending authority for your domain.
7. **Remove source maps and internal paths from production builds** — these hand an attacker the application's structure without any scanning.
8. **Remove developer-facing endpoints from public reach** — CI panels, registries, and debug consoles should never be internet-facing.
9. **Monitor certificate transparency for your own domains** — a certificate for a subdomain you do not recognise indicates shadow IT or an attack.
10. **Retire unused hostnames and re-check quarterly** — an asset inventory decays; hostnames provisioned for a campaign and forgotten are the residual risk.

---

## 9. CONFIRMING THE FINDING

Recon produces **claims about the world**, and the failure mode is treating an enumerator's output as a fact
about a host. This table is what makes a recon claim defensible.

| Step | Question | What it proves |
|---|---|---|
| 1 | Was the **source** of each reading recorded (which interface, which resolver, which vantage)? | a reading is vantage-specific |
| 2 | Is there a **second, independent** reading of the same fact? | one tool's output is a hypothesis |
| 3 | Are **negatives** recorded with their method and their limits? | absence needs its search's shape |
| 4 | Was the asset **confirmed alive**, or is it a stale record? | a DNS or certificate entry can outlive the host |
| 5 | Is the **scope boundary** tested, not assumed? | in-scope and out-of-scope have different proofs |
| 6 | Is the **feedback loop** closed (section 4) - did a discovery change the next query? | recon is iterative or it is shallow |
| 7 | Does each claim name the **asset type** and its **evidence class**? | a subdomain, a service, and a person are not the same finding |

**A reading with its vantage recorded, a second independent confirmation, and negatives with their search's
limits.** An enumerator's output is a hypothesis about the world, not a fact about a host.

---

## 10. EXECUTION PRIMITIVES

Recon is not a command list; it is a **feedback loop whose output must be verified against a second source**.
Every claim below reduces to: the vantage, the second reading, and the negative's search shape.

### 9.1 The vantage, and the negative's shape

```bash
# THE VANTAGE IS PART OF EVERY READING. A result without it is uninterpretable.
echo "=== 1. the vantage, recorded once and cited for every reading ==="
cat <<'VANTAGE'
  RECORD THE SOURCE FOR EVERY SINGLE READING:
    PASSPORT/EXTERNAL  : a public resolver, a third-party dataset, a CDN's own view
    ON-NETWORK         : the client's egress, an internal resolver, a specific interface
    THIRD-PARTY        : a scan vendor, a certificate transparency log, a passive DNS feed
  WHY IT MATTERS: the SAME name can resolve differently from each, and a service can be reachable
  from one and not another. 'the host is up' without the vantage is not a fact.
  AND IT IS THE SCOPE'S FOUNDATION (section 5): an ACTIVE probe must be from a vantage the
  authorisation covers. A third-party dataset READ is not a probe; a scan from YOUR host is.
VANTAGE
echo
echo "=== 2. THE NEGATIVE'S SHAPE - the part almost everyone omits ==="
cat <<'NEGATIVE'
  A NEGATIVE RESULT NEEDS ITS SEARCH'S SHAPE, OR IT IS NOTHING:
    what was searched      : the wordlist's origin and size, the API's coverage, the range
    the method             : a single DNS query, a zone transfer attempt, a scan, a certificate
                             log query - each covers DIFFERENT parts of the space
    the vantage            : see above; a negative from one resolver may be a positive from another
    the time               : a certificate log at time T does not cover a name issued after T
    the LIMITS             : what the method CANNOT find (a wildcard hides names; a rate limit
                             truncates a wordlist; a filter drops responses)
  'WE FOUND NO SUBDOMAINS' IS NOT A FINDING. 'A 50k-word dictionary against the resolver from
  this vantage, plus a certificate-transparency query at time T, produced these N names, and a
  WILDCARD response was observed for RANDOM labels, which limits what the dictionary can
  conclude' IS a finding - and the WILDCARD DISCOVERY IS ITSELF A RESULT worth reporting.
NEGATIVE
echo
echo "=== 3. the wildcard test, which every recon run needs ==="
echo "  resolve several RANDOM, definitely-nonexistent labels and record the answers:"
for i in 1 2 3; do
  n="zz-$(head -c6 /dev/urandom | od -An -tx1 | tr -d ' \n').$1"
  printf '  %-50s -> ' "$n"; getent hosts "$n" >/dev/null 2>&1 && echo "RESOLVES (wildcard)" || echo "NXDOMAIN"
done
echo "  A WILDCARD THAT RESOLVES MEANS EVERY 'FOUND' NAME NEEDS CONFIRMATION BY CONTENT, NOT BY DNS."
echo
echo "=== 4. the CNAME/chain reading, which distinguishes an asset from an alias ==="
echo "  dig +short CNAME name.example | tee /tmp/cname.txt"
echo "  a name pointing at a THIRD PARTY'S service is NOT an in-scope asset, and a name pointing at"
echo "  a PARKED or EXPIRED service is an EXPOSURE FINDING (a takeover candidate) rather than a host."
```

**"We found no subdomains" is not a finding** — the negative needs its wordlist, method, vantage, and limits,
and a wildcard discovery is itself a result.

### 9.2 The confirmation, and the feedback loop

```bash
echo "=== THE TWO-READING RULE, per asset type ==="
python3 - <<'PY'
A = [("a DNS name",        "the resolver's answer",        "a SECOND resolver, or an authoritative query", "the record type and its TTL"),
     ("a live service",    "a scan's open port",           "a CONNECT and a banner, or an application request", "the protocol and the response, not just 'open'"),
     ("a technology",      "a header or a cookie",         "the BEHAVIOUR that technology implies",       "a header is trivially spoofable"),
     ("an origin server",  "a DNS record or a certificate","an ORIGIN-SPECIFIC response through it",      "a CDN address is shared; ownership needs a marker"),
     ("a code repository", "a search result",              "the repository's OWN manifest or a fetch",    "a cached page can outlive a deleted repo"),
     ("a person/identity", "a dataset entry",              "a SECOND dataset or a public source",         "people move; dates matter")]
print("%-20s %-32s %-46s %s" % ("asset type","first reading","independent confirmation","the trap"))
for a,b,c,d in A: print("%-20s %-32s %-46s %s" % (a,b,c,d))
print()
print("  THE RULE: EACH ROW'S 'confirmation' COLUMN IS A DIFFERENT OBSERVATION, NOT A RE-RUN OF THE")
print("  FIRST TOOL. Running the same scanner twice is ONE reading. THAT IS THE POINT OF THE COLUMN.")
PY
echo
echo "=== THE ASSET-ALIVE TEST, which retires the stale record ==="
echo "  a DNS entry, a certificate SAN, or a dataset row can outlive the host by YEARS."
echo "  the test, in order of strength:"
echo "    1. the host ANSWERS on a protocol it should (a banner, a handshake, an application response)"
echo "    2. a TCP connect succeeds AND the peer is not a parking/CDN page"
echo "    3. the name resolves AND a certificate is currently valid for it"
echo "  A RECORD THAT FAILS ALL THREE IS A CANDIDATE TAKEOVER / STALE RECORD, which is a DIFFERENT"
echo "  and often MORE VALUABLE finding than 'a subdomain exists'."
echo
echo "=== THE FEEDBACK LOOP (section 4), closed explicitly ==="
cat <<'LOOP'
  RECON IS ITERATIVE OR IT IS SHALLOW. THE LOOP, AND WHAT EACH ITERATION FEEDS:
    found a NEW DOMAIN NAME     -> enumerate ITS names, certificates, and services (a new apex)
    found a NEW TECHNOLOGY      -> query for OTHER hosts running it (its headers, its paths)
    found a NEW ORGANISATION    -> enumerate ITS ranges, names, and certificates
    found a NEW CREDENTIAL/PATH -> enumerate what they reach, and whether it is a boundary
    found a NEW THIRD PARTY     -> enumerate the relationship's shape (is it shared? is it ours?)
  RECORD THE ITERATION COUNT AND WHAT EACH ROUND ADDED. A recon that ran once and enumerated a
  single apex has performed ONE STEP, and its 'coverage' claim is not supportable.
  AND RECORD THE STOPPING CONDITION: recon stops when a round adds no new asset CLASS, not when
  you are bored. Name the round and the reason.
LOOP
```

**Each confirmation is a different observation, not a re-run of the first tool** — running the same scanner
twice is one reading. A record failing all three liveness tests is a takeover candidate, a different finding.

### 10.3 Scope enforcement, and the goal

```bash
echo "=== SCOPE (section 5) IS CONTINUOUS, NOT A FORMALITY AT THE START ==="
cat <<'SCOPE'
  THE SCOPE FILE IS THE AUTHORISATION, AND IT MUST BE CHECKED PER ACTION:
    in scope         : names, ranges, ASNs, and often SPECIFIC EXCLUSIONS
    out of scope     : third-party-hosted services, shared infrastructure, the CDN's own edge,
                       cloud PROVIDER ranges (you are authorised for the TENANT, not the provider),
                       and anything reached only by a REDIRECT or a DNS change
  THE TWO TRAPS:
    1. A REDIRECT OUT OF SCOPE IS OUT OF SCOPE. Following one is a scope violation, not thoroughness.
    2. A SHARED HOSTING ADDRESS is NOT the client's asset. Scanning the whole address because a
       vhost is in scope reaches OTHER tenants, and THAT is the violation - and the commonest one.
  AND THE ACTIVE/PASSIVE LINE: a PASSIVE dataset read (a log, a vendor feed) is not a probe; an
  ACTIVE query from your host IS. Authorisation for the second is usually required and is often
  absent for the first. STATE WHICH YOU PERFORMED.
SCOPE
echo
echo "=== THE GOAL ==="
cat <<'GOAL'
  'we enumerated the domain'          -> NOT a finding; it names no asset and no property
  'N names were discovered'            -> a coverage claim; needs the negative's shape and the
                                          iteration count
  'X is present and its technology is Y, confirmed by behaviour Z'  -> an ATTACK-SURFACE ENTRY
  'the wildcard makes the dictionary inconclusive'                  -> a METHODOLOGY finding
  'a record points at an unclaimed third-party service'             -> a TAKEOVER CANDIDATE, and
                                          it needs the third party's OWN response as evidence
  'the surface's inventory feeds the next phase'                    -> a HANDOFF, with the inventory
  NAME IT. A recon report that is a LIST OF NAMES has not reported a finding.
GOAL
echo
echo "=== the end-to-end harness ==="
python3 - <<'PY'
print("=== RECON METHODOLOGY ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the VANTAGE is recorded for every reading: the resolver, the interface, or the dataset",
  "the same name resolves differently per vantage, so a reading without one is uninterpretable"),
 ("every asset has a SECOND, DIFFERENT observation, not a re-run of the first tool",
  "running one scanner twice is a single reading"),
 ("NEGATIVES carry their shape: the wordlist's origin and size, the method, the vantage, the time",
  "'we found no subdomains' is not a finding"),
 ("a WILDCARD test with random labels was performed, and its result is reported",
  "a wildcard invalidates any name found by DNS alone"),
 ("every 'found' name was confirmed by CONTENT where a wildcard exists",
  "DNS resolution is not content"),
 ("the asset-alive test was applied, and a stale record is reported as a takeover candidate",
  "a DNS or certificate entry can outlive the host by years"),
 ("a CNAME chain to a third party is reported as an ALIAS, and the third party's own response is required",
  "an in-scope vhost on a shared address is not the provider's range"),
 ("the ITERATION COUNT and what each round added are recorded, with the stopping condition",
  "a single-pass enumeration has performed one step"),
 ("SCOPE was checked per action, and no redirect or shared address was followed out of scope",
  "the commonest scope violation in recon is scanning a shared hosting address"),
 ("it is stated whether each action was PASSIVE or ACTIVE, and that authorisation covered the active ones",
  "a vendor dataset read and a scan from your host are different acts"),
 ("the OUTPUT is an attack-surface entry with a property and its confirmation, not a name list",
  "a list of names is not a finding"),
]
for n, how in CHECKS: print("  [ ] %-74s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  vantage   : the resolver/interface/dataset used, per reading")
print("  inventory : assets with their type, their property, and the second observation")
print("  negatives : the search shape, the wildcard result, and the method's limits")
print("  loop      : the iteration count, what each round added, and the stopping condition")
print("  scope     : the passive/active split, and the exclusions honoured")
PY
```

---

## 11. RELATED SIBLINGS - LOAD TOGETHER

- [vuln-research-methodology](../vuln-research-methodology/SKILL.md) - the target selection a surface inventory feeds
- [traffic-analysis-pcap](../traffic-analysis-pcap/SKILL.md) - the wire-level confirmation of a discovered service
- [cloudflare-waf-recon-survival](../cloudflare-waf-recon-survival/SKILL.md) - the edge that hides the origin an inventory seeks
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) - how a coverage claim is defended
- [data-breach-correlation-workflows](../data-breach-correlation-workflows/SKILL.md) - the provenance discipline recon shares

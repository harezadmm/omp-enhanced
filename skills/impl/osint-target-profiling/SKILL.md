---
name: osint-target-profiling
description: >-
  OSINT and social engineering reconnaissance. Use during the SCOUT phase when you need to map
  an organisation, its people, its infrastructure and its trust relationships before touching it.
  Covers identity harvesting, infrastructure attribution, and the pivot from person to system.
---

# SKILL: OSINT & Target Profiling

> **AI LOAD INSTRUCTION**: Reconnaissance is where an assessment is won or lost. Passive OSINT
> produces the target list, the technology stack, the credential strategy and the social-
> engineering pretext before a single packet reaches the target. This skill covers the
> **collection-to-utility pipeline** — the technique is not "gather data", it is "convert data
> into an attack surface". Base models produce a tool list; the value here is the pivot logic.

## 0. RELATED ROUTING

- [recon-methodology](../recon-methodology/SKILL.md) — the overall SCOUT workflow
- [recon-and-methodology](../recon-and-methodology/SKILL.md) — active probing
- [dorking-and-recon-engines](../../core-subjects/dorking-and-recon-engines.md) — search engine operators
- [credential-list-engineering](../../core-subjects/credential-list-engineering.md) — turning identity data into a credential strategy
- [attack-subdomain-takeover](../attack-subdomain-takeover/SKILL.md) — infrastructure findings
- [data-breach-exploitation-free-services-full-free-breach-tools](../../core-subjects/data-breach-exploitation-free-services-full-free-breach-tools.md) — breach-correlated identity

---

## 1. THE FIVE COLLECTION LAYERS

Collect in this order — each layer constrains the next.

| Layer | Question | Output |
|---|---|---|
| **1. Organisation** | who are they, how are they structured, what is their tempo? | business units, subsidiaries, acquisitions, hiring signals |
| **2. Identity** | who works there, with what role, contactable how? | names, roles, email format, phone, social presence |
| **3. Infrastructure** | what do they own and expose? | domains, subdomains, IP ranges, ASN, cloud tenancy |
| **4. Technology** | what runs where? | frameworks, CDN/WAF, mail provider, identity provider, SaaS |
| **5. Relationships** | who do they trust? | vendors, partners, contractors, supply chain |

**Layer 5 is the most valuable and most neglected.** An organisation's trust relationships are
its attack surface — a smaller vendor with the same SSO access is a legitimate target, and most
scope conversations never reach them. Identify them and raise them explicitly with the client.

---

## 2. IDENTITY HARVESTING

The goal is a **credential strategy**, not a name list.

| Source | Yields |
|---|---|
| LinkedIn / job boards | names, roles, technologies named in job adverts, reporting structure |
| Email format inference | `first.last@`, `flast@`, `first@` — verify against a known address before spraying |
| Breach corpus lookups | which corporate addresses appeared in past breaches — **a licensing/validity ceiling on current credentials** |
| Code hosting profiles | employee accounts, often with personal repos containing corporate references |
| Certificate transparency | email addresses in cert subjects |
| Conference talks / papers | named individuals and the systems they own |
| Social media | travel, hobbies, and the pretext material for social engineering |
| Metadata in public documents | author names, internal paths, software versions in published PDFs/Office files |

**Email format verification matters.** A spray against the wrong format is a locked-out
account list and a detection event. Infer the format, verify against one confirmed address
(password reset flow reveals existence without revealing the password), then spray.

**Do not treat breach data as a free win.** Old credentials from a decade-old breach are usually
invalid; their value is (a) confirming the email format, (b) password-reuse across the target's
own estate, and (c) building the pattern that generates the next guess.

---

## 3. INFRASTRUCTURE ATTRIBUTION

| Target | Method |
|---|---|
| Root domains | WHOIS, registrar records, MX/SPF/DMARC records |
| Subdomains | certificate transparency logs, passive DNS, search-engine dorks |
| IP ranges | ASN lookup, WHOIS netblocks, reverse DNS |
| Cloud tenancy | storage-bucket naming patterns, app URLs, error pages |
| Mail posture | SPF/DKIM/DMARC — a weak posture is a phishing finding |
| Identity provider | the SSO redirect on any login page names the IdP |
| Third-party services | script/style/asset domains on the public site |
| Historical exposure | archived snapshots for removed pages and deprecated endpoints |

**Passive-first discipline:** certificate transparency and passive DNS give you the subdomain
list with **zero packets to the target**. Exhaust passive sources before active resolution;
the moment you resolve, you appear in their logs.

---

## 4. TECHNOLOGY FINGERPRINTING

| Signal | Reveals |
|---|---|
| Response headers | server, framework, proxy, CDN, WAF |
| Cookie names | framework (session cookie naming is distinctive) |
| Error page format | framework and sometimes version |
| Static asset paths | build tooling, framework, version at build time |
| `robots.txt` / `sitemap.xml` | the paths the owner did not want indexed — often the interesting ones |
| Favicon hash | product identification at scale |
| TLS certificate | issuer, SAN list, expiry, sometimes internal names |
| JavaScript bundle | endpoint list, feature flags, sometimes hardcoded keys |

**The WAF/CDN determination belongs early.** It changes every subsequent decision: rate limits,
payload survival, whether the origin IP is reachable directly, and whether the assessment is
testing the edge or the application.

---

## 5. THE PIVOT — DATA INTO SURFACE

This is the part that separates reconnaissance from note-taking. Each pivot turns one dataset
into the next.

```
domain → subdomains        → attack surface (takeovers, forgotten staging, exposed panels)
subdomains → tech stack    → candidate vulnerability classes
tech stack → CVEs          → specific version checks
people → email format      → credential strategy
email format + breach data → valid credentials
credentials → access       → internal recon begins (SCAFFOLD done)
vendors/partners → trust   → secondary targets for the scope conversation
job adverts → technologies → systems you have not seen yet
```

**Every pivot must terminate in a hypothesis.** "I found 400 subdomains" is not a finding.
"eleven subdomains resolve to a decommissioned SaaS product with an unclaimed CNAME" is.

---

## 6. OPSEC — WHAT YOUR PROBING REVEALS

| Your action | What they see |
|---|---|
| resolving a subdomain | a DNS query from your resolver |
| fetching a page | your IP, user-agent, TLS fingerprint in their logs |
| cert transparency search | nothing — fully passive |
| passive DNS / archive lookup | nothing — fully passive |
| breach API query | nothing to the target |
| social profile view | depending on platform, a view notification |
| **anything from a corporate IP** | **attribution to the client or to you** |

**Use a dedicated infrastructure for reconnaissance, separate from exploitation.** A resolver
that sees both the recon phase and the strike phase ties them together in the target's logs,
which converts a quiet assessment into a detected one.

---

## 7. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the source for every data point | OSINT has no reproducibility without provenance |
| the collection date | domain/infrastructure data changes weekly |
| **which sources were passive vs active** | the client's detection team needs to know what they should have seen |
| the pivots performed | shows the analysis, not just the harvest |
| the infrastructure you used | lets them distinguish your traffic |
| explicitly: what you could NOT determine | bounds the assessment honestly |

---

## 8. REMEDIATION REFERENCE

1. **Reduce the exposed surface** — decommission forgotten subdomains, stage environments in non-public DNS, remove stale records.
2. **Email posture** — strict SPF, DKIM, and DMARC `p=reject` removes the spoofing path and the phishing finding.
3. **Identity exposure** — minimise the employee/role information published and the technologies named in job adverts.
4. **Document metadata hygiene** — strip author and path metadata from published files; it leaks internal naming and structure.
5. **Third-party trust review** — the vendor list is an attack surface; assess vendor access with the same rigour as internal.
6. **Monitor certificate transparency and brand lookalikes** — CT monitoring is free and detects infrastructure you do not own but that impersonates you.

---

## 9. EXECUTION PRIMITIVES

OSINT is only usable if a **lead becomes a verified asset**. Each block below converts a collected
datum into a testable target, and each one records its provenance.

### 9.1 Domain and certificate transparency baseline

```bash
DOMAIN="target.tld"
# certificate transparency: every name ever issued a cert for this domain
curl -sS "https://crt.sh/?q=%25.$DOMAIN&output=json" \
  | python3 -c "import sys,json;[print(n) for e in json.load(sys.stdin) for n in e['name_value'].split(chr(10))]" \
  | sed 's/^\*\.//' | sort -u > ct.txt
wc -l < ct.txt
# whois / registration data for ownership and date range
whois "$DOMAIN" 2>/dev/null | grep -iE 'registrar|creation|expiry|name server|registrant|org'
# DNS records: hosting, mail, and any third-party verification tokens
for T in A AAAA MX TXT NS CNAME SOA CAA; do
  echo "--- $T"; dig +short "$T" "$DOMAIN"
done
```

CT names are **leads, not assets** - wildcard and stale entries frequently resolve nowhere. Verify
each with 9.3 before treating it as surface.

### 9.2 Reverse lookups: infrastructure pivots

```bash
IP=$(dig +short A target.tld | grep -E '^[0-9.]+$' | head -1); echo "ip=$IP"
# other names on the same address - reveals shared hosting vs dedicated, and sibling properties
curl -sS "https://api.hackertarget.com/reverseiplookup/?q=$IP" | head -30
# the ASN and netblock - a pivot to the whole estate
whois -h whois.cymru.com " -v $IP" 2>/dev/null | tail -2
# TLS certificate SANs from the live host: often more names than CT
echo | openssl s_client -connect target.tld:443 -servername target.tld 2>/dev/null \
  | openssl x509 -noout -text | grep -A2 'Subject Alternative Name' | tr ',' '\n' | sed 's/.*DNS://'
```

A shared address with 400 unrelated domains means a shared host, and your finding there is not the
target's. **Always establish ownership** before reporting anything discovered this way.

### 9.3 Verify a lead is live and owned

```bash
while read -r H; do
  [ -z "$H" ] && continue
  A=$(dig +short A "$H" | head -1)
  C=$(curl -sS -o /tmp/p -w '%{http_code}' --max-time 12 "https://$H/" 2>/dev/null)
  T=$(grep -oE '<title>[^<]*' /tmp/p 2>/dev/null | head -1 | cut -c8-)
  printf '%-44s ip=%-16s http=%-4s %s\n' "$H" "${A:-none}" "${C:-timeout}" "$T"
done < ct.txt
```

Rows with an address, a `200`, and a title that matches the target's product are real surface. Rows
with an address but a parking page, or no address at all, are residue - exclude them and say so.

### 9.4 Email and identity correlation (authorized use only)

```bash
# address patterns from published data - never from a breach dump you are not entitled to hold
DOMAIN="target.tld"
for P in info support admin sales hr dev security noreply; do
  MX=$(dig +short MX "$DOMAIN" | head -1)
  echo "$P@$DOMAIN  mx=$MX"
done
# mailbox verification is an active probe: only where the engagement permits it, and slowly
dig +short TXT "$DOMAIN" | grep -iE 'spf|dmarc|dkim|verification|google-site|ms=' 
```

SPF, DMARC, and DKIM records tell you which third parties send mail for the domain - a supply-chain
lead with a named vendor. **Never validate addresses at scale**; that is a mail-bombing risk and is
almost never in scope.

### 9.5 Technology fingerprint with provenance

```bash
curl -sS -D- -o /tmp/h "https://target.tld/" | grep -iE '^(server|x-powered-by|x-generator|via|x-aspnet|x-drupal|cookie|set-cookie|strict-transport|content-security)'
# library versions from the served assets, not from a guess
curl -sS "https://target.tld/" | grep -oE 'src="[^"]+"|href="[^"]+"' | grep -oE '/[^"]+\.(js|css)' | sort -u | head -20
# and the favicon hash, which survives CDN changes and identifies the stack
curl -sS "https://target.tld/favicon.ico" -o /tmp/f.ico && python3 -c "
import codecs,mmh3  # pip install mmh3
print(mmh3.hash(codecs.encode(open('/tmp/f.ico','rb').read(),'base64')))" 2>/dev/null
```

Record the **evidence for each fingerprint** (the header, the file, the hash) - a technology guess
with no provenance becomes a wrong assumption three steps later.

### 9.6 Employee and organisational pivots for social surface

```bash
# published, legitimate sources only: the corporate site, press pages, job ads, and public repos
curl -sS "https://target.tld/careers" | grep -oiE '[a-z0-9._%+-]+@[a-z0-9.-]+' | sort -u | head
# job ads disclose the internal stack and often specific versions
curl -sS "https://target.tld/careers/senior-backend" | grep -oiE '(kubernetes|terraform|jenkins|gitlab|aws|azure|java|node|python)[^.,;<]{0,30}' | sort -u
# public repositories under the org name reveal internal package names (dependency-confusion lead)
curl -sS "https://api.github.com/users/target-org/repos?per_page=100" | grep -oE '"name":\s*"[^"]+"' | head -20
```

Job ads and public repos are the two richest legitimate sources of internal naming. They are
published by the target, so using them is not a boundary crossing.

### 9.7 Build the attribution record

```bash
{
  echo "asset,type,address,evidence,source,verified_utc,owned"
  while read -r H; do
    A=$(dig +short A "$H" | head -1)
    printf '%s,host,%s,DNS A record,dig,%s,true\n' "$H" "${A:-none}" "$(date -u +%FT%TZ)"
  done < ct.txt
} > attribution.csv
column -s, -t attribution.csv | head -20
```

One row per asset, with the **source of every claim**. This file is what turns OSINT into evidence
and what stops an unverified lead from entering a report.

### 9.8 Opsec check on your own probing

```bash
# what does the target see when you collect? resolve your own egress first
curl -sS https://ifconfig.me/ip; echo
curl -sS https://ipinfo.io/json | python3 -c "import sys,json;d=json.load(sys.stdin);print(d.get('org'),d.get('city'),d.get('country'))"
```

Your research ASN, hostname, and location are visible in the target's logs. If the engagement
requires attribution to the engagement rather than to you personally, use the agreed infrastructure -
and never use infrastructure that could be mistaken for a hostile actor.

---

## 10. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Is the asset **owned and controlled by the target**, shown by DNS, TLS, or registration evidence? | third-party and shared-host assets are out of scope |
| 2 | Is each claim backed by a **cited, public source** you can point to? | unsourced OSINT becomes a fabricated finding |
| 3 | Does the datum **change what you can test** (a new host, a named vendor, a stack version)? | otherwise it is background, not a finding |
| 4 | Has the pivot been **verified live** now, not merely listed historically? | CT and archive data include dead entries |
| 5 | Is the disclosure **already public** by the target's own publishing? | published job ads and repos are not a leak |
| 6 | For an exposure claim: does the exposed datum give **access or a specific attack path**? | a job title is not a finding; a vendor endpoint with a default credential is |
| 7 | Was collection **within the engagement's rules** and the rate agreed? | collection without authorization is an incident |

**OSINT is a lead-generation discipline.** A profile alone is rarely a finding; it becomes one when it
names an asset, a version, or a vendor that you then verify. Say explicitly which step turned the
profile into a finding.

---

## 11. EVIDENCE STANDARD — SOURCED ATTRIBUTION

| Item | Why |
|---|---|
| The **source of every claim** (URL, record type, retrieval timestamp) | unsourced attribution is indistinguishable from invention |
| The **ownership evidence** - DNS, TLS server name, registration, or corporate publication | determines whether the asset is even in scope |
| The **live verification** of each lead (address, status, title) | CT and archive data are full of dead entries |
| For an exposure: the **datum and the attack path it enables** | a profile is not a finding; the path is |
| The **collection rate and volume**, within the agreed bounds | OSINT at scale is still traffic against the target or a third party |
| **Negative results you excluded** - dead names, parking pages, third-party hosts | shows rigour and prevents a re-check later |
| The **opsec context** (the egress identity your probing presented) | the target's logs will show it; the report should be consistent with it |
| Confirmation that **no breach data or unlawfully obtained material** was used | using such data invalidates the engagement |
| A statement of what remains **unverified** | honest coverage over a confident-sounding summary |

Report the **verified path**: "the 2023 certificate for `vpn.target.tld` is still live, resolves to the
target's own netblock, and serves a Fortinet SSL-VPN portal at version 7.0.1 (shown by the login page
asset path and the `Server` header); that version maps to a published advisory, which is the testable
lead", never "the target uses Fortinet".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A CT entry for a domain that no longer resolves | historical record, not surface |
| Hostname found on a **shared** address with unrelated tenants | not the target's asset |
| An email address published on the corporate contact page | intended publication |
| Job ads naming the tech stack | the target publishes these deliberately |
| Public repository names | published by definition |
| A named vendor with no reachable, vulnerable endpoint | a supply-chain lead, not a finding |
| WHOIS privacy on a domain the target clearly uses | a privacy service, not a finding |
| An IP in a JS bundle with no reachable service | a hint; verify before reporting |
| A social profile that "seems" to be an employee | attribution error risk; correlation is not identity |
| Breach-dump data of any kind | unlawfully obtained; must not be used or reported |
| Anything derived from scanning a third-party SaaS account you do not own | out of scope and likely illegal |
| A wildcard DNS response making every name "resolve" | a wildcard, not a discovery |

**Cite or drop it.** Every OSINT claim in a report needs a source the reader can open.

---

## 12. REMEDIATION REFERENCE — EXTERNAL EXPOSURE CONTROL

1. **Maintain an authoritative register of your own domains and certificates, and decommission the rest** - most OSINT findings are forgotten assets; a quarterly review that retires old hosts and lets certificates lapse removes the class at the source.
2. **Minimise certificate transparency exposure with wildcards where appropriate** - every specific hostname you issue a certificate for is published permanently, so avoid naming internal services in public CT.
3. **Separate internal and external naming** - do not let internal service names (`jira-internal`, `vpn-staging`) appear in public DNS, certificates, or job ads; naming is the reconnaissance map.
4. **Publish deliberately and audit what you publish** - job ads, documentation, and public repositories should be reviewed for internal hostnames, package names, and version detail before release.
5. **Restrict public metadata on exposed services** - suppress version banners and product-default pages, which turn a hostname into a version into an advisory match.
6. **Use a central publishing review for anything that names infrastructure** - a single checkpoint catches the internal hostname in a job ad or a support article before it becomes an OSINT lead.
7. **Segment and authenticate anything discovered this way** - a VPN portal should require MFA and be patched to a supported version; the finding is often that an internet-exposed admin service is neither.
8. **Monitor for enumeration of your names** - certificate issuance alerts for your domain, DNS query anomalies, and burst access to discovery paths are detectable and give warning.
9. **Provide a `security.txt` and a research contact** - it channels well-intentioned research and reduces the chance that recon work starts from an unverified premise.
10. **Treat vendor relationships as attack surface** - SPF, MX, and third-party verification records name your suppliers; inventory them and know what each can reach in your systems.
11. **Re-verify your own external footprint with the same tools, on a schedule** - the researcher's view of you should be one you have looked at yourself, recently, with the same method.

---

## 13. RELATED SIBLINGS - LOAD TOGETHER

- [recon-and-methodology](../recon-and-methodology/SKILL.md) - the technical discovery phase this profile feeds
- [recon-methodology](../recon-methodology/SKILL.md) - the compact recon companion
- [dorking-recon-engines](../dorking-recon-engines/SKILL.md) - search-engine collection
- [insecure-source-code-management](../insecure-source-code-management/SKILL.md) - where public repositories turn into credentials
- [subdomain-takeover](../subdomain-takeover/SKILL.md) - the highest-impact outcome of a stale DNS lead

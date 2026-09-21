---
name: subdomain-takeover
description: >-
  Subdomain takeover detection and exploitation playbook. Use when targets have
  dangling CNAME/NS/MX records pointing to deprovisioned cloud resources, expired
  third-party services, or unclaimed SaaS tenants that an attacker can register
  to serve content under the victim's domain.
---

# SKILL: Subdomain Takeover — Detection & Exploitation Playbook

> **AI LOAD INSTRUCTION**: Covers CNAME/NS/MX takeover, per-provider fingerprint matching, claim procedures, and defensive monitoring. Base models often confuse "CNAME exists" with "takeover possible" — the key is whether the *resource behind the CNAME is unclaimed and claimable*.

## 0. RELATED ROUTING

- [ssrf-server-side-request-forgery](../ssrf-server-side-request-forgery/SKILL.md) when a subdomain takeover is used to bypass SSRF allowlists trusting `*.target.com`
- [cors-cross-origin-misconfiguration](../cors-cross-origin-misconfiguration/SKILL.md) when CORS trusts `*.target.com` — takeover → full cross-origin read
- [xss-cross-site-scripting](../xss-cross-site-scripting/SKILL.md) takeover gives you script execution under target origin (cookie theft, OAuth redirect abuse)
- [http-host-header-attacks](../http-host-header-attacks/SKILL.md) when Host routing leads to subdomain-scoped cache or auth issues
- [web-cache-deception](../web-cache-deception/SKILL.md) when a taken-over subdomain shares cache with the main domain

---

## 1. CORE CONCEPT

Subdomain takeover occurs when:

1. `sub.target.com` has a DNS record (CNAME, NS, A) pointing to an external service
2. The external resource is **no longer provisioned** (deleted S3 bucket, removed Heroku app, etc.)
3. The attacker can **register/claim** that exact resource name on the provider
4. The attacker now controls content served under `sub.target.com`

**Impact**: cookie theft (parent domain cookies), OAuth token interception, phishing under trusted domain, CORS bypass, CSP bypass via whitelisted subdomain.

---

## 2. DETECTION METHODOLOGY

### 2.1 CNAME Enumeration

```
1. Collect subdomains (amass, subfinder, assetfinder, crt.sh, SecurityTrails)
2. Resolve DNS for each:
   dig CNAME sub.target.com +short
3. For each CNAME → check if the CNAME target returns NXDOMAIN or a provider error
4. Match error response against fingerprint table (Section 3)
```

### 2.2 Key Signals

| Signal | Meaning |
|---|---|
| CNAME → `xxx.s3.amazonaws.com` + HTTP 404 "NoSuchBucket" | S3 bucket deleted, claimable |
| CNAME → `xxx.herokuapp.com` + "No such app" | Heroku app deleted |
| CNAME → `xxx.github.io` + 404 "There isn't a GitHub Pages site here" | GitHub Pages unclaimed |
| NXDOMAIN on the CNAME target domain itself | Target domain expired or never existed |
| CNAME → provider but HTTP 200 with default parking page | May or may not be claimable — verify |

### 2.3 Automated Tools

| Tool | Purpose |
|---|---|
| `subjack` | Automated CNAME takeover checking |
| `nuclei -t takeovers/` | Nuclei takeover detection templates |
| `can-i-take-over-xyz` (GitHub) | Reference for which services are vulnerable |
| `dnsreaper` | Multi-provider takeover scanner |
| `subzy` | Fast subdomain takeover verification |

---

## 3. SERVICE PROVIDER FINGERPRINT TABLE

| Provider | CNAME Pattern | Fingerprint (HTTP Response) | Claimable? |
|---|---|---|---|
| **AWS S3** | `*.s3.amazonaws.com` / `*.s3-website-*.amazonaws.com` | `NoSuchBucket` (404) | Yes — create bucket with matching name |
| **GitHub Pages** | `*.github.io` | `There isn't a GitHub Pages site here` (404) | Yes — create repo + enable Pages |
| **Heroku** | `*.herokuapp.com` / `*.herokudns.com` | `No such app` | Yes — create app with matching name |
| **Azure** | `*.azurewebsites.net` / `*.cloudapp.azure.com` / `*.trafficmanager.net` | Various default pages, NXDOMAIN | Yes — register matching resource |
| **Shopify** | `*.myshopify.com` | `Sorry, this shop is currently unavailable` | Yes — create shop, add custom domain |
| **Fastly** | CNAME to Fastly edge | `Fastly error: unknown domain` | Yes — add domain to Fastly service |
| **Pantheon** | `*.pantheonsite.io` | `404 Site Not Found` with Pantheon branding | Yes |
| **Tumblr** | `*.tumblr.com` (custom domain CNAME) | `There's nothing here` / `Whatever you were looking for doesn't exist` | Yes |
| **WordPress.com** | CNAME to `*.wordpress.com` | `Do you want to register` | Yes — claim domain in WP.com |
| **Zendesk** | `*.zendesk.com` | `Help Center Closed` / Zendesk branding on error | Yes — create matching subdomain |
| **Unbounce** | `*.unbouncepages.com` | `The requested URL was not found` | Yes |
| **Ghost** | `*.ghost.io` | `404 Not Found` Ghost error | Yes |
| **Surge.sh** | `*.surge.sh` | `project not found` | Yes |
| **Fly.io** | CNAME to `*.fly.dev` | Fly.io default 404 | Yes |

---

## 4. TAKEOVER PROCEDURE — COMMON PROVIDERS

### 4.1 AWS S3

```
1. Confirm: curl -s http://sub.target.com → "NoSuchBucket"
2. Extract bucket name from CNAME (e.g., sub.target.com.s3.amazonaws.com → bucket = "sub.target.com")
3. aws s3 mb s3://sub.target.com --region <region>
4. Upload index.html proving control
5. Enable static website hosting
```

### 4.2 GitHub Pages

```
1. Confirm: curl -s https://sub.target.com → "There isn't a GitHub Pages site here"
2. Create GitHub repo (any name)
3. Add CNAME file containing "sub.target.com"
4. Enable GitHub Pages in repo settings
5. Wait for DNS propagation (GitHub verifies CNAME match)
```

### 4.3 Heroku

```
1. Confirm: curl -s http://sub.target.com → "No such app"
2. heroku create <app-name-from-cname>
3. heroku domains:add sub.target.com
4. Deploy proof-of-concept page
```

---

## 5. NS TAKEOVER — HIGH SEVERITY

NS takeover is **far more dangerous** than CNAME takeover: you control **all DNS resolution** for the zone.

### How It Happens

```
target.com NS → ns1.expireddomain.com
                 ↓
attacker registers expireddomain.com
                 ↓
attacker now controls ALL DNS for target.com
(A records, MX records, TXT records — everything)
```

### Detection

```
1. Enumerate NS records: dig NS target.com +short
2. Check each NS domain: whois ns1.example.com → is the domain expired or available?
3. Also check: dig A ns1.example.com → NXDOMAIN/SERVFAIL?
4. Subdelegated zones: check NS for sub.target.com specifically
```

### Impact

- Full domain takeover (serve any content, intercept email, issue TLS certs via DNS-01)
- Issue DV certificates from any CA using DNS challenge
- Modify SPF/DKIM/DMARC → send authenticated email as target

---

## 6. MX TAKEOVER — EMAIL INTERCEPTION

When MX records point to deprovisioned mail services:

```
target.com MX → mail.deadservice.com (service discontinued)
```

If attacker can claim `mail.deadservice.com` or the mail tenant:
- Receive password reset emails
- Intercept sensitive communications
- Potentially reset accounts that use email-based auth

### Common Scenario

Expired Google Workspace / Microsoft 365 tenant → MX still points to Google/Microsoft → attacker creates new tenant and claims the domain.

---

## 7. WILDCARD DNS RISKS

If `*.target.com` has a wildcard CNAME to a claimable service:
- **Every** undefined subdomain is vulnerable
- `anything.target.com` can be taken over
- Massively increases attack surface

Detection: `dig A random1234567.target.com` — if it resolves, wildcard exists.

---

## 8. DETECTION & EXPLOITATION DECISION TREE

```
Subdomain discovered (sub.target.com)?
├── Resolve DNS records
│   ├── Has CNAME → external service?
│   │   ├── HTTP response matches known fingerprint? (Section 3)
│   │   │   ├── YES → Attempt claim on provider (Section 4)
│   │   │   │   ├── Claim successful → TAKEOVER CONFIRMED
│   │   │   │   └── Claim blocked (name reserved, region locked) → document, try variations
│   │   │   └── NO → Service active, no takeover
│   │   └── CNAME target NXDOMAIN?
│   │       ├── Target is a registrable domain? → Register it → full control
│   │       └── Target is a subdomain of active provider → check provider claim process
│   │
│   ├── Has NS records → external nameserver?
│   │   ├── NS domain expired/available? → Register → FULL ZONE TAKEOVER
│   │   └── NS domain active → no takeover
│   │
│   ├── Has MX → external mail service?
│   │   ├── Mail service deprovisioned/claimable? → Claim tenant → EMAIL INTERCEPTION
│   │   └── Active mail service → no takeover
│   │
│   └── Has A record → IP address?
│       ├── IP belongs to elastic cloud (AWS EIP, Azure, GCP)?
│       │   ├── IP unassigned? → Claim IP → serve content
│       │   └── IP assigned to another customer → no takeover
│       └── IP belongs to dedicated server → no takeover
│
└── Post-takeover impact assessment
    ├── Shared cookies with parent domain? → Session hijacking
    ├── CORS trusts *.target.com? → Cross-origin data theft
    ├── CSP whitelists *.target.com? → XSS via taken-over subdomain
    ├── OAuth redirect_uri allows sub.target.com? → Token theft
    └── Can issue TLS cert for sub.target.com? → Full MITM
```

---

## 9. DEFENSE & REMEDIATION

| Action | Priority |
|---|---|
| Remove DNS records when deprovisioning cloud resources | Critical |
| Monitor CNAME targets for NXDOMAIN responses | High |
| Use DNS monitoring tools (SecurityTrails, DNSHistory) | High |
| Claim/reserve resource names before deleting DNS records | High |
| Audit NS delegations — ensure NS domains are owned and renewed | Critical |
| Avoid wildcard CNAMEs to third-party services | Medium |
| Implement Certificate Transparency monitoring | Medium |

---

## 10. TRICK NOTES — WHAT AI MODELS MISS

1. **CNAME ≠ takeover**: A CNAME to S3 that returns 403 (bucket exists, private) is NOT vulnerable. Only `NoSuchBucket` (404) is.
2. **Region matters for S3**: Bucket names are global, but website endpoints are regional. Try matching the region from the CNAME.
3. **GitHub Pages verification**: GitHub added domain verification — org-verified domains cannot be claimed by others. Check if target uses this.
4. **Edge cases**: Some providers (e.g., Cloudfront) require specific distribution configuration, not just domain claiming.
5. **Second-order takeover**: `sub.target.com CNAME → other.target.com CNAME → dead-service.com` — the chain must be followed fully.
6. **SPF subdomain takeover**: If SPF includes `include:sub.target.com` and you take over `sub.target.com`, you can modify its SPF TXT record to authorize your mail server → send spoofed email as `target.com`.

---

## 11. EXECUTION PRIMITIVES

Subdomain takeover is proven by **serving your own content from a hostname you do not own**, and
nothing less. The dangling record plus a controlled response from the provider is the evidence.

### 11.1 Enumerate the candidates

```bash
D="target.tld"
# every CNAME and its target
for SUB in $(cat subs.txt); do
  C=$(dig +short CNAME "$SUB.$D")
  [ -n "$C" ] && printf '%-40s CNAME %s\n' "$SUB.$D" "$C"
done
# and the records that point at providers but have no address
for SUB in $(cat subs.txt); do
  A=$(dig +short A "$SUB.$D")
  C=$(dig +short CNAME "$SUB.$D")
  if [ -z "$A" ] && [ -n "$C" ]; then printf '%-40s -> %s  (NO A RECORD)\n' "$SUB.$D" "$C"; fi
done
```

The signal is a **CNAME to a third-party service with no resolving address, or resolving to the
provider's generic "not found" page**. Both indicate a claimed-but-unowned name.

### 11.2 Confirm the takeover is available, per provider

```bash
for SUB in dangling1 dangling2 dangling3; do
  H="$SUB.target.tld"
  echo "════ $H"
  echo "-- DNS";      dig +short CNAME "$H"; dig +short A "$H"
  echo "-- HTTP";     curl -sS -o /tmp/st -D /tmp/sh -w '  code=%{http_code} size=%{size_download}\n' "http://$H/"
  echo "-- headers";  grep -iE 'server:|x-|via|cf-|x-amz|x-github|x-heroku|x-vercel' /tmp/sh | head -6
  echo "-- body fingerprint"
  grep -oiE 'no such app|not found|404|heroku|github|netlify|vercel|s3|azure|fastly|unclaimed|repo not found|project not found' /tmp/st | sort -u | head -5
done
```

Each provider has a **distinctive unclaimed-resource page**. Match the fingerprint against the provider
table before attempting a claim - the page text is the first piece of evidence.

### 11.3 Test the claim without actually taking it over

```bash
# for object-storage targets, a read of the bucket's status proves it is unclaimed without registering
aws s3api head-bucket --bucket dangling-bucket-name 2>&1 | head -3
curl -sS -o /tmp/s3 -w 's3 status=%{http_code}\n' "https://dangling-bucket-name.s3.amazonaws.com/"
grep -oiE 'NoSuchBucket|AccessDenied|ListBucketResult' /tmp/s3
# for GitHub Pages, the repository's existence is public information
curl -sS -o /dev/null -w 'github repo status=%{http_code}\n' "https://api.github.com/repos/ORG/dangling-repo"
```

**A `NoSuchBucket` or a `404` on the repository is the strongest pre-takeover proof** and it involves no
action on the provider. This is the responsible first step, and it is often sufficient.

### 11.4 Claiming, when the engagement explicitly permits it

```bash
# ONLY with written authorization for the specific hostname.
# the claim is a provider-specific registration of the exact name the CNAME points at.
# after claiming, serve a non-destructive marker:
printf 'takeover-marker-%s' "$(date +%s)" > index.html
python3 -m http.server 80 &
sleep 1
curl -sS "http://dangling.target.tld/" | head -c 120
echo
echo "record the timestamp and the marker; do not upload anything else, and release it after the test"
```

A takeover marker must be **inert** - a static string. Never serve a payload, never collect traffic,
and release the name immediately after documenting it. Many engagements require authorization for this
specific step, so confirm it is in scope before claiming.

### 11.5 NS and MX takeover - the high-severity variants

```bash
# a delegation to a nameserver that no longer exists lets you answer for the whole zone
dig +short NS sub.target.tld
for NS in $(dig +short NS sub.target.tld); do
  echo "--- $NS"
  dig +short A "$NS"          # no address means the delegation is dangling
  dig +time=3 +tries=1 @"$NS" SOA sub.target.tld 2>&1 | head -3
done
# an MX pointing at a provider host that is claimable
dig +short MX target.tld
for M in $(dig +short MX target.tld | awk '{print $2}'); do
  echo "$M -> $(dig +short CNAME "$M") / $(dig +short A "$M" | tr '\n' ' ')"
done
```

A **dangling NS delegation is the highest-severity form**: if you can register the nameserver name, you
control every record in the subzone, including the certificates' validation path. An MX to a claimable
provider host enables mail interception. **Prove the dangling state with the queries**, and coordinate
before any registration.

### 11.6 Certificate transparency as corroboration

```bash
# certificates issued to a hostname prove who has actually served it
curl -sS "https://crt.sh/?q=%25.target.tld&output=json" | python3 -c "
import json,sys
for e in json.load(sys.stdin):
    print(e.get('name_value','').replace(chr(10),','), e.get('issuer_name','')[:50], e.get('not_before','')[:10])
" | sort -u | head -20
```

A hostname with **old certificates and no current answer** is a strong takeover candidate: it was once
served, and now nothing claims it. Corroborate the finding with the certificate history.

### 11.7 Verify from an independent vantage point

```bash
# confirm the DNS state from a public resolver and over a different network path
dig +short @1.1.1.1 dangling.target.tld
dig +short @8.8.8.8 dangling.target.tld
dig +short @9.9.9.9 dangling.target.tld
# and the HTTP response without any local proxy or hosts entry
curl -sS --noproxy '*' -o /tmp/v -w '%{http_code} %{remote_ip}\n' "http://dangling.target.tld/"
head -c 200 /tmp/v
```

Resolvers disagree when a zone is mid-change, and a local `/etc/hosts` entry or proxy can falsify the
result. **Confirm from at least two public resolvers** before reporting.

### 11.8 The provider fingerprint table in practice

```bash
# map the target hostname to the provider by its CNAME suffix, then request the unclaimed page
declare -A SUF=(
 [s3.amazonaws.com]="AWS S3"
 [cloudfront.net]="CloudFront"
 [herokuapp.com]="Heroku"
 [github.io]="GitHub Pages"
 [azurewebsites.net]="Azure App Service"
 [cloudapp.azure.com]="Azure VM"
 [trafficmanager.net]="Azure Traffic Manager"
 [netlify.app]="Netlify"
 [vercel.app]="Vercel"
 [fastly.net]="Fastly"
 [wpengine.com]="WP Engine"
 [pantheonsite.io]="Pantheon"
 [surge.sh]="Surge"
 [readthedocs.io]="Read the Docs"
 [zendesk.com]="Zendesk"
)
for H in dangling1.target.tld dangling2.target.tld; do
  C=$(dig +short CNAME "$H" | head -1)
  for K in "${!SUF[@]}"; do
    case "$C" in *"$K") echo "$H -> ${SUF[$K]} (via $C)";; esac
  done
done
```

**The provider determines the claim procedure and the exact unclaimed-page text.** Identify it by the
CNAME suffix, then confirm with the page fingerprint - do not guess from the page text alone.

---

## 12. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Does a **CNAME or delegation point at a third party** that no longer serves the resource? | the dangling pointer |
| 2 | Does the provider return its **unclaimed-resource page** or a `NoSuchBucket`-class error? | the resource is free to claim |
| 3 | Did you establish the provider's **claim path** without performing the claim? | reproducibility without acting on the provider |
| 4 | If you claimed it, did **your marker serve from the hostname**? | the takeover, in its strongest form |
| 5 | Is the hostname's **cookie or origin scope** under the parent domain? | severity: cookie theft or origin trust |
| 6 | Is it an **NS or MX** delegation rather than a simple CNAME? | the high-severity variants |
| 7 | Does the DNS state reproduce from **two public resolvers**? | rules out local interference |

**Your content on their hostname is the bar.** A dangling CNAME plus a provider 404 is strong evidence;
a served marker is proof. Report precisely which of the two you have.

---

## 13. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **DNS record** - the CNAME, NS, or MX, shown with `dig` output and the resolver used | the dangling pointer is the root cause |
| The **provider's unclaimed response** - the status, headers, and page fingerprint | proves the resource is claimable |
| The **provider identity**, matched to the CNAME suffix and the fingerprint | determines the claim path and the fix |
| Where claimed, the **marker served from the hostname**, with a timestamp and the request log | the takeover, proved |
| The **scope impact** - whether the hostname shares cookies or is in a CORS/redirect allowlist | severity |
| **Corroboration from certificate transparency** - past certificates with no current server | shows the host once existed and is now free |
| The **resolver behaviour** - two public resolvers agreeing | rules out local DNS interference |
| **Negative control** - a hostname whose CNAME target still serves its resource shows a different page | shows the unclaimed fingerprint is specific |
| Confirmation that the claim was **authorized**, and that the resource was **released** afterwards | scope and ethics discipline |
| A statement that **no traffic was collected and no payload was served** | scope discipline |

Report the **record, the provider state, and the impact**: "`status.target.tld` is a CNAME to
`target-status.herokuapp.com`; the hostname returns Heroku's "No such app" page and resolves to
Heroku's shared address with no A record of its own, and the app name is unregistered, so the hostname
can be claimed by anyone; because the cookie scope is `.target.tld`, a takeover would allow session
cookie theft for the parent domain; the state reproduces from 1.1.1.1 and 8.8.8.8", never
"the subdomain is vulnerable to takeover".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A CNAME to a provider that still serves a live resource | nothing is dangling |
| A generic provider page on a hostname the provider still owns | the name is claimed |
| A wildcard DNS record answering for every name | not a takeover |
| A `404` from the target's own server | the target owns and serves the name |
| A hostname with no DNS records at all | nothing to take over |
| A worker or load balancer that answers with a default page for unknown hosts | the name is claimed by the platform |
| A takeover you demonstrated on your own test domain | tests your own setup |
| A dangling record where the provider registration requires verification of the parent domain | the claim path is closed |
| A state you only observed once, from one resolver | could be propagation |
| A hostname outside the agreed scope | scope violation |
| A claim you performed without authorization | an incident |
| A takeover that serves traffic or collects data | an incident |

**Prove the resource is unclaimed without claiming it where possible.** The `NoSuchBucket`-style check
is usually sufficient and is always preferable.

---

## 14. REMEDIATION REFERENCE

1. **Remove the DNS record when the service is decommissioned** - the fix is process discipline, and an automated reconciliation between DNS records and live services is the control that prevents the whole class.
2. **Maintain an inventory of every hostname that delegates to a third party, with an owner** - takeover findings are almost always a record nobody remembered owning, so the inventory is the primary control.
3. **Monitor for dangling records continuously, and alert on CNAMEs that stop resolving** - the condition is detectable the moment it appears, so detection is cheap and effective.
4. **Verify domain ownership with the provider before it lapses** - reserving the name, keeping the account active, or adding a provider-side verification record prevents an unclaimed-resource state entirely.
5. **Re-check every record before and after a decommission, in both directions** - the record and the service must be removed together, in a defined order, by one owner.
6. **Restrict who can create DNS records, and require a purpose for each** - an unreviewed record is the precondition, so a reviewed change process removes it.
7. **Avoid wildcard DNS where it is not needed, and understand its takeover interaction** - a wildcard masks dangling names and makes enumeration harder, which is a risk in itself.
8. **Scope cookies to the specific hostname rather than the parent domain where feasible** - this limits the session-theft impact of any subdomain compromise, not just a takeover.
9. **Do not include wildcard origins or unverified subdomains in CORS and redirect allowlists** - these lists are what turn a takeover into a cross-domain compromise.
10. **Use certificate transparency monitoring to detect unexpected issuance** - an attacker who takes over a subdomain can obtain a certificate, so CT monitoring is a detection layer for the post-takeover phase.
11. **For NS delegations, treat the delegated zone with the same rigour as the parent** - a dangling delegation is the highest-severity form, and it is also the easiest to overlook.

---

## 15. RELATED SIBLINGS - LOAD TOGETHER

- [recon-and-methodology](../recon-and-methodology/SKILL.md) - the enumeration that finds the candidates
- [dns-rebinding-attacks](../dns-rebinding-attacks/SKILL.md) - the other DNS-level trust failure
- [cors-cross-origin-misconfiguration](../cors-cross-origin-misconfiguration/SKILL.md) - the allowlist that turns a takeover into cross-origin access
- [api-recon-and-docs](../api-recon-and-docs/SKILL.md) - the API surface a taken-over hostname exposes
- [cloud-assessment](../cloud-assessment/SKILL.md) - the cloud-side review that finds dangling resources

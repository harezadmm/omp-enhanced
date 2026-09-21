---
name: attack-subdomain-takeover
description: "Subdomain takeover — dangling DNS records, unclaimed cloud resources, and the hijack chain"
category: "web-application"
version: "1.1"
author: "cyberstrike-official"
tags:
  - dns
  - takeover
  - recon
  - cloud
  - attack
tech_stack:
  - dns
  - aws
  - azure
  - github
cwe_ids:
  - CWE-350
chains_with:
  - attack-cors
  - attack-host-header
prerequisites: []
severity_boost:
  attack-cors: "Taken-over subdomain plus a *.target.com CORS wildcard = credentialed cross-origin read"
  attack-host-header: "Taken-over subdomain plus host-header trust = password-reset link poisoning"
---

# Subdomain Takeover

> **AI LOAD INSTRUCTION**: A subdomain takeover is not "a DNS record points somewhere odd." It
> is proven when **you control content served at a hostname that belongs to the target's
> domain.** The decisive test is claiming the resource and showing your own content at
> `https://sub.target.com` — nothing short of that is a finding. A dangling `CNAME` pointing
> at a deprovisioned service is a *candidate*; the finding requires the claim to succeed.
>
> The reason these matter beyond the subdomain itself is **cookie scope and origin trust**. A
> hostname under `target.com` inherits the target's cookies if they are scoped to the parent
> domain, is trusted by any CORS wildcard on `*.target.com`, and passes host-header
> validation. That is why a "low-value" leftover subdomain is frequently critical.
>
> **Never claim a resource you do not intend to hold**, and never serve content that could
> harm the target's users. Prove the claim with a static marker, screenshot it, and report it.

## 0. RELATED ROUTING

- [subdomain-takeover](../subdomain-takeover/SKILL.md) — the long-form companion; load alongside this file
- [recon-methodology](../recon-methodology/SKILL.md) — producing the subdomain inventory
- [attack-cors](../attack-cors/SKILL.md) — the escalation that makes a low-value subdomain critical
- [attack-host-header](../attack-host-header/SKILL.md) — the other trust relationship a takeover abuses
- [attack-open-redirect](../attack-open-redirect/SKILL.md) — the chaining primitive
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — reporting with a held claim, safely

---

## 1. BUILDING THE INVENTORY

You cannot find a takeover without a candidate list. Build it from DNS, not from guessing.

**Sources, in order of yield:**

| Source | What it gives |
|---|---|
| certificate transparency logs | every hostname ever issued a cert — **the best source** |
| DNS brute force | current, live records |
| passive DNS datasets | historical records no longer resolving |
| the target's own JS bundles and sitemaps | internal hostnames the app references |
| search engines | indexed subdomains from old content |
| GitHub / repo configs | CI and deployment configs naming hosts |
| SPF/DMARC records | hosts listed in mail configuration |
| the target's mobile app | hardcoded API hostnames |

**Certificate transparency is the highest-yield passive source** because it captures hostnames
that existed even briefly and no longer resolve — which is exactly the takeover candidate
profile:

```bash
# crt.sh JSON query (replace the domain)
curl -s "https://crt.sh/?q=%25.target.com&output=json" | jq -r '.[].name_value' | \
  sed 's/\*\.//g' | sort -u

# Subfinder / assetfinder style enumeration if available
subfinder -d target.com -silent | sort -u
```

**Collect historical records too.** A hostname that resolved last year and does not resolve now
is more suspicious than one that resolves today, because the service may have been
deprovisioned while the DNS record was left behind.

---

## 2. IDENTIFYING DANGLING RECORDS

**Step 1 — resolve everything and record CNAME chains.** The CNAME target names the hosting
provider, which determines whether the resource can be claimed:

```bash
for sub in $(cat subdomains.txt); do
  cname=$(dig +short CNAME "$sub" | head -1)
  ip=$(dig +short A "$sub" | head -1)
  printf "%-40s CNAME=%-50s A=%s\n" "$sub" "${cname:-none}" "${ip:-none}"
done
```

**Step 2 — recognise the error signatures.** A dangling record produces a provider-specific
"not found" page. The exact string is the signal:

| Provider | CNAME target pattern | Error signature |
|---|---|---|
| GitHub Pages | `*.github.io` | "There isn't a GitHub Pages site here." |
| AWS S3 | `*.s3.amazonaws.com`, `*.s3-website-*.amazonaws.com` | "NoSuchBucket" |
| Heroku | `*.herokuapp.com` | "No such app" |
| Netlify | `*.netlify.app` | "Not Found - Request ID:" |
| Vercel | `*.vercel.app` | `DEPLOYMENT_NOT_FOUND` |
| Azure | `*.azurewebsites.net`, `*.cloudapp.azure.com` | "Error 404 - Web app not found" |
| Shopify | `*.myshopify.com` | "Sorry, this shop is currently unavailable." |
| Fastly | `*.fastly.net` | "Fastly error: unknown domain" |
| Pantheon | `*.pantheonsite.io` | "The gods are wise, but do not know of the site" |
| Tumblr | `*.tumblr.com` | "Whatever you were looking for doesn't currently exist" |
| Zendesk | `*.zendesk.com` | "Help Center Closed" |
| Read the Docs | `*.readthedocs.io` | "unknown to Read the Docs" |
| Surge | `*.surge.sh` | "project not found" |
| WordPress | `*.wordpress.com` | "doesn't exist" |
| Bitbucket | `*.bitbucket.io` | "Repository not found" |

**The error page itself is the candidate marker.** Record the exact string verbatim — it is
your evidence that the resource is unclaimed.

**Step 3 — distinguish the cases:**

| Observation | Meaning |
|---|---|
| CNAME to a provider, provider returns "not found" | **strong candidate** |
| CNAME to a provider, provider serves *their* generic page | candidate — check whether it is claimable |
| CNAME to a provider, provider serves the target's content | live, not vulnerable |
| `NXDOMAIN` on the subdomain | dead record — no takeover surface |
| CNAME to another domain of the target | internal, not vulnerable |
| A record to a provider IP, no CNAME | harder; possible with elastic IPs |

**Only the first two are candidates.** Do not report `NXDOMAIN` — there is nothing to claim.

---

## 3. PROVING THE CLAIM

**The finding is the claim.** A dangling record is a hypothesis; controlling the hostname is
the proof.

**The general shape, per provider:**

| Provider | Claim method |
|---|---|
| GitHub Pages | create a repo, add the hostname as a custom domain, commit a `CNAME` file |
| AWS S3 | create a bucket **with the exact subdomain as its name** |
| Heroku | `heroku create <appname>` matching the dangling app name |
| Netlify / Vercel | add the domain to a new project |
| Azure | create an App Service with the matching name |
| Shopify | create a store and add the domain |
| Fastly | create a service and add the domain |

**Critical detail: the resource name must match exactly.** A CNAME to `target-assets.s3.
amazonaws.com` requires a bucket named `target-assets`. If that name is taken, the takeover is
not possible — record that and move on.

**Proof-of-claim procedure — do this carefully:**

1. Claim the resource.
2. Serve a **static, inert page** containing a unique token and a timestamp:
   ```html
   <!doctype html><title>Takeover proof</title>
   <p>Subdomain takeover proof — token &lt;engagement-token&gt; — <time>&lt;utc-timestamp&gt;</time></p>
   ```
3. Screenshot `https://sub.target.com` showing the token.
4. Record the HTTP response headers showing `sub.target.com` in the `server`/`via` chain.
5. **Report immediately and release the claim** once the target confirms.

**Never serve anything active.** No JavaScript, no redirects, no credential capture, no
fingerprinting of visitors. A takeover you use to collect user data converts a clean finding
into a criminal act.

**If the claim is not possible, say so.** "Dangling CNAME to a deprovisioned Heroku app; the
app name is already re-registered by a third party; not currently claimable" is an honest and
still-useful report — it documents a latent risk.

---

## 4. ESCALATION — WHY THE SUBDOMAIN MATTERS

A takeover of `static-assets.target.com` is low on its own. These are the chains that make it
critical.

| Chain | Mechanism |
|---|---|
| **Cookie scope** | if session cookies are `Domain=.target.com`, the taken-over host can **set cookies the main app reads** — session fixation |
| **CORS wildcard** | a policy trusting `*.target.com` now trusts an attacker origin — credentialed cross-origin read |
| **Host-header trust** | the app may accept the taken-over host as a valid `Host`, enabling reset-link poisoning |
| **OAuth redirect** | if the subdomain is a registered `redirect_uri`, authorization codes can be redirected to you |
| **CSP allowance** | if the subdomain appears in a `script-src` allowlist, you can inject script into the main app |
| **Email trust** | a subdomain in the SPF record can send mail as the domain |
| **Trusted-origin checks** | applications that whitelist their own subdomains for privileged actions |
| **VPN / SSO** | a takeover of an SSO-adjacent hostname can capture credentials |

**Test the highest-impact chain you can safely verify.** Reading the main app's `Set-Cookie`
for a `Domain=.target.com` attribute is passive and safe. Demonstrating cookie injection
against a real user is not — describe the mechanism and stop.

**Wildcard CORS is the most common critical escalation.** Check whether the main API returns
`Access-Control-Allow-Origin` reflecting any `*.target.com` origin — see [attack-cors](../attack-cors/SKILL.md).

---

## 5. WHAT CONSTITUTES A FINDING

| Finding | Severity | Proof required |
|---|---|---|
| Takeover claimed, hostname in a `redirect_uri` or CSP allowlist | **Critical (P1)** | the claim plus the referencing configuration |
| Takeover claimed, cookies scoped to the parent domain | **Critical (P1)** | the claim plus the `Set-Cookie` domain attribute |
| Takeover claimed, CORS wildcard trusts `*.target.com` | **High–Critical (P1/P2)** | the claim plus the reflected origin |
| Takeover claimed, no elevated trust found | **Medium (P3)** | the claim and the inert proof page |
| Dangling CNAME confirmed, resource already claimed by another | **Low (P4)** | the dangling record and the third-party claim |
| Dangling CNAME, not yet claimable by anyone | **Medium (P3)** | the record and the error signature |
| `NXDOMAIN` subdomain | **Not a finding** | nothing to take over |
| CNAME to a provider serving the target's live content | **Not a finding** | the resource is claimed |

---

## 6. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the subdomain and the full CNAME chain | the dangling record |
| the provider's error response, verbatim | proves the resource is unclaimed |
| the claim action performed (bucket created, repo configured) | proves you claimed it |
| a screenshot of `https://sub.target.com` with your inert token | **the proof of control** |
| the timestamp of the proof | establishes the window; you release it after |
| for escalation: the referencing configuration (CORS header, cookie attribute, CSP entry) | converts a medium into a critical |
| confirmation that you released the claim | shows responsible handling |
| a **control**: a correctly configured sibling subdomain | proves the dangling one is anomalous |

**The screenshot with your token is the finding.** Everything else supports it.

**False positives to exclude:**

| Looks like a takeover | Actually |
|---|---|
| the provider serves its own default page but the name is taken | not claimable |
| `NXDOMAIN` | nothing to claim |
| the CNAME points to another target-owned hostname | internal, not dangling |
| the provider error is generic and appears for all hosts | check whether a valid host shows a different page |
| you claimed it but the hostname does not resolve to your content | the DNS is not actually pointing at your resource |
| the subdomain is intentionally decommissioned and pending deletion | report as latent, not active |

---

## 7. REMEDIATION REFERENCE

1. **Delete DNS records when you deprovision a service** — make decommissioning a checklist step that includes the DNS record, not just the cloud resource.
2. **Hold the resource name** — when a service is retired but the hostname is still referenced, keep the underlying bucket/app registered and empty. An occupied name cannot be claimed.
3. **Inventory every CNAME and its target, continuously** — an automated job that resolves each subdomain and alerts when a target stops serving the expected content catches these before an attacker does.
4. **Register the resource name before pointing DNS at it** — the reverse order creates the window.
5. **Scope session cookies to the exact host** — avoid `Domain=.example.com`; this is what turns a low-value subdomain into account takeover.
6. **Never use wildcard CORS for `*.yourdomain`** — enumerate the origins that genuinely need it. A wildcard means any future takeover is immediate critical.
7. **Do not allowlist subdomains in CSP `script-src`** — list exact hosts, and review the list when any host is retired.
8. **Verify `redirect_uri` registrations against your live hostname inventory** — remove entries for hosts that no longer serve content.
9. **Monitor certificate transparency for your own domain** — a new certificate for a subdomain you do not recognise is an early indicator.

---

## 8. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did **YOUR content get served** at the dangling name, in a browser? | control of the name, not just a DNS state |
| 2 | Was there a **control** - a healthy sibling subdomain that serves the real app? | the difference is the takeover |
| 3 | Did the DNS record **point at a service you could claim**, and did you claim it? | the mechanism |
| 4 | Did the claim require **no prior ownership proof**? | the service's defect, and the fix |
| 5 | Is the parent domain **in scope and trusted** (cookies, CORS, CSP, e-mail)? | the severity |
| 6 | Did you **check for a certificate**, which may make the takeover more or less dangerous? | the exploitability |
| 7 | Did you **claim only one name**, and did you **not disrupt** the service? | engagement integrity |

**Your content served at the dangling name is the bar.** An `NXDOMAIN`, a `404`, or a CNAME pointing at a
dead service is a candidate; a token page of yours being served is the finding.

---

## 9. EXECUTION PRIMITIVES

Subdomain takeover is proven by **a page you control being served at the target's name, with the DNS
record quoted and a healthy-subdomain control**. Every block ends at your content on their name.

### 9.1 The DNS evidence and the fingerprint

```bash
S="dev.target.example"; GOOD="app.target.example"
# the record chain, which is the primary evidence
dig +short CNAME "$S"; dig +short A "$S"; dig +short NS "$S"
echo "--- and the control: a healthy subdomain, which resolves to the real service ---"
dig +short CNAME "$GOOD"; dig +short A "$GOOD"
# the response, which carries the service's fingerprint
curl -sS -D- -o /tmp/tk.html "http://$S/" 2>&1 | head -8
echo "--- THE FINGERPRINT: the body usually names the unclaimed service ---"
grep -oiE '(github pages|heroku|s3|amazonaws|azure|cloudapp|trafficmanager|fastly|netlify|surge|bitbucket|shopify|wordpress|zendesk|readme|statuspage|pantheon|unbounce|tumblr|desk|teamwork|helpjuice|helpscout|cargo|feedpress|ghost|freshdesk|pingdom|surveygizmo|smartling|uservoice|wpengine|agilecrm|canny|launchrock|getresponse|hatena|tictail)' /tmp/tk.html | sort -u
head -c 400 /tmp/tk.html; echo
echo "--- and whether it is a wildcard, which changes the exploitability ---"
dig +short "$(head -c8 /dev/urandom | base64 | tr -d '/+=' | head -c8).$S"
```

**The fingerprint is what names the claimable service.** The body's error string identifies the provider,
and the provider's own message is the most reliable identifier.

### 9.2 The claim, with an ownership token

```bash
# STEP 1 - claim the name at the provider, in YOUR account, with a token page
# (each provider has its own claim flow - the exact clicks are not reproduced here, the STATE is)
cat > index.html <<'HTML'
<!doctype html><html><head><title>takeover-proof</title></head><body>
<h1>Subdomain takeover proof</h1>
<p>domain: dev.target.example</p>
<p>claimed by: &lt;engagement id&gt; at <span id="t"></span></p>
<script>document.getElementById('t').textContent = new Date().toISOString();</script>
</body></html>
HTML
echo 'verification token: <engagement-id>-tk-9f2c' > token.txt
echo "-> upload index.html and token.txt to the claimed service"
echo "-> DO NOT deploy anything that impersonates the brand or collects credentials"
# STEP 2 - the proof: fetch the target's name and see YOUR page
sleep 30   # allow DNS and the provider's provisioning
curl -sS "http://dev.target.example/" | grep -oE 'Subdomain takeover proof|verification token:.*'
echo "   ^ YOUR content at THEIR name - this is the finding"
# STEP 3 - the same over HTTPS, which shows whether a certificate is issued for the name
curl -sS -o /dev/null -w 'https %{http_code}  cert-issuer %{ssl_verify_result}  ' "https://dev.target.example/" 2>/dev/null
echo | openssl s_client -connect dev.target.example:443 -servername dev.target.example 2>/dev/null | grep -E 'subject=|issuer=' | head -2
```

**The token page is the artefact.** A timestamped page with the engagement id, served at the target's
name, is unambiguous and does not require any brand impersonation.

### 9.3 The DNS-state matrix, which shows how far each name has gone

```python
# the four states, and which ones are claimable
import subprocess, re

def dns(name, rtype):
    try:
        out = subprocess.run(["dig", "+short", rtype, name], capture_output=True, text=True, timeout=10).stdout.strip()
        return out or "<none>"
    except Exception as e:
        return f"ERR:{type(e).__name__}"

NAMES = ["dev.target.example", "staging.target.example", "test.target.example", "old.target.example",
         "app.target.example"]
print("%-28s %-34s %-8s %s" % ("name", "CNAME", "HTTP", "state"))
for n in NAMES:
    cn = dns(n, "CNAME"); a = dns(n, "A")
    try:
        r = subprocess.run(["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}",
                            "--max-time", "8", f"http://{n}/"], capture_output=True, text=True, timeout=12).stdout.strip()
    except Exception:
        r = "ERR"
    if cn != "<none>" and r in ("000", "404", "502", "503", "ERR"):
        state = "CANDIDATE - dangling CNAME, no live service"
    elif r in ("000", "ERR"):
        state = "candidate - does not resolve or serve"
    else:
        state = "live"
    print("%-28s %-34s %-8s %s" % (n, cn[:34], r, state))
print()
print("only the CANDIDATE rows are worth chasing; a 'live' row is the CONTROL that shows")
print("the difference between a taken-over name and a healthy one.")
```

**Only the dangling rows are candidates, and a `live` row is the control.** The matrix is what makes the
difference between a takeover and a live name explicit.

### 9.4 The impact surfaces

```bash
S="dev.target.example"; PARENT="target.example"
# 1) COOKIES: a wildcard-scoped cookie or a parent-domain session flow
dig +short TXT "$PARENT"; echo "---"
curl -sS -D- -o /dev/null "https://$S/" 2>&1 | grep -i '^set-cookie'
# 2) CORS: does the parent's API trust the taken-over host - check before you control it
curl -sS -D- -o /dev/null "https://api.$PARENT/api/me" -H "Origin: https://$S" 2>&1 | grep -iE 'access-control|HTTP/'
# 3) CSP: does a parent page's policy allow the taken-over host as a script source
for P in / /login /app; do
  printf '%-8s ' "$P"
  curl -sS "https://$PARENT$P" 2>/dev/null | grep -oiE "content-security-policy[^>]*" | head -c 300; echo
done
# 4) EMAIL: the DKIM/SPF/DMARC state, which decides whether the name can send mail
for R in SPF DKIM DMARC; do
  case $R in SPF) D="TXT";; *) D="TXT";; esac
  printf '%-8s ' "$R"; dig +short TXT "$( [ $R = DMARC ] && echo _dmarc.$PARENT || echo $PARENT )" | head -2
done
# 5) OAuth: whether the name is an allowlisted redirect_uri or an allowed origin
echo "--- check the OAuth client config and the SSO allowlist for $S"
```

**The parent-domain trust is the severity.** A takeover on a host that the API trusts for CORS, or that a
parent CSP allows, or that can send authenticated mail, is a different grade of finding.

### 9.5 The safe-claim discipline

```python
RULES = [
 "claim ONE name, the most clearly dangling one, and only the name in scope",
 "serve a token page: a timestamp, the engagement id, and nothing resembling the brand",
 "never collect credentials, never impersonate the login page, never serve content to real users",
 "do not claim a name that is serving production traffic or that has a valid certificate in use",
 "release the claim immediately after the evidence is captured, and confirm the release",
 "photograph the DNS record and the response BEFORE the claim and AFTER it",
 "if the provider requires a payment method, do not proceed without written authorisation",
 "if the name is on a mail-sending domain, do not send mail; report the state only",
]
for r in RULES: print(" -", r)
print()
print("WHAT THE REPORT NEEDS: the DNS record, the pre-claim fingerprint, the pre-claim response,")
print("the claimed page with the token, the post-claim response, and the release confirmation.")
```

**One name, a token page, and a release.** The discipline is what keeps a takeover proof from becoming an
impersonation, and the release confirmation belongs in the report.

### 9.6 The end-to-end harness

```bash
python3 - <<'PY'
import subprocess, re, time
S = "dev.target.example"; GOOD = "app.target.example"
def sh(*a, t=12):
    try:
        return subprocess.run(a, capture_output=True, text=True, timeout=t).stdout.strip()
    except Exception as e:
        return f"ERR:{type(e).__name__}"

print("=== DNS RECORDS ===")
for n in (S, GOOD):
    print(" ", n)
    for rt in ("CNAME", "A", "AAAA"):
        v = sh("dig", "+short", rt, n)
        if v: print(f"    {rt:6} {v[:90]}")

print()
print("=== HTTP RESPONSE AND FINGERPRINT ===")
for n in (S, GOOD):
    code = sh("curl", "-sS", "-o", "/tmp/f.html", "-w", "%{http_code}", "--max-time", "10", f"http://{n}/")
    body = open("/tmp/f.html", errors="replace").read()[:300]
    print(f"  {n:28} {code}")
    if code != "200":
        print("    body:", body.replace("\n", " ")[:220])

print()
print("=== VERDICT ===")
code = sh("curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", "10", f"http://{S}/")
cn = sh("dig", "+short", "CNAME", S)
if code in ("000", "404", "502", "503") and cn:
    print(f"  CANDIDATE: {S} has CNAME {cn} and returns {code}")
    print("  NEXT: identify the provider from the body, claim it, serve the token page, re-fetch.")
    print("  CONTROL: {} returns 200 with the real application.".format(GOOD))
else:
    print(f"  live or ambiguous ({code}); the control above shows what a healthy name looks like")
print()
print("FINDING = YOUR token page served at the target's name, with the DNS record quoted")
print("          and a healthy subdomain as the control. A dead CNAME alone is a candidate.")
PY
```

**The pre-claim state, the claim, and the controls.** A dead CNAME is a candidate, and the token page
serving at the target's name is the finding.

---

## 10. EVIDENCE STANDARD — TAKEOVER ARTEFACTS

| Item | Why |
|---|---|
| The **DNS record** (the CNAME chain and the A records), quoted | the mechanism |
| The **pre-claim response** and its provider fingerprint | proves the name was dangling and identifies the service |
| The **healthy-subdomain control** | distinguishes a takeover from a name that is simply down |
| The **claimed token page**, with a timestamp and the engagement id | the finding, unambiguously |
| The **post-claim response** at the target's name | the proof of control |
| The **certificate state**, before and after | whether TLS can be issued for the name |
| The **parent trust surfaces**: cookies, CORS, CSP, email, OAuth allowlists | the severity |
| The **release confirmation**, and the time it happened | engagement integrity |
| Whether the takeover is **wildcard** (every name) or single | the scope |
| The **provider's claim behaviour** (did it require ownership proof?) | the root cause and the fix |

Report the **claim and the record**: "`dev.target.example` has a CNAME to
`dev-target.herokuapp.com` and returns `404` with Heroku's `No such app` page, while `app.target.example`
returns `200` with the application, which is the healthy control. The name was claimed in a Heroku
account, and `http://dev.target.example/` then returned my token page containing
`Subdomain takeover proof` and `verification token: <engagement-id>-tk-9f2c` with a timestamp of
`2026-09-12T09:14:22Z`. `dig +short CNAME dev.target.example` still shows the same target, so the record
was never changed. `https://api.target.example/api/me` returns
`Access-Control-Allow-Origin: https://dev.target.example` with credentials, so the name is trusted for
CORS and the takeover composes into a cross-origin read, which is reported separately. The claim was
released at `2026-09-12T09:31:10Z` and the name now returns the provider's unclaimed page again", never
"there is a dangling CNAME record".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| An **`NXDOMAIN`** for the name | nothing to claim |
| A CNAME to a service that is **still serving the real site** | not dangling |
| A `404` from **the target's own infrastructure** | the name is served by the target, not by a claimable service |
| A provider's **generic landing page** for a name you do not control | verify the claim, not the page |
| A **`502`/`503`** with the target's own server header | the origin is down, not claimable |
| A take-overable name **outside the engagement scope** | out of scope; report the observation only |
| A **wildcard DNS** that resolves everything, with no claimable service behind it | verify the service, not the DNS |
| A name whose provider **requires ownership proof** you could not satisfy | not claimable |
| A finding where you claimed a name **serving production traffic** | an incident you caused |
| A finding where you **left the claim active** | an incident you caused |
| A dangling record on a **third-party domain**, not the target's | not the target's exposure |

**A page you control served at the target's name, plus the healthy control.** Dead DNS records that were
never claimable are this family's most common non-finding.

---

## 11. REMEDIATION REFERENCE — DANGLING RECORD HARDENING

1. **Remove the DNS record at the moment the service it points to is decommissioned** - it is the entire fix, and the ordering matters more than the tooling.
2. **Inventory every CNAME and every record pointing at a third-party service, with an owner, a purpose, and a review date** - an unowned record is the one that dangles.
3. **Run a pre-decommission step that removes the record first and the service second** - the reverse order is how every one of these is created.
4. **Monitor every external record for the provider's unclaimed-service signature, and alert on it** - the fingerprint in 9.1 is a reliable signal and is cheap to check.
5. **Re-verify a service's ownership claim where the provider supports it, and prefer providers that require a verification record** - a provider with an ownership check removes the class.
6. **Restrict the trust attached to subdomains: do not allowlist a wildcard in CORS, CSP, or the OAuth `redirect_uri`, and do not issue wildcard cookies** - it bounds the impact when a name is lost.
7. **Include subdomain takeover in the release process for any service decommission, with a checklist item and a named owner** - the defect is a process defect, not a technical one.
8. **Keep an up-to-date certificate inventory and treat a newly issued certificate for an unexpected name as an alert** - it detects a takeover in progress over TLS.
9. **Prefer names under a domain you control for anything customer-facing, and avoid handing brand-bearing names to providers you do not manage** - it reduces the surface that can dangle.
10. **Publish the e-mail authentication state for the parent domain so a taken-over subdomain cannot send authenticated mail** - DMARC with a strict policy bounds the impact.
11. **Re-run the external-record inventory quarterly, and after every decommission, migration, or provider change** - the window between a decommission and a detection is the exposure.

---

## 12. RELATED SIBLINGS - LOAD TOGETHER

- [subdomain-takeover](../subdomain-takeover/SKILL.md) - the full technique reference
- [attack-cors](../attack-cors/SKILL.md) - the trust a taken-over name inherits
- [recon-methodology](../recon-methodology/SKILL.md) - the enumeration that supplies the candidate list
- [insecure-source-code-management](../insecure-source-code-management/SKILL.md) - the other place an abandoned asset is found
- [attack-host-header](../attack-host-header/SKILL.md) - the sibling trust defect on the same names

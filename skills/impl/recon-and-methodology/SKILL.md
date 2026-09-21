---
name: recon-and-methodology
description: >-
  Reconnaissance and methodology playbook. Use when mapping assets, discovering endpoints, fingerprinting technology, and building a structured testing plan for a new target.
---

# SKILL: Recon and Methodology — Expert Bug Bounty Playbook

> **AI LOAD INSTRUCTION**: Systematic recon and bug-finding methodology from top bug hunters. Covers subdomain enumeration, endpoint discovery, tech fingerprinting, and the hunter's mental model for finding bugs that others miss. Key insight: most high-severity bugs are found through systematic coverage, not just clever payloads.

---

## 1. RECON HIERARCHY

```
Target Selection
└── Scope Definition (in-scope assets)
    └── Asset Discovery (subdomains, IPs, domains)
        └── Tech Fingerprinting (what's running)
            └── Endpoint Discovery (attack surface)
                └── Vulnerability Testing (per vulnerability type)
```

---

## 2. SUBDOMAIN ENUMERATION (CRITICAL FIRST STEP)

### Passive (no DNS queries to target)
```bash
# Subfinder (aggregates multiple sources):
subfinder -d target.com -o subdomains.txt

# Amass passive:
amass enum -passive -d target.com

# Certsh (certificate transparency):
curl -s "https://crt.sh/?q=%.target.com&output=json" | jq -r '.[].name_value' | sort -u

# SecurityTrails API, Shodan:
# Web: https://securitytrails.com/list/apex_domain/target.com
```

### Active (DNS brute force + resolution)
```bash
# Massdns + wordlist:
massdns -r /path/to/resolvers.txt -t A -o S -w output.txt \
  <(cat wordlist.txt | sed 's/$/.target.com/')

# ffuf for subdomain brute:
ffuf -w subdomains-wordlist.txt -u https://FUZZ.target.com \
  -mc 200,301,302,403 -H "Host: FUZZ.target.com"

# DNSx for bulk resolution:
cat subdomains.txt | dnsx -a -resp -o resolved.txt

# Recommended wordlist: SecLists/Discovery/DNS/
```

### Virtual Host Discovery
```bash
# ffuf vhost mode:
ffuf -w wordlist.txt -u https://target.com \
  -H "Host: FUZZ.target.com" -mc 200,301,403

# gobuster vhost:
gobuster vhost -u https://target.com -w wordlist.txt
```

---

## 3. SERVICE AND PORT DISCOVERY

```bash
# Fast port scan (common ports):
nmap -T4 -F target.com -oN ports.txt

# Comprehensive scan on resolved subdomains:
cat resolved_ips.txt | nmap -iL - --open -p 80,443,8080,8443,8888,3000,5000 -oG scan.txt

# httpx for HTTP probing:
cat subdomains.txt | httpx -title -tech-detect -status-code -o live_hosts.txt

# masscan for speed on large IP ranges:
masscan -p 80,443,8080,8443 10.0.0.0/8 --rate=1000
```

---

## 4. WEB TECHNOLOGY FINGERPRINTING

```text
# Wappalyzer (browser extension) or:
whatweb https://target.com

# httpx with tech detection:
httpx -u https://target.com -tech-detect

# Check headers manually:
curl -sI https://target.com | grep -i "server\|x-powered-by\|x-generator\|cf-ray"

# Fingerprint from:
- Server header: nginx/1.18, Apache/2.4, IIS/10.0
- X-Powered-By: PHP/7.4, ASP.NET
- Cookies: PHPSESSID (PHP), JSESSIONID (Java), _rails_session (Rails)
- HTML comments: <!-- Drupal 9 -->
- Meta generator: <meta name="generator" content="WordPress 6.2">
- JS framework files: /static/js/angular.min.js
```

---

## 5. ENDPOINT DISCOVERY

### Directory Brute Force
```bash
# ffuf (fastest):
ffuf -u https://target.com/FUZZ -w /usr/share/seclists/Discovery/Web-Content/raft-medium-files.txt \
  -mc 200,301,302,403 -t 50 -o dirs.txt

# Gobuster:
gobuster dir -u https://target.com -w wordlist.txt -x php,html,js,json

# feroxbuster (recursive):
feroxbuster -u https://target.com -w wordlist.txt -x php,html,txt -r
```

### Parameter Discovery
```bash
# Arjun (hidden parameter finder):
arjun -u https://target.com/api/endpoint

# x8:
x8 -u https://target.com/api/endpoint -w params-wordlist.txt
```

### JavaScript Source Mining
```bash
# Extract endpoints from JS files:
gau target.com | grep '\.js$' | httpx -mc 200 | xargs -I{} curl -s {} | \
  grep -oE '"/[a-zA-Z0-9/_-]+"' | sort -u

# LinkFinder:
python3 linkfinder.py -i https://target.com -d -o output.html

# GetAllURLs (gau):
gau target.com | sort -u > all_urls.txt

# Wayback URLs:
waybackurls target.com | sort -u > wayback_urls.txt
```

### API Endpoint Discovery
```bash
# Common API paths:
ffuf -u https://target.com/FUZZ -w /SecLists/Discovery/Web-Content/api/api-endpoints.txt

# Swagger/OpenAPI:
test: /swagger.json /api-docs /openapi.json /v2/api-docs /.well-known/ /docs/

# GraphQL:
test: /graphql /gql /v1/graphql /api/graphql
```

---

## 6. SOURCE CODE RECON

### GitHub / GitLab Exposure
```bash
# trufflehog (secret scanner in git history):
trufflehog git https://github.com/target-org/target-repo

# gitleaks:
gitleaks detect --source /path/to/cloned/repo

# Manual GitHub search:
# site:github.com "target.com" "api_key" OR "secret" OR "password"
# site:github.com "target.com" ".env" OR "config.php" OR "db_password"

# GitHub dorks:
# "target.com" extension:env
# "target.com" filename:*.config password
# org:target-org secret OR password OR apikey
```

### Exposed Environment Files
```
# Check common paths:
https://target.com/.env
https://target.com/.git/config
https://target.com/config.json
https://target.com/config.yaml
https://target.com/credentials.json
https://target.com/secrets.json
https://target.com/wp-config.php
https://target.com/backup.sql
https://target.com/backup.zip
```

---

## 7. ZSEANO'S TESTING METHODOLOGY

### Core Philosophy
1. **Go deep on one program** rather than spread across many — learn the application thoroughly
2. **Build a profile of the company** — tech stack, developers, processes
3. **Look where others don't** — check error pages, admin paths, old versions, mobile API
4. **Follow the filter** — if input is filtered somewhere, that functionality exists and may be bypassed

### Testing Sequence (One Page / Feature)
```
For each input point:
1. Non-malicious HTML tags (<h2>, <img>) → are they reflected?
2. Incomplete tags → what happens? (<iframe src=//evil.com )
3. Encoding tests → %0d, %0a, %09, <%00
4. Observe the OUTPUT too (not just response) — where does your input appear?
5. Test same input in ALL similarly-structured pages (shared code → shared vuln)
6. Check if the same parameter exists in mobile/API endpoint (less protected)
```

### Parameter Insights
```
- Each parameter tells a story: "what does this do server-side?"
- Filename → OS interaction → Path Traversal / CMDi
- URL/location → HTTP fetch → SSRF
- Template/HTML parameter → render function → SSTI
- XML field → parser → XXE
- SQL filter → query → SQLi
- User-content → storage → Stored XSS
```

---

## 8. BUG BOUNTY PROGRAM TRIAGE (WHERE TO SPEND TIME)

### High-Value Target Selection
```
✓ Programs with large scope (*.target.com)
✓ Programs that pay for P2/P3 (not just RCE)
✓ Programs with recent tech changes (migrations = new bugs)
✓ Programs with active development (new features = new attack surface)
× Avoid: frozen/old codebases with well-known CVEs (already claimed)
× Avoid: strict programs with narrow scope (less surface)
```

### High-Value Feature Focus (by bug probability)
```
Priority 1: Authentication, password reset, 2FA → account takeover
Priority 2: File upload, profile edit, API endpoints → stored XSS, IDOR
Priority 3: Admin panels, user management → BFLA, privilege escalation
Priority 4: Payment flows, subscription → business logic
Priority 5: Import/export, template rendering → XXE, SSTI
```

---

## 9. NUCLEI TEMPLATES (AUTOMATED SCANNING)

```bash
# Run all on target:
nuclei -u https://target.com -t /nuclei-templates/ -o nuclei-results.txt

# Specific categories:
nuclei -u https://target.com -t cves/ -severity critical,high
nuclei -u https://target.com -t exposures/
nuclei -u https://target.com -t misconfiguration/

# On subdomain list:
cat subdomains.txt | nuclei -t exposures/ -t misconfiguration/ -o exposed.txt
```

---

## 10. COMMON MISCONFIGURATIONS (QUICK WINS)

```
□ CORS: Access-Control-Allow-Origin: * with credentials → CSRF + data theft
□ S3 bucket public: curl https://target.s3.amazonaws.com/
□ Directory listing: response contains "Index of /"
□ .git exposed: curl https://target.com/.git/config
□ .env exposed: curl https://target.com/.env
□ Debug mode: stack traces in production (source code exposure)
□ Default credentials: admin:admin, admin:password on admin panels
□ phpinfo.php: curl https://target.com/phpinfo.php
□ Backup files: config.bak, database.sql.gz, app.zip
□ GraphQL introspection enabled: POST /graphql {"query":"{__schema{types{name}}}"}
□ Admin panels: /admin /manager /console /phpmyadmin /wp-admin
```

---

## 11. QUICK REFERENCE TOOLS

| Category | Tool |
|---|---|
| Subdomain enum | subfinder, amass, massdns |
| Port scan | nmap, masscan |
| HTTP probe | httpx |
| Dir brute | ffuf, feroxbuster, gobuster |
| JS mining | LinkFinder, gau, waybackurls |
| Secret scan | trufflehog, gitleaks |
| Parameter fuzz | arjun, x8 |
| Vuln scan | nuclei |
| Proxy/intercept | Burp Suite Pro |
| JWT attacks | jwt_tool |
| SQLi | sqlmap |
| XSS | dalfox, XSStrike |
| SSRF | SSRFmap, Gopherus |

---

## 12. JAVA MIDDLEWARE FINGERPRINT MATRIX

| Middleware | Detection Path | Key Indicators |
|---|---|---|
| Apache Tomcat | `/manager/html`, `/manager/status` | Default creds: `tomcat:tomcat`, `admin:admin` |
| JBoss / WildFly | `/jmx-console/`, `/web-console/` | JMX MBean access, WAR deployment |
| WebLogic | `/console/`, `/wls-wsat/` | T3 protocol on 7001/7002, IIOP |
| Spring Boot Actuator | `/actuator/`, `/actuator/env`, `/actuator/heapdump` | JSON endpoint listing, heap dump contains secrets |
| Spring Boot (alt paths) | `/actuator/jolokia`, `/actuator/gateway/routes` | Jolokia JMX bridge, Gateway route injection |
| Jenkins | `/script`, `/manage` | Groovy console, API token in cookie |
| GlassFish | `/common/`, `/theme/` | Admin on 4848, default empty password |
| Jetty | `/jolokia/` | JMX access |
| Resin | `/resin-admin/` | Admin panel |

### Spring Boot Actuator Exploitation Priority

```
/actuator/env          → Leak environment variables (DB creds, API keys)
/actuator/heapdump     → Download JVM heap → search for passwords in memory
/actuator/jolokia      → JMX → possible RCE via MBean manipulation
/actuator/gateway/routes → Spring Cloud Gateway → SpEL injection (CVE-2022-22947)
/actuator/configprops  → All configuration properties
/actuator/mappings     → All URL mappings (hidden endpoints)
/actuator/beans        → All Spring beans
/actuator/threaddump   → Thread dump (may leak session tokens / secrets in stack frames)
```

---

## 13. INFORMATION LEAK DETECTION CHECKLIST

### Version Control & Backup Leaks

```
/.git/HEAD                    → Git repository exposed
/.svn/entries                 → SVN metadata
/.svn/wc.db                   → SVN SQLite database
/.hg/requires                 → Mercurial
/.bzr/README                  → Bazaar
/.DS_Store                    → macOS directory listing
```

### Backup File Patterns

```
/backup.zip    /backup.tar.gz    /backup.sql
/wwwroot.rar   /www.zip          /web.zip
/db.sql        /database.sql     /dump.sql
/config.php.bak    /config.php~    /config.php.swp
/.config.php.swp   /wp-config.php.bak
/.env          /.env.bak         /.env.production
```

### API Documentation & Debug

```
/swagger-ui.html              → Swagger/OpenAPI
/swagger-ui/                  → Swagger UI
/api-docs                     → API documentation
/graphql                      → GraphQL playground
/graphiql                     → GraphQL IDE
/debug/                       → Debug endpoints
/phpinfo.php                  → PHP configuration
/server-status                → Apache status
/server-info                  → Apache info
/nginx_status                 → Nginx status
```

### Cloud & Infrastructure

```
/.aws/credentials             → AWS credentials
/.docker/config.json          → Docker registry auth
/robots.txt                   → Disallowed paths (hint list)
/sitemap.xml                  → Full URL listing
/crossdomain.xml              → Flash cross-domain policy
/.well-known/                 → Various well-known URIs
```

---

## 14. CONFIRMING THE FINDING

Recon findings are the most commonly rejected, because most of what recon produces is **inventory,
not vulnerability**. A subdomain, an open port, a technology banner, and a leaked path are all
observations until you connect them to an impact. The discipline is to convert an observation into a
finding with one more step.

| Step | Question | What it proves |
|---|---|---|
| 1 | Is the asset **in scope** and owned by the target (not a third party or shared host)? | out-of-scope and shared-hosting findings are rejected outright |
| 2 | Is it **live and reachable** now, not a zoned record or a parking page? | DNS residue produces the majority of false positives |
| 3 | Is it **different from a known-good** sibling (a staging copy, a forgotten vhost)? | the deviation is what is interesting, not the existence |
| 4 | Does the banner match a version with a **specific known issue**? | version alone is not a finding; the matching CVE is |
| 5 | Does the leaked artefact contain **a secret you can use**, or only internal naming? | a path list is a hint; a credential is an impact |
| 6 | Can you reach a **non-public function** (admin, debug, internal API) through this asset? | turns exposure into access |
| 7 | Is the asset **unauthenticated where its sibling is authenticated**? | differential exposure is the strongest recon finding |

**The differential is the finding.** A port scan that lists 22 services is not a report; "the staging
vhost on `dev.target.tld` serves the same app with `DEBUG=True` and returns stack traces that expose
the database DSN" is a report. Always compare the discovered asset against the known-good production
baseline.

**Version banners are a lead, not a conclusion.** `nginx/1.18.0` is a fact; it becomes a finding only
when paired with a reachable, verified behaviour. Report the behaviour you observed, and cite the
version as supporting context — never report a version in isolation.

**Establish ownership and scope first.** A subdomain takeover is only a finding on a host the target
controls; a bucket is only a finding if the target owns it. Verify with DNS records, TLS certificate
issuance, WHOIS, and the program's scope page before you spend time proving impact.

---

## 15. EXECUTION PRIMITIVES
Recon executes as an **observation with a recorded vantage**. Every step below is a procedure, and the
control pair is the observation on a known-present asset against the observation that should find it.

### The vantage, recorded before any finding

```bash
echo "=== 1. RECORD THE VANTAGE. An observation without one is not evidence ==="
cat <<'VANTAGE'
  EVERY RECON OBSERVATION CARRIES:
    - the VANTAGE: passive (a third-party dataset), active (you queried the target), or internal
    - the SOURCE: the dataset, its collection date, and its coverage
    - the TIME: when the observation was made
    - the MECHANISM: DNS resolution, a certificate log, a search engine, a direct connection
  WHY: an active observation is visible to the target's defenders. A passive one is not. THEY ARE
  DIFFERENT FINDINGS EVEN WHEN THE DATA IS THE SAME, and the difference is a scoping and an
  attribution fact, not a detail.
VANTAGE
echo
echo "=== 2. THE WILDCARD TEST, which is mandatory before any subdomain claim ==="
cat <<'WILD'
  A WILDCARD DNS RECORD MAKES EVERY NAME RESOLVE, WHICH FALSIFIES ANY FINDING NOT TESTED FOR IT.
    query a RANDOM, HIGH-ENTROPY label:  <random-uuid>.<domain>
    IF IT RESOLVES, THE ZONE HAS A WILDCARD. Every name you found is then a CANDIDATE, and each
    must be distinguished from the wildcard by its own content, not by its resolution.
  AND THE BRUTE-FORCE CHECK: a wordlist hit that produces the SAME response as the random label is
  the wildcard, not a host. RECORD THE RESPONSE HASH AND COMPARE.
WILD
echo
echo "=== 3. the negative result, which must carry its search's shape ==="
cat <<'NEG'
  'WE FOUND NO SUBDOMAINS' IS NOT A FINDING. A NEGATIVE IS ONLY INFORMATIVE WITH:
    - the WORDLIST, and its size
    - the METHOD (brute force, certificate transparency, passive DNS, a search engine)
    - the VANTAGE (see above)
    - the TIME, and the wildcard test's result
    - the LIMITATIONS: what the method structurally cannot see
  WITHOUT THESE, THE NEGATIVE MEANS 'WE LOOKED A LITTLE', NOT 'IT IS NOT THERE', and reporting it
  as the latter is the commonest false negative in this domain.
NEG
```

**'We found no subdomains' is not a finding** — a negative is informative only with its wordlist, method,
vantage, time, and limitations, and the wildcard test is mandatory.

### Confirmation, and the end-to-end harness

```bash
```
echo "=== EVERY ASSET CONFIRMED BY A SECOND, DIFFERENT OBSERVATION ==="
cat <<'CONFIRM'
  ONE OBSERVATION IS A CANDIDATE. CONFIRMATION IS A DIFFERENT KIND OF OBSERVATION THAT AGREES:
    a DNS record -> a CONNECTION to the resolved address
    a certificate entry -> a TLS handshake presenting that name
    a search-engine hit -> a direct fetch of the page
  AND THE ANTI-PATTERN: RUNNING THE SAME SCANNER TWICE IS NOT TWO OBSERVATIONS. It is one
  observation, repeated, and it agrees with itself by construction.
  AND THE LIVENESS TESTS, WHICH ARE THREE SEPARATE QUESTIONS:
    1. does the NAME resolve?
    2. does the ADDRESS accept a connection on the relevant port?
    3. does the SERVICE identify the asset (a body, a header, a certificate)?
  AN ASSET FAILING TWO OF THREE IS A TAKEOVER CANDIDATE, WHICH IS A DIFFERENT, OFTEN MORE VALUABLE
  FINDING THAN THE ENUMERATION ITSELF.
CONFIRM
echo
echo "=== end-to-end harness ==="
python3 - <<'PY'
print("=== RECON ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("every observation carries a VANTAGE, a source, a time, and a mechanism",
  "active and passive observations are different findings, and the difference is a scope fact"),
 ("the WILDCARD test ran with a random label before any subdomain claim",
  "a wildcard falsifies every name that resolves"),
 ("wordlist hits were compared against the wildcard's response hash",
  "a hit with the same response as the random label is the wildcard, not a host"),
 ("every NEGATIVE carries its wordlist, method, vantage, time, and limitations",
  "'we found nothing' without the search's shape is not a finding"),
 ("every confirmed asset has a SECOND, DIFFERENT observation agreeing",
  "running the same scanner twice is one observation"),
 ("the three liveness tests were run separately, and failures recorded",
  "a name that resolves but does not serve is a takeover candidate"),
 ("the source's collection DATE is recorded",
  "a dataset's age bounds every claim derived from it"),
 ("third-party and shared infrastructure were identified and not claimed",
  "a CDN edge is not the target's asset"),
 ("the methodology's structural blind spots are stated",
  "a certificate-transparency method cannot see internal names"),
 ("no active probing was performed outside the authorised window",
  "recon touches the target and is bound by the same scope as testing"),
]
for n, how in CHECKS: print("  [ ] %-74s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  vantage  : passive, active, or internal; the source, its date, and its coverage")
print("  method   : the mechanism, the wordlist, and the wildcard result")
print("  assets   : each with its second, different confirming observation")
print("  negatives: each with the search's shape and its limitations")
print("  boundary : what was not probed, and the takeover candidates flagged")
PY

---

## 16. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **command and raw output** for each discovery primitive (subfinder/httpx/nmap/ffuf with flags) | recon is reproducible only from the exact tool invocation; the flags are the technique |
| The **baseline asset** you compared against | converts an observation into a differential finding |
| The **timestamp and scope confirmation** (program scope reference, DNS/TLS ownership) | out-of-scope and stale assets are the top rejection reason |
| The **live proof** — an HTTP response, a screenshot, a returned record | proves the asset is real now, not a DNS artefact |
| For exposures: the **artefact itself** (response bytes, listing, leaked file) | the impact is the content, not the URL |
| For version-based leads: the **observed behaviour** plus the version and advisory reference | version alone is not evidence of exploitability |
| The **reachable non-public function** — the request and its response | turns exposure into access |
| Chain mapping: how this asset connects to a **broader finding** | recon is most valuable as the first step of a chain |
| **Negative control** — the production sibling behaves differently | proves the deviation is real and specific to the discovered asset |

Report the **differential and the impact**: "`dev.target.tld` is not in the docs but resolves to the
same origin as production, serves the application without authentication, and returns Werkzeug debug
pages whose stack traces include the `DATABASE_URL`; the production host requires auth and shows no
debug output", never "a staging subdomain was found".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| Subdomain resolves but returns a parking page or `NXDOMAIN`-style stub | DNS residue, not an asset |
| Asset is owned by a **third party** (shared host, CDN, SaaS provider) | out of scope; not the target's system |
| Open port with a service that is **public by design** (443, mail, DNS) | expected exposure |
| Technology banner without a matching, reachable weakness | version alone proves nothing |
| Wildcard DNS makes every name "resolve" | a wildcard response is not discovery |
| Directory listing that exposes only **public** assets | no boundary crossed |
| `.env`/backup path returning `403` or the SPA's `index.html` | the catch-all handler, not a leak |
| Internal hostname or IP in a JS bundle | naming hint; verify reachability before reporting |
| Certificate transparency logs listing a subdomain | CT is a lead, not a live asset |
| Shodan/Censys hit with an old timestamp | verify live before reporting |
| A "leaked" key that is a **public** or test credential, or revoked | no impact |
| Rate-limited or WAF-blocked scan reported as "service down" | measurement artefact |

**Every recon finding needs one more step.** If you cannot state the impact in one sentence, you have
an observation to keep hunting with, not a finding to report.

---

## 17. REMEDIATION REFERENCE

1. **Maintain an authoritative asset inventory and retire what is not in it** - most recon findings are forgotten assets; a quarterly review that decommissions staging, dev, and legacy vhosts removes the class at the source.
2. **Enforce the same authentication and hardening on every environment** - dev/staging must not be a weaker copy of production; apply the same auth, headers, TLS policy, and debug settings through shared configuration, and gate non-production behind SSO or a VPN.
3. **Disable debug modes and verbose errors in every deployed environment** - `DEBUG=False` with a verified test in CI, generic error pages in production, and no stack traces, DSNs, or framework banners in responses.
4. **Turn off directory listing and remove default content** - configure the web tier explicitly (`autoindex off`, `Options -Indexes`), and delete sample apps, default pages, `.git`, `.env`, backups, and editor swap files from the document root.
5. **Automate discovery of your own exposed assets** - run the same subdomain/port/path tooling against yourself on a schedule, with alerting on new names, new ports, and new paths, so you find them before a researcher does.
6. **Publish an accurate scope and a security.txt** - clear, current scope with a machine-readable `/.well-known/security.txt` reduces out-of-scope noise and speeds triage for the findings that matter.
7. **Minimise the metadata you emit** - suppress server and framework version tokens, remove internal hostnames from bundles and comments, and audit client-side source maps before they ship.
8. **Harden DNS and certificate transparency exposure** - remove stale records, avoid wildcard certificates that enumerate your estate, and treat CT logs as public information when naming internal hosts.
9. **Restrict access to non-public surfaces by network, not by obscurity** - admin panels, internal APIs, and monitoring endpoints behind IP allowlists, VPN, or mTLS, so a discovered path is not a discovered entry point.
10. **Patch on a measured cadence and track versions centrally** - version-based findings become exploitable behaviour; keep an inventory of component versions and a process that closes known issues within a defined window.
11. **Monitor for recon-shaped traffic** - bursts of `404`s, sequential subdomain requests, and scanner user-agents are the detectable footprint of enumeration, and give you advance warning of a hunt in progress.

---

## 18. RELATED SIBLINGS - LOAD TOGETHER

- [recon-methodology](../recon-methodology/SKILL.md) - the compact companion playbook to this long-form recon reference
- [subdomain-takeover](../subdomain-takeover/SKILL.md) - the highest-impact finding that recon surfaces
- [insecure-source-code-management](../insecure-source-code-management/SKILL.md) - where a leaked path or repository turns into credentials
- [cloud-assessment](../cloud-assessment/SKILL.md) - triaging exposed cloud assets discovered during recon
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) - converting inventory into reportable findings

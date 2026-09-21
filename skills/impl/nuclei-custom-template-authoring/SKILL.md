---
name: nuclei-custom-template-authoring
description: >-
  Writing and running nuclei templates for scalable vulnerability detection. Use when you need
  to check a class of vulnerability across many targets, convert a manual finding into a
  repeatable check, or triage a large surface. Covers template anatomy, protocol types,
  matchers, and safe execution.
---

# SKILL: Nuclei Template Authoring & Scalable Detection

> **AI LOAD INSTRUCTION**: nuclei is the tool that turns a one-off finding into a check you can
> run against 10,000 hosts. The public library ships 13,761 templates — 4,298 CVE, 1,575
> exposed-panel, 981 misconfiguration, 918 technology-fingerprint, 705 exposure, 307
> default-login, 248 token-spray, 73 takeover. This skill covers **reading** the taxonomy, the
> **anatomy** of a template, and how to **write your own** for what the library does not cover.
> The skill is authoring, not running — `nuclei -t template.yaml -u target` needs no skill.

## 0. RELATED ROUTING

- [recon-methodology](../recon-methodology/SKILL.md) — where scanning sits in the flow
- [nuclei-template-library-operations](../nuclei-template-library-operations/SKILL.md) — running the library: profile selection, gating, triage
- [vuln-research-methodology](../vuln-research-methodology/SKILL.md) — turning a finding into a check
- [api-recon-and-docs](../api-recon-and-docs/SKILL.md) — endpoint discovery to feed templates
- [web-cache-deception](../web-cache-deception/SKILL.md), [attack-ssrf](../attack-ssrf/SKILL.md) — common template targets
- [unauthorized-access-common-services](../unauthorized-access-common-services/SKILL.md) — default-login templates map here

---

## 1. THE PUBLIC TAXONOMY — WHAT YOU ALREADY HAVE

Before writing anything, know what the library covers. Match your need to a category first;
most needs are already solved.

| Category | Templates | Use |
|---|---|---|
| `http/cves` | 4,298 | version-specific vulnerabilities |
| `http/exposed-panels` | 1,575 | admin dashboards, management interfaces |
| `http/osint` | 1,081 | public information about the target |
| `http/misconfiguration` | 981 | default settings, unsafe configs |
| `http/vulnerabilities` | 960 | generic (non-CVE) vulnerability classes |
| `http/technologies` | 918 | fingerprinting |
| `http/exposures` | 705 | files, keys, secrets left public |
| `http/default-logins` | 307 | known default credentials |
| `http/token-spray` | 248 | credential validity probes |
| `http/takeovers` | 73 | subdomain takeover |
| `http/iot` | 66 | embedded devices |
| Protocols | 1,620 total | dns 31, ssl 38, network 282, file 447, code 304, headless 24, javascript 131, dast 251, workflows 207 |

**Decision rule:** run the library before writing a template. A custom template is justified when
(a) no template exists for the target technology, (b) the existing template is too noisy for
this environment, or (c) you need a target-specific check for a client deliverable.

---

## 2. TEMPLATE ANATOMY

Every template is the same five blocks. Read them in this order.

```yaml
id: service-version-check              # 1. IDENTITY — unique, lowercase, hyphenated

info:                                   # 2. METADATA
  name: Service Version Disclosure
  author: operator
  severity: info                        # info|low|medium|high|critical
  description: |
    What this finds and why it matters.
  reference:
    - https://example.com/advisory
  classification:
    cve-id: CVE-2021-0000                # omit if not CVE-backed
    cwe-id: CWE-200
  tags: exposure,disclosure              # drives -tags selection
  metadata:
    verified: true
    max-request: 2

requests:                               # 3. REQUESTS (or http:, network:, dns: …)
  - method: GET
    path:
      - "{{BaseURL}}/api/version"
    matchers-condition: and             # 4. MATCHERS — decides hit/no-hit
    matchers:
      - type: word
        part: body
        words:
          - '"version"'
        condition: and
      - type: status
        status:
          - 200
    extractors:                         # 5. EXTRACTORS — pull data out of a hit
      - type: regex
        part: body
        regex:
          - '"version"\s*:\s*"([^"]+)"'
        group: 1
```

**The discipline that matters:** a template with weak matchers is a false-positive generator.
Matchers must be specific enough that a hit means the finding is real. Where possible, match on
**content that only the vulnerable version produces**, not merely on a 200 status.

---

## 3. MATCHERS — THE PART THAT DECIDES QUALITY

| Matcher | Use for | Trap |
|---|---|---|
| `word` | string in body/header | too short a word matches everywhere |
| `regex` | structured extraction | catastrophic backtracking on large bodies |
| `status` | HTTP code | rarely sufficient alone |
| `dsl` | compound logic over response fields | most powerful, most misused |
| `binary` | raw bytes (binaries, protocols) | needs a hash or offset |

**`matchers-condition: and`** across independent evidence is the standard for a low-noise
template. A status code plus a body marker plus (often) a negative matcher — proving the
*absence* of a patched marker — is what makes a CVE template trustworthy.

**Negative matchers matter for patched-vs-vulnerable discrimination.** If the fixed version
changes a string, match on the vulnerable string and explicitly exclude the fixed one. Without
this, you report every host as vulnerable.

---

## 4. PROTOCOL TYPES

| Type | When | Note |
|---|---|---|
| `http` / `requests` | web | 11,339 of the library |
| `network` | raw TCP/UDP banners | 282 — services, not web |
| `dns` | zone transfer, record checks | 31 |
| `ssl` / `tls` | certificate, cipher, expiry | 38 |
| `file` | local file scanning | 447 |
| `code` | run a script, evaluate a protocol | 304 |
| `headless` | browser-driven (JS-heavy apps) | 24 — heavy, use sparingly |
| `javascript` | custom JS protocol logic | 131 |
| `dast` | fuzzing, input injection | 251 |
| `workflows` | chain multiple templates | 207 — orchestrates the others |

**`workflows` is underused.** It lets a template run only if a precondition template matched —
which is how you avoid sending a CVE probe to 10,000 hosts that are not running the product.
The technology-detection template gates the exploit template. This is the difference between a
useful scan and a noisy one.

---

## 5. AUTHORING PROCEDURE

```
1. Reproduce it manually first.  A template encodes a confirmed finding, not a guess.
2. Minimise the request.         Fewest requests that still prove the finding.
3. Pick the discriminator.       Which response content exists ONLY when vulnerable?
4. Add the negative matcher.     Exclude the patched/lookalike case.
5. Set severity honestly.        Severity inflation destroys the value of a scan.
6. Write the description.        State what a hit means. The next reader has no context.
7. Test against a known-positive AND a known-negative. Both. Always.
8. Gate it in a workflow.        If it targets one product, only run it after detecting it.
```

**Step 7 is not optional.** A template validated only against a vulnerable host is untested —
you have no evidence it stays silent on a patched one.

---

## 6. SAFE EXECUTION

Scanning is the loudest phase of an assessment. Rate, scope, and request shape all matter.

| Control | Setting | Why |
|---|---|---|
| Rate limit | `-rate-limit` / `-rl` | a burst is a denial of service on fragile hosts |
| Concurrency | `-c` | parallel targets multiply the burst |
| Bulk size | `-bs` | hostname resolution volume |
| Tag selection | `-tags`, `-etags` | never run all 13,761 templates against a client |
| Severity | `-severity` | restrict to what the engagement covers |
| Exclusions | `-exclude-tags dos,fuzz` | destructive classes off by default |
| Interactsh | `-ni` when not needed | OAST traffic leaves the client network |

**Never run the full library against production.** Select by tag and severity, exclude
destructive classes, and confirm scope in writing first. A DAST or fuzzing template can take a
service down, and that is a different incident than the one you were hired for.

**Interactsh and OOB:** templates using out-of-band detection send callbacks to a third-party
service. That is egress from the client network to an external host — disclose it before use.

---

## 7. EVIDENCE STANDARD

| Item | Why |
|---|---|
| template id + version/commit of the library | templates change; the finding must be reproducible |
| the target, the request sent, the response received | proof |
| the matcher that fired | distinguishes a real hit from a weak match |
| **manual confirmation of each reported hit** | automated scans produce false positives; unconfirmed hits are not findings |
| scan rate and time window | lets the client correlate with their own logs |
| anything destructive that was excluded, and why | shows scope discipline |

**Never report a scanner output as a finding without manual verification.** The report is
yours; the false positive is also yours.

---

## 8. REMEDIATION REFERENCE

1. **Version hygiene** — the CVE templates are overwhelmingly version-gated; patch cadence is the primary control.
2. **Remove exposed interfaces** — 1,575 exposed-panel templates exist because those panels are reachable; network controls or authentication are the fix.
3. **Change defaults** — 307 default-login templates exist because defaults persist.
4. **Scan yourself with the same library** — it is defensive tooling as much as offensive; run it against your own estate on a schedule.
5. **Alert on scan patterns** — high request rates, sequential path probes, and known template user-agents are detectable; scanning is not stealthy and should not be treated as such.
6. **Watch `exposures` and `misconfiguration` categories** — these are often neglected because they are not CVEs, yet they lead directly to credential and data exposure.

---

## 9. CONFIRMING THE FINDING

A template is a **matcher plus a request**, and a template that fires is not a template that is correct.
This table is what separates a working template from one that produces false positives at scale.

| Step | Question | What it proves |
|---|---|---|
| 1 | Is there a **request/response pair** the template fires against, captured verbatim? | the template's evidence is a pair, not a scan result |
| 2 | Does the matcher fire on the **vulnerable response** and stay silent on a **benign response**? | the negative control, and the whole correctness argument |
| 3 | Is the matcher **specific**: a body condition, a status, a header, a word - not a single common string? | a matcher on `200 OK` matches the internet |
| 4 | Is the **severity and the metadata** justified by what the matcher actually proves? | a matcher on a version banner is not a critical |
| 5 | Was the template run against a **deliberately benign target** that shares the fingerprint? | the false-positive control |
| 6 | Is the template's **id unique, and does it follow the protocol's schema**? | `nuclei -validate` is necessary but not sufficient |
| 7 | Is the finding **reproducible with the template alone**, from a clean checkout? | the template is the artefact and it must stand alone |

**A captured pair, a firing matcher, a silent benign control, and a justified severity.** A template that
validates is syntactically correct; the control is what makes it correct.

---

## 10. EXECUTION PRIMITIVES

This domain executes as a **matcher-against-a-pair differential.** Every step below is a procedure, and the
control pair is the vulnerable response against the benign response the matcher must NOT fire on.

### 9.1 The pair, captured before the matcher is written

```bash
echo "=== 1. capture the TWO responses first: vulnerable and benign ==="
mkdir -p testdata
curl -sS -D testdata/vuln.headers -o testdata/vuln.body  "$VULN_URL"
curl -sS -D testdata/benign.headers -o testdata/benign.body "$BENIGN_URL"
cat <<'PAIR'
  YOU CANNOT WRITE A CORRECT MATCHER WITHOUT BOTH SIDES. The BENIGN response is the one that matters:
    - a PATCHED or FIXED instance of the same product
    - a DIFFERENT product that shares the fingerprint (the version string, the header, the title)
    - the SAME endpoint with the vulnerable condition ABSENT (the parameter removed, the method changed)
  AND THE FINGERPRINT ANALYSIS: what in the vulnerable response is ACTUALLY absent in the benign one?
    If the answer is 'nothing', the matcher cannot be made specific and THE TEMPLATE SHOULD NOT EXIST.
    A matcher on the product's VERSION STRING matches every instance, vulnerable or not.
PAIR
echo
echo "=== the matcher types, in order of how specific they are ==="
python3 - <<'PY'
M = [("dsl / expression",   "a computed condition over the response", "MOST specific: body + status + header + a regex, combined"),
     ("regex on body",      "a pattern in the body",                 "specific IF the pattern is unique to the flaw"),
     ("word",               "one or more literal substrings",        "the commonest SOURCE of false positives"),
     ("header / status",    "a response header or code",             "weak alone; useful only combined"),
     ("binary / hex",       "a byte sequence",                       "specific, and useful for binary protocols"),
     ("a version banner",   "the product's self-reported version",   "CORRELATION, NOT A FINDING. It says 'a candidate'; you still have to test.")]
print("%-20s %-46s %s" % ("matcher","what it tests","its specificity"))
for a,b,c in M: print("%-20s %-46s %s" % (a,b,c))
print()
print("  THE RULE: A MATCHER MUST BE AS SPECIFIC AS THE THING IT CLAIMS. If it claims a specific flaw,")
print("  it must test for that flaw's OBSERVABLE CONSEQUENCE, not for the product's presence.")
print()
print("  AND THE `condition` FIELD: use AND across the parts that must ALL hold (body condition AND")
print("  status AND header), and put the parts in `matchers-condition: and` at the top. An OR across")
print("  weak parts is how a template becomes a machine for false positives.")
PY
```

**A matcher on the product's version string matches every instance** — the benign response is what makes
the template correct, and if nothing differs, the template should not exist.

### 9.2 The negative control, and the validation

```bash
echo "=== 2. THE NEGATIVE CONTROL: run the template against the benign target ==="
cat <<'NEG'
  THE TEST THAT MATTERS:
    A. `nuclei -t my-template.yaml -u $VULN_URL`     -> FIRES        <- intended
    B. `nuclei -t my-template.yaml -u $BENIGN_URL`   -> SILENT       <- THE CONTROL
  IF B FIRES, THE MATCHER IS TOO WEAK, AND THE TEMPLATE MUST BE TIGHTENED BEFORE IT SHIPS.
  AND THE CORPUS TEST, which is how you find the false positives you did not anticipate:
    run the template against a BENIGN CORPUS (a few hundred unrelated hosts you are authorised to
    test, or the project's own testdata) and COUNT the hits. ANY hit on an unrelated host is a
    matcher that is not specific, and it is the same defect at scale.
NEG
echo
echo "=== 3. validation, which is necessary but not sufficient ==="
cat <<'VAL'
  `nuclei -validate -t my-template.yaml` CHECKS SYNTAX AND SCHEMA. It does NOT check:
    - whether the matcher is specific (it validates structure, not correctness)
    - whether the severity is justified
    - whether the request is safe or idempotent
  SO VALIDATE **AND** RUN BOTH CONTROLS. A validator passing template that fires on every Apache is a
  validator passing template.
  AND THE SAFETY CHECK, which the schema will not catch: does the request MODIFY state (POST, PUT,
  DELETE), or is it read-only? A template that writes is a different risk class, and `-validate`
  cannot see it. State the method and the risk in the template's own description.
VAL
echo
echo "=== the severity argument, which is metadata, not decoration ==="
python3 - <<'PY'
S = [("info",     "the matcher proves the product's presence or a version",  "a candidate; do not report as a flaw"),
     ("low",      "an information disclosure with no direct impact",          "justified if the matcher proves the disclosure"),
     ("medium",   "a flaw whose exploitation needs a precondition",           "state the precondition in the description"),
     ("high",     "a directly exploitable flaw the matcher actually proves",  "the matcher must prove it, not the product's version"),
     ("critical", "unauthenticated RCE the matcher proves",                   "RARE. Do not assign it to a version banner.")]
print("%-10s %-58s %s" % ("severity","what justifies it","note"))
for a,b,c in S: print("%-10s %-58s %s" % (a,b,c))
print()
print("  THE RULE: SEVERITY DESCRIBES WHAT THE MATCHER PROVES, NOT WHAT THE PRODUCT MIGHT BE. A")
print("  version-based matcher is 'info' even when the CVE is critical, because the template did not")
print("  prove the flaw - it proved the version. Say 'a candidate for CVE-XXXX; manual confirmation")
print("  required' in the description, and let the operator decide.")
PY
```

**Severity describes what the matcher proves, not what the product might be** — a version-based matcher is
`info` even when the CVE is critical.

### 9.3 The end-to-end harness

```bash
echo "=== the template's own self-check, before shipping ==="
cat <<'SHIP'
  EVERY TEMPLATE SHIPS WITH:
    - the REQUEST (method, path, and any payload), and its state-mutating risk named
    - the MATCHER, at the highest specificity available for this flaw's observable
    - the BENIGN RESPONSE it must NOT match against, kept as TESTDATA alongside the template
    - the SOURCE: where the flaw was characterised, and the version it applies to
    - the METADATA: a unique id, the product, the tags, and a SEVERITY justified by the matcher
  AND THE SHIP TEST, run from a clean checkout:
    1. `nuclei -validate` passes
    2. the template FIRES on the vulnerable fixture
    3. the template is SILENT on the benign fixture
    4. the template is SILENT across the benign corpus
    ONLY THEN IS THE TEMPLATE CORRECT. A template that passes 1 alone is a syntax exercise.
SHIP
echo
echo "=== end-to-end harness ==="
python3 - <<'PY'
print("=== NUCLEI TEMPLATE AUTHORING ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the VULNERABLE and BENIGN responses were both captured, verbatim, before the matcher was written",
  "you cannot write a correct matcher without both sides"),
 ("the differentiator between them is NAMED, and it is present in the vulnerable and absent in the benign",
  "if nothing differs, the template should not exist"),
 ("the matcher uses the MOST SPECIFIC type available for this flaw's observable",
  "a word matcher is the commonest source of false positives"),
 ("a version-banner matcher is labelled CORRELATION, and the description says manual confirmation is required",
  "a banner says 'a candidate'; it does not prove the flaw"),
 ("`matchers-condition: and` combines the parts that must ALL hold",
  "an OR across weak parts is how a template becomes a false-positive machine"),
 ("the NEGATIVE CONTROL ran: the template is SILENT on the benign fixture",
  "the control is the correctness argument"),
 ("the BENIGN CORPUS test ran, and any hit on an unrelated host was investigated",
  "this is how you find the false positives you did not anticipate"),
 ("`nuclei -validate` passes, AND both controls pass",
  "a validator checks structure, not correctness"),
 ("the request's METHOD and its state-mutating risk are stated in the template",
  "a template that writes is a different risk class, and the schema cannot see it"),
 ("the SEVERITY reflects what the MATCHER proves, not the product's potential",
  "a version matcher is info even when the CVE is critical"),
 ("the template has a unique id, product, tags, and a source for the flaw",
  "the template is an artefact that must stand alone"),
 ("the template runs from a CLEAN CHECKOUT and reproduces the finding alone",
  "the template, not your working directory, is the deliverable"),
]
for n, how in CHECKS: print("  [ ] %-74s -> %s" % (n, how))
print()
print("=== THE TEMPLATE SHAPE ===")
print("  request  : the method, the path, any payload, and the mutating risk")
print("  matcher  : the most specific type available, combined with AND")
print("  control  : the benign fixture it stays silent on, kept as testdata")
print("  metadata : a unique id, the severity the matcher justifies, the source")
PY
```

---

## 11. RELATED SIBLINGS - LOAD TOGETHER

- [nuclei-template-library-operations](../nuclei-template-library-operations/SKILL.md) - the library a new template joins
- [vuln-research-methodology](../vuln-research-methodology/SKILL.md) - the differential a matcher is built from
- [burp-scan](../burp-scan/SKILL.md) - the scanner finding a matcher may encode
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) - why a template finding needs its own headline, not a bundle
- [injection-checking](../injection-checking/SKILL.md) - the interpreter decision a request template encodes

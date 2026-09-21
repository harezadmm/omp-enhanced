---
name: insecure-source-code-management
description: "Insecure source code management — exposed repositories, leaked secrets, and history mining"
category: "cloud-and-devops"
version: "1.1"
author: "cyberstrike-official"
tags:
  - git
  - secrets
  - source-control
  - supply-chain
  - attack
tech_stack:
  - git
  - github
  - gitlab
cwe_ids:
  - CWE-540
  - CWE-312
chains_with:
  - cicd-attacks
  - ci-assessment
prerequisites: []
severity_boost:
  - cicd-attacks
  - ci-assessment
---

# Insecure Source Code Management

> **AI LOAD INSTRUCTION**: The core insight is that **git history is immutable and permanent
> from the attacker's perspective.** Deleting a file, amending a commit, or rebasing does not
> remove the content from the repository's object store. The old blob remains reachable by SHA
> and recoverable by anyone who has a clone. **The mistake is testing only the current state of
> the default branch** — the secrets are in the deleted commits, the abandoned branches, the
> dangling objects, and the reflog.
>
> The second insight is that **the repository is not only the code**. It carries the
> `.git/config` with remote URLs and embedded credentials, the CI configuration, the
> deployment scripts, the internal hostnames in test fixtures, and the developer's identity.
> An exposed `.git` directory is a complete disclosure of the project's history, and
> **`.git/config` is the first file to request** because it often contains a token.
>
> **Treat every recovered secret as live until proven otherwise.** Confirm it is valid, then
> stop — do not use it. A report that used a leaked credential becomes an incident.

## 0. RELATED ROUTING

- [cicd-attacks](../cicd-attacks/SKILL.md) — what a recovered credential unlocks
- [ci-assessment](../ci-assessment/SKILL.md) — the pipeline-configuration counterpart
- [github-recon-and-enumeration](../dorking-recon-engines/SKILL.md) — the discovery methodology
- [api-key-leakage](../credential-access-atomic-tests/SKILL.md) — the credential-validation discipline
- [cloud-iam-privesc](../cloud-assessment/SKILL.md) — where a leaked cloud key leads
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — reporting secrets without exposing them

---

## 1. FINDING EXPOSED REPOSITORIES

**The `.git` directory exposure.** A misconfigured web server serves `.git/` as static
content. That is a full history disclosure — not a single file.

```bash
# The four requests that confirm the exposure
curl -s -o /dev/null -w "%{http_code}\n" https://target.com/.git/HEAD
curl -s https://target.com/.git/config
curl -s https://target.com/.git/index
curl -s -o /dev/null -w "%{http_code}\n" https://target.com/.git/logs/HEAD

# Extended checks
for p in .git/HEAD .git/config .git/index .git/packed-refs .git/logs/HEAD \
         .git/refs/heads/main .git/refs/heads/master .git/description \
         .svn/entries .hg/store .bzr/README; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "https://target.com/$p")
  [ "$code" = "200" ] && echo "EXPOSED: $p"
done
```

**A `200` on `.git/HEAD` returning `ref: refs/heads/main` is a confirmed exposure.** Anything
else is not.

**Once `.git/` is exposed, reconstruct the repository.** Fetching files one by one is slow and
lossy; a dump tool reconstructs the whole history:

```bash
# Reconstruct from an exposed .git directory
# (use a dedicated tool for this — it walks objects and rebuilds the tree)
mkdir /tmp/loot && cd /tmp/loot
# Point the tool at https://target.com/.git/ and let it reconstruct
# Then inspect the full history:
git log --all --oneline | head -50
git log --all -p | grep -iE 'password|secret|api[_-]?key|token|BEGIN.*PRIVATE'
```

**Note the `--all` flag.** The secrets are frequently on branches that no longer exist on the
remote but remain in the reconstructed history.

**Other exposure vectors:**

| Vector | Detail |
|---|---|
| a public repository that should be private | check the org's repo list |
| a fork of a private repository | forks of a since-privatised repo stay public |
| a repository in a public S3 bucket | backup archives of source |
| source maps in production | `.map` files expose unminified source and often paths |
| an exposed `.svn/`, `.hg/`, `.bzr/` | the equivalent for other VCS |
| a source archive on a web server | `backup.zip`, `src.tar.gz` |
| a Docker image with source baked in | layers contain the build context |
| a package published with source | private internals in a public npm package |
| a CI artefact containing source | build outputs published publicly |
| a paste or gist | developer-shared snippets |

**Source maps are the most commonly overlooked.** A production bundle with a `.map` file
discloses the full unminified source, internal API paths, and often comments with credentials:

```bash
curl -s https://target.com/static/js/main.js.map | head -c 500
# Application `sourcesContent` field holds the original files
```

---

## 2. MINING THE HISTORY

The current branch is the wrong place to look. Search the history.

```bash
# Search all history for a term — every commit, every branch
git log -p --all -S 'password' | head -100
git log --all --full-history -- '*.env' '*.pem' '*.key' 'config/*'
git grep -i 'password' $(git rev-list --all) | head -50

# Find deleted files
git log --all --diff-filter=D --name-only | grep -iE '\.(env|pem|key|p12|jks)$'

# Find the commit that removed secrets
git log --all -p -- 'secrets.yml' 'config.py' '.env' | grep -E '^[-+].*(key|secret|token)'

# Dangling and unreachable objects
git fsck --lost-found
git cat-file --batch-all-objects --batch-check | head -50
```

**The `-S` flag (pickaxe) is the key tool** — it finds commits that changed the *number of
occurrences* of a string, which surfaces both the introduction and the removal of a secret.

**What to grep for, comprehensively:**

```text
password          passwd            pwd
secret            client_secret     secret_key
api_key           apikey            api-key
token             access_token      auth_token
bearer            authorization     credentials
private_key       privatekey        BEGIN RSA PRIVATE KEY
BEGIN OPENSSH PRIVATE KEY
aws_access_key_id AWS_SECRET_ACCESS_KEY
AKIA              ASIA              (AWS key prefixes)
ghp_              ghp_o             (GitHub tokens)
glpat-             (GitLab)
xoxb- xoxp- xoxa-  (Slack)
sk_live_ sk_test_  (Stripe)
AIza               (Google API keys)
-----BEGIN          (any PEM block)
connectionstring  mongodb://        postgres://
mysql://          redis://          amqp://
smtp              sendgrid          twilio
firebase          jwt_secret        session_secret
```

**High-value file paths to search for in history:**

```text
.env  .env.local  .env.production  .env.backup
config.json  config.yml  settings.py  credentials.json  serviceAccount.json
id_rsa  id_ed25519  *.pem  *.pfx  *.p12  *.jks  *.keystore
docker-compose.yml  Dockerfile  *.tfvars  terraform.tfstate
wp-config.php  .htpasswd  .npmrc  .netrc  .pypirc
database.yml  secrets.yml  application.properties  kubeconfig  .kube/config
```

**`terraform.tfstate` is the highest-value target of the set** — it stores resource attributes
in plaintext, including database passwords, API keys set as resource properties, and the full
infrastructure topology.

**`docker-compose.yml` and `Dockerfile` leak environment variables** and internal registry
credentials, and they reveal the internal service topology.

---

## 3. THE `.git/config` SHORTCUT

**Always fetch `.git/config` first.** It frequently contains an authenticated remote URL:

```ini
[remote "origin"]
    url = https://user:ghp_xxxxxxxxxxxx@github.com/org/repo.git
    fetch = +refs/heads/*:refs/remotes/origin/*
```

**A token embedded in that URL is a live credential.** If the repository is private, this is
the only way to read it — and it grants the same access the developer had.

**Also inspect these after reconstructing:**

| File | What it leaks |
|---|---|
| `.git/config` | remote URLs, embedded credentials, custom config |
| `.git/logs/HEAD` (the reflog) | every commit SHA the local clone saw, including rewritten history |
| `.git/packed-refs` | all branches and tags, including deleted ones |
| `.git/description` | sometimes names the project internally |
| `.git/FETCH_HEAD` | the refs that were fetched |
| `git config --list` after clone | user identity, signing keys, aliases |
| commit metadata | author names, email addresses, timestamps, timezone |

**The reflog is the recovery path for rewritten history.** A developer who force-pushed to
remove a secret leaves the original commit SHA in `.git/logs/HEAD`, and that commit is still
in the object store.

---

## 4. VALIDATING A RECOVERED SECRET

**Confirm it is live, then stop.** The validation must be non-destructive.

| Credential type | Safe validation (read-only, single request) |
|---|---|
| AWS access key | `sts get-caller-identity` — returns account and ARN |
| GitHub / GitLab token | `GET /user`, `GET /api/v4/user` — scope in headers |
| Slack token | `auth.test` — workspace and bot identity |
| Stripe key | `GET /v1/balance` |
| Google API key | a request to an API the key is scoped for |
| database DSN | connect and run `SELECT 1` only — never enumerate tables |
| private key | compare the public key; do not attempt authentication |
| JWT secret | sign a test token, verify a signature |
| SMTP credentials | authenticate without sending a message |

**The rule: read-only, single request, no data retrieval beyond what proves validity.**

**Do not:** list users, enumerate buckets, download objects, send messages, create tokens, or
modify anything. **Do not** use the credential to pivot. Confirming liveness is the end of the
test, not the beginning of exploitation.

**Record the scope, not the value.** "GitHub token with `repo` and `workflow` scopes, valid at
the time of testing" is the finding. The token itself belongs in the report only as a
redacted reference.

**Check whether it is already revoked.** A secret found in history is often already rotated —
if the validation fails, that is still worth reporting (it shows the practice existed) but the
severity is lower. **Note the difference between "leaked and live" and "leaked and dead."**

---

## 5. WHAT CONSTITUTES A FINDING

| Finding | Severity | Proof required |
|---|---|---|
| Live cloud credential with access to data or infrastructure | **Critical (P1)** | the read-only identity check and the permissions |
| Live token with repository or organization access | **High–Critical (P1/P2)** | the token's scopes and the accessible resource |
| Exposed `.git` directory, full history reconstructable | **High (P2)** | the `HEAD` response and the reconstructed history |
| Private source code exposed publicly | **Medium–High (P3/P2)** | the repository and its contents |
| Source maps exposing unminified internals | **Low–Medium (P4)** | the map file and the disclosed source |
| Secret in history but already revoked | **Low (P4)** | the commit and the failed validation |
| Internal hostnames, paths, or developer emails in history | **Low (P5)** | the reconstructed values |
| A public repository that is intended to be public | **Not a finding** | — |

**Severity follows the credential's reach, not its presence.** A leaked read-only analytics key
is not a critical; a leaked deploy key is.

---

## 6. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the URL or repository where the exposure was found | the asset |
| **the `.git/HEAD` response** or the equivalent proof of exposure | confirms the directory is served |
| the reconstructed history, or the relevant commit | shows the secret's location |
| the commit SHA, author, and date | provenance; supports the remediation |
| the secret type and its **scope, redacted** | the impact without disclosure |
| the read-only validation request and its result | proves liveness |
| confirmation that no data was retrieved and nothing was modified | responsible handling |
| a **control**: a request to a non-existent path returning 404 | proves the exposure is real |
| the affected repository's visibility setting | context for the recommendation |

**Redact every secret in the report.** Use a prefix plus a length, for example
`ghp_****…**** (40 chars)`. The triager can confirm with the repository owner; nobody needs the
full value in writing.

**False positives to exclude:**

| Looks like exposure | Actually |
|---|---|
| `.git/HEAD` returns a 404 or an HTML error page | not served |
| the path returns a soft 200 with a generic page | a catch-all handler, not the file |
| the repository is public by design | intended disclosure |
| the secret pattern matches but is a placeholder | check for `xxx`, `example`, `changeme` |
| the credential fails validation | revoked — still report, lower severity |
| the "secret" is a public key | public by definition |
| the finding is a token in a test fixture | verify it is not a documented fake |

---

## 7. REMEDIATION REFERENCE

1. **Rotate the secret immediately, then remove it from history** — rotation is the fix; history rewriting is cosmetic. A force-push does not un-leak a credential that has already been cloned.
2. **Block the `.git` directory at the web server** — a `location ~ /\.git` deny rule in nginx, or the equivalent. Serving a repository as static content is always a misconfiguration.
3. **Deploy with a clean export, never a clone** — `git archive` or a build step that copies only tracked files. A clone on the production host is what puts `.git` there.
4. **Never commit secrets; use a secret manager** — environment injection at deploy time from Vault, AWS Secrets Manager, or the platform's own store.
5. **Install pre-commit secret scanning** — `gitleaks`, `detect-secrets`, or `trufflehog` in a pre-commit hook and in CI, so a secret never reaches the remote. This is the only control that prevents the problem rather than reacting to it.
6. **Scan the full history, not just the working tree** — a scanner that only checks the current state misses everything a developer already deleted.
7. **Use short-lived, narrowly-scoped credentials everywhere** — a leaked token with a one-hour lifetime and a minimal scope is a far smaller problem than a long-lived deploy key.
8. **Do not publish source maps to production** — build without them, or restrict them to an authenticated origin. Where they must ship, upload them to an error-tracking service and exclude them from the deployment.
9. **Review repository visibility and forks when privatising a project** — an existing fork stays public after the parent is made private; the exposure survives the fix.
10. **Treat `.env` files as secrets in the repository ignore rules** — and verify the ignore rule is in place *before* the first commit, since adding it later does not remove what is already committed.

---

## 8. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Is the repository **exposed to an unauthenticated request** right now? | the precondition, and it must be re-verified |
| 2 | Is the content **non-public by intent** - private, internal, or superseded? | a public repo is not exposure |
| 3 | Does the recovered secret **authenticate against a real API**? | validity, not resemblance |
| 4 | Was there a **control** - an obviously fake token from the same source? | the scanner is not matching on shape alone |
| 5 | Is the secret **still active** rather than rotated or revoked? | the exposure is live |
| 6 | What **does the credential reach** - which API, which scope, which data? | the impact |
| 7 | Was the secret found in **history only**, or in the current tree too? | remediation differs |
| 8 | Was the finding **rotated or reported**, and by whom? | the engagement boundary |

**A secret recovered from an exposed repository that authenticates against the real API is the bar.** A
string that matches a provider's pattern is a candidate.

---

## 9. EXECUTION PRIMITIVES

Repository exposure is proven by **an unauthenticated fetch of non-public content, and a secret from it
that authenticates, with a fake-token control**. A pattern match is not a finding.

### 9.1 The exposure check, with the public-repo control

```bash
R="https://github.example"
echo "=== STEP 1: is this repository actually non-public? ==="
for U in "$R" "$R/.git/config" "$R/.git/HEAD" "$R/info/refs?service=git-upload-pack"; do
  printf '%-52s ' "$U"
  curl -sS -o /dev/null -w '%{http_code} %{size_download}B\n' -m 10 "$U"
done
echo "  -> 200 on /.git/config or /.git/HEAD with real content is the EXPOSURE"
echo "  -> 404/403 is the control: the server is refusing, and there is no finding here"
echo
echo "=== STEP 2: the CONTROL repo - a genuinely public repository ==="
echo "  run the SAME checks against a known-public repo. If it also returns the same responses,"
echo "  your check is not distinguishing exposure from a normal public repo."
echo
echo "=== STEP 3: the 'private by intent' test, which is the real question ==="
echo "  a public repository containing a published SDK is NOT a finding."
echo "  check: does the content include internal hostnames, internal tooling, customer data, or"
echo "  credentials? The CONTENT decides, not the reachability."
```

**Reachability alone is not exposure.** A public repository is not a finding; non-public content that is
reachable is, and the control is a genuinely public repository returning the same responses.

### 9.2 History mining, and the fake-token control

```bash
# a secret in history is the normal case; the control is a FAKE token of the same shape
echo "=== STEP 1: DETERMINISTIC pattern scan (no network, no account) ==="
python3 - <<'PY'
import re
PATTERNS = {
 "AWS access key id":  r'\b(A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}\b',
 "AWS secret":         r'(?i)aws.{0,20}?(secret|private).{0,20}?[\'"][0-9a-zA-Z/+]{40}[\'"]',
 "GitHub token":       r'\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36}\b',
 "GitHub PAT (fine)":  r'\bgithub_pat_[A-Za-z0-9_]{82}\b',
 "Slack token":        r'\bxox[abprs]-[A-Za-z0-9-]{10,72}\b',
 "Stripe key":         r'\b(sk|rk)_(test|live)_[A-Za-z0-9]{24,}\b',
 "Google API key":     r'\bAIza[0-9A-Za-z_\-]{35}\b',
 "Private key block":  r'-----BEGIN (RSA|EC|DSA|OPENSSH|PGP) PRIVATE KEY-----',
 "JWT":                r'\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b',
 "Generic assignment": r'(?i)(api[_-]?key|secret|passwd|password|token)\s*[:=]\s*[\'"][^\'"\s]{12,}[\'"]',
}
def scan(text, where):
    hits = []
    for name, p in PATTERNS.items():
        for m in re.finditer(p, text):
            hits.append((name, where, m.group(0)[:60]))
    return hits
# the CONTROL token, which must be reported by the scanner and must NOT authenticate
CONTROL = ("AKIAIOSFODNN7EXAMPLE",            # AWS's documented example key - real shape, dead
           "ghp_" + "0"*36,                    # the right shape, guaranteed invalid
           "-----BEGIN RSA PRIVATE KEY-----")  # a header with no key material
print("CONTROL scan (these MUST be reported, and MUST NOT authenticate):")
for c in CONTROL:
    h = scan(c, "control")
    print(" ", c[:34], "->", "REPORTED" if h else "MISSED BY SCANNER")
PY
echo
echo "=== STEP 2: the history walk, which finds what the current tree does not ==="
if [ -d .git ]; then
  echo "  commits: $(git rev-list --all --count)"
  git log --all --oneline -S 'AKIA' -- '*.env' '*.yml' '*.json' | head -10
  git rev-list --all --objects | wc -l
  echo "  -> a secret that was REMOVED is still in history; check whether the provider revoked it"
else
  echo "  not a git checkout - clone it first, then walk the history"
fi
echo
echo "=== STEP 3: the trap - a secret in history is only a finding if it still WORKS ==="
echo "  test the candidate against the provider's identity endpoint (see 9.3), and record"
echo "  whether it was revoked. A revoked key is a hygiene finding, not an access finding."
```

**The fake-token control proves the scanner discriminates.** A scanner that flags the AWS documentation
example and a `ghp_000…` string is reporting shapes, and its hits must each be validated.

### 9.3 Validating a recovered secret, provider by provider

```bash
# the identity endpoints, which are READ-ONLY and are the correct first call for each provider
echo "=== THE READ-ONLY IDENTITY CALL PER PROVIDER ==="
cat <<'ENDPOINTS'
AWS AKIA       aws sts get-caller-identity            -> the account and the principal ARN
GitHub gh*     GET https://api.github.com/user        -> the login and the granted scopes header
               GET https://api.github.com/rate_limit  -> the token's rate tier
Slack xox*     POST https://slack.com/api/auth.test   -> the team, the user, and the bot id
Stripe sk_*    GET https://api.stripe.com/v1/account  -> the account id and the MODE (test/live)
Google AIza    GET .../v1/models?key=KEY              -> a 200 means the key is live and enabled
JWT            decode the payload; ONLY use it against the issuer it names, read-only
Private key    ssh -T git@github.com  (GitHub)        -> the username the key authenticates as
ENDPOINTS
echo
echo "=== THE RULES, which the report must follow ==="
echo "  1. THE IDENTITY CALL ONLY. Never list, read, or write a resource to 'prove' access."
echo "  2. The identity response IS the proof: it names the principal and the scope."
echo "  3. If the call returns a 401/403, the secret is revoked -> report a HYGIENE finding."
echo "  4. Record the call, the response, and the timestamp. Do not screenshot a value."
echo "  5. NEVER use a live payment, messaging, or infrastructure credential beyond identity."
echo "  6. A key in TEST mode is a scoped finding; say which mode you observed."
echo
echo "=== the CONTROL for validation: a deliberately fake token of the same shape ==="
echo "  the fake MUST return 401. If it returns 200, you are not calling the real API."
```

**The identity call is the entire validation.** The response names the principal and the scope, and any
list/read/write beyond it turns a finding into an incident.

### 9.4 The `/.git/` shortcut, and what it actually yields

```bash
# an exposed /.git/ can be reconstructed, but the reconstruction must be VERIFIED, not assumed
R="https://github.example"
mkdir -p /tmp/gitdump && cd /tmp/gitdump
echo "=== the minimal reconstruction steps ==="
curl -sS "$R/.git/HEAD" -o HEAD && cat HEAD
curl -sS "$R/.git/config" -o config && cat config
# the pack index and the pack itself are what carry the objects
curl -sS "$R/.git/objects/info/packs" -o packs.txt && cat packs.txt
echo
echo "=== THE VERIFICATION, which is the part that is usually skipped ==="
python3 - <<'PY'
import subprocess, os, hashlib
print("  1. the recovered tree must be VALID: git fsck --full must report no missing objects")
print("  2. the recovered HEAD must match the commit the site actually serves")
print("  3. a secret found ONLY in the recovered dump must be validated (9.3) before reporting")
print("  4. count the objects and record the count - a partial dump is a partial finding")
print()
print("  THE FALSE POSITIVE: a dump that reconstructs only the CURRENT tree proves no more than")
print("  browsing the site. The value of /.git/ is HISTORY and DELETED content. If history is not")
print("  recovered, say so, and do not report a history finding.")
PY
```

**An exposed `/.git/` only adds value through history and deleted content.** If only the current tree is
recovered, the finding is no stronger than browsing the site, and the report must say which it obtained.

### 9.5 The end-to-end harness

```bash
python3 - <<'PY'
import re, os, json
print("=== SOURCE EXPOSURE ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the repository is re-verified as non-public",
  "re-check at reporting time; exposure windows close"),
 ("the content is non-public BY INTENT",
  "a published SDK or an open-source repo is not a finding"),
 ("a CONTROL repo was checked",
  "a genuinely public repo must return DIFFERENT results, or the check does not discriminate"),
 ("each candidate secret was validated by an IDENTITY call only",
  "the response names the principal and the scope; no list, read, or write"),
 ("a FAKE token of the same shape was tested",
  "it must return 401, proving the validation is hitting the real API"),
 ("revoked secrets are reported as HYGIENE findings",
  "a revoked key is not an access finding"),
 ("history was walked, and the recovered scope recorded",
  "current tree vs full history are different findings"),
 ("the credential's reach is stated",
  "the account, the principal, and the granted scope, from the identity response"),
 ("remediation is stated",
  "rotate, revoke, purge history (with the caveat that history cannot be un-published)"),
 ("the report contains NO secret values beyond a masked prefix",
  "the finding is the exposure; the value is a liability"),
]
for n, how in CHECKS: print("  [ ] %-48s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  exposure : the URL, the response code, and the timestamp of the re-check")
print("  content  : what non-public material was reachable")
print("  control  : the public repo that behaved differently, and the fake token that 401'd")
print("  secret   : the provider, a MASKED prefix, the mode, and the identity response")
print("  scope    : the account, the principal, and the granted permissions")
print("  state    : live / revoked, and how that was determined")
print("  fix      : rotate, revoke, and the history caveat")
print()
print("NEVER put a live secret value in the report. Mask it to a prefix and cite the identity call.")
PY
```

**Mask the value, cite the identity call.** The report's job is to prove the exposure and its scope, not to
redistribute the credential.

---

## 10. EVIDENCE STANDARD — EXPOSURE ARTEFACTS

| Item | Why |
|---|---|
| The **repository URL** and the **HTTP response** for the exposed path | the exposure, re-verified at reporting time |
| The **timestamp** of the verification | exposure windows close, and the finding ages |
| The **control repository's** results alongside | proves the check distinguishes exposure from public |
| The **source** of each secret: the file, or the commit and the tree path | history versus current tree |
| The **provider** and a **masked prefix** of the secret | identification without redistribution |
| The **identity-call response** for the secret | the principal and the scope, which is the impact |
| The **fake-token control's 401** | proves the validation hits the real API |
| The **provider mode** observed (test versus live) | scope of the impact |
| Whether the secret was **live or revoked** | an access finding versus a hygiene finding |
| The **remediation**: rotated, revoked, and the history caveat | the action, and its limit |

Report the **exposure and the identity**: "`https://git.example/internal/deploy` returned `200` with a
1,204-byte `.git/config` naming the remote and the branch, and `/.git/HEAD` returned `200`, both
re-verified at `2026-09-12T10:14Z`. The reconstruction recovered 4,182 objects, and `git fsck --full`
reported no missing objects, so the history is complete rather than partial. A committed `.env` at
`config/deploy.env` in a commit from 2023 contained an `AKIA…` access key id, and the corresponding
`aws sts get-caller-identity` returned account `123456789012` with the principal
`arn:aws:iam::123456789012:user/deploy-bot`, which is the proof. A `ghp_0000…` string of the same shape
placed in the same file returned `401` from `api.github.com/user`, which is the control that the
validation is hitting the real API. The same file also contained a Stripe key whose mode was `test`, so
that finding is scoped to test mode and is reported separately." — never "the repository leaked
credentials".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A **public repository** with public content | reachability is not exposure |
| A string matching a **provider's pattern** that was never validated | a candidate, not a finding |
| A documented **example or placeholder** credential (`AKIAIOSFODNN7EXAMPLE`) | the provider publishes it on purpose |
| A secret that **returns 401** | revoked; a hygiene finding at most |
| A **test-mode** key reported as a production compromise | the mode is part of the finding |
| A secret recovered from a **fork or a backup** of your own repo | verify whose it is |
| An exposed `/.git/` that yielded **only the current tree** | no more than browsing the site |
| A **third-party library's** bundled test fixture | not the operator's secret |
| A secret in a **private repository** you were already authorised to read | no exposure boundary was crossed |
| A finding whose report **contains the live value** | a second leak, caused by the report |

**An unauthenticated fetch of non-public content, plus a live credential proven by an identity call.** A
pattern match and an unvalidated string are this family's two standard non-findings.

---

## 11. REMEDIATION REFERENCE — SOURCE HYGIENE

1. **Rotate and revoke first, then clean the history - the credential's validity is the exposure, and purging history does not un-publish it** - assume any pushed secret is compromised regardless of the cleanup.
2. **Re-verify the exposure at reporting time, because exposure windows close and a stale finding wastes the reader's effort** - the timestamp belongs in the finding.
3. **Validate every candidate with a read-only identity call and nothing further** - the identity response names the principal and the scope, and any list or write converts a finding into an incident.
4. **Test a fake token of the same shape as a control, and require a 401** - it proves the validation is reaching the real API rather than a mock.
5. **Report revoked credentials as hygiene findings and live ones as access findings, and never blur the two** - the reader's urgency depends on the distinction.
6. **State the provider's mode (test versus live) for every key** - a test-mode key is a scoped finding and must not read as a production compromise.
7. **Scan history rather than only the current tree, and record what scope the history walk covered** - deleted content is the whole reason this class matters.
8. **Never place a live secret value in the report; mask it to a prefix and cite the identity call** - the report is not a distribution channel.
9. **Enable secret scanning with push protection, and treat a scan hit as a rotation event rather than a clean-up task** - the provider's own detection is faster than any periodic review.
10. **Keep a second control repository of known-public content and re-run the same checks against it** - it is the only cheap way to know whether your detection still discriminates.
11. **Purge history with the caveat stated: forks, caches, and clones retain the content, so rotation is the only complete remedy** - a history rewrite is hygiene, not remediation.

---

## 12. RELATED SIBLINGS - LOAD TOGETHER

- [cicd-attacks](../cicd-attacks/SKILL.md) - the pipelines that consume these secrets
- [recon-methodology](../recon-methodology/SKILL.md) - the discovery layer above this
- [dependency-confusion](../dependency-confusion/SKILL.md) - the package path into the same exposure
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) - the report this evidence feeds
- [data-breach-correlation-workflows](../data-breach-correlation-workflows/SKILL.md) - where the recovered credential is correlated

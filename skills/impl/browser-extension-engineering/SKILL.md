---
name: browser-extension-engineering
description: >-
  Assessing browser extensions as an attack surface and an enterprise supply-chain risk.
  Use when testing an extension's permissions and message passing, or when advising on
  extension allowlisting and update-risk policy. Covers the manifest attack surface,
  dangerous permission classes, CRX assessment method, and engagement utility limits.
---

# SKILL: Browser Extension Engineering

> **AI LOAD INSTRUCTION**: A browser extension is code the user invited inside the trust
> boundary — it reads pages the firewall never sees, makes requests that look exactly like
> the user, and updates itself without asking. Assess it on both sides: as an application
> with its own vulnerabilities (manifest overreach, unsafe message passing, leaked keys),
> and as a supply-chain item that can turn hostile on update. **An extension benign at
> install time is not evidence it stays benign.**

## 0. RELATED ROUTING

- [xss-exploitation-chains](../xss-exploitation-chains/SKILL.md) — page-context execution the content script parallels
- [csp-bypass-advanced](../csp-bypass-advanced/SKILL.md) — policy boundaries extensions routinely bypass
- [osint-target-profiling](../osint-target-profiling/SKILL.md) — user profiling via extension-visible data
- [browser-extension-engineering](../../core-subjects/browser-extension-engineering.md) — MV3 engineering doctrine stub

---

## 1. WHY EXTENSIONS MATTER

An extension runs with the browser's own privileges: it sees the DOM of every page its host permissions cover — banking, webmail, admin panels — after TLS decryption, after the WAF, inside a process the EDR trusts. Network controls never see it as a separate actor; **it is the browser making the requests, from the user's authenticated session, with the user's cookies attached.**

| Property | Consequence |
|---|---|
| Inside the trust boundary | sees plaintext post-TLS; page CSP and SOP do not bind privileged contexts |
| Requests carry ambient authority | session cookies, SSO tokens, corporate egress reputation — inherited silently |
| Per-user install, silent update | usually no admin rights needed; updates push with no prompt |

Testing implication: treat an in-scope extension as a privileged insider application, not a web page. Enterprise implication: each installed extension is standing access to every site its host permissions match.

---

## 2. THE MANIFEST AS AN ATTACK SURFACE

`manifest.json` (MV3 in current Chrome/Edge) is the declared privilege set. Read it before the code — it states what the extension *can* do.

| Manifest key | Capability granted | Abuse potential |
|---|---|---|
| `permissions` | named API powers (`cookies`, `tabs`, `debugger`, …) | audit each entry individually — see §3 |
| `host_permissions` | sites it can read, modify, and fetch freely | `<all_urls>` is total page visibility |
| `content_scripts` (`matches`, `all_frames`) | JS injected into matching pages | broad `matches` + `all_frames` reaches embedded payment/SSO frames |
| `background` (service worker) | privileged context with cross-origin fetch | the exfiltration point — collected page data lands here |
| `externally_connectable` | which pages/extensions may message it | wildcard `matches` lets any site drive the background |
| `web_accessible_resources` | extension resources exposed to web pages | broad `matches` enables fingerprinting and resource abuse |
| `content_security_policy` | CSP guarding extension pages | a weakened CSP reopens the XSS class the platform tried to close |
| `webRequest` / `declarativeNetRequest` | observe or rewrite traffic at browser layer | silent rewriting the proxy and DLP never see |

**Read the manifest's delta, not just its snapshot — a permission added on update is the highest-signal malicious-update indicator you will get.**

---

## 3. THE DANGEROUS PERMISSION CLASSES

Most permissions are mundane. A small set converts a page helper into a credential-theft or host-compromise tool:

| Permission | What it grants | Why it is dangerous |
|---|---|---|
| `<all_urls>` | read/modify every page, unrestricted cross-origin fetch | total visibility plus silent exfiltration anywhere |
| `cookies` (+ host perm.) | read/write cookies incl. `HttpOnly` for matched sites | session theft that bypasses `HttpOnly` entirely |
| `webRequest` blocking | synchronously modify requests/responses | transparent credential capture below every network control |
| `debugger` | DevTools protocol on tabs — read, modify, intercept anything | **full page control, bypassing the permission model the manifest pretends to enforce** |
| `nativeMessaging` | JSON exchange with a registered host binary | **effectively arbitrary code execution on the host** — it drives a real process outside the sandbox |
| `proxy` | rewrite browser proxy configuration | silent traffic diversion invisible to OS-level settings |
| `tabs` + `scripting` | tab metadata plus programmatic injection | targeted injection into the high-value tab (bank, admin console) |
| `management` / `privacy` | alter other extensions and privacy settings | uninstalls security extensions, weakens hardened settings |

On `nativeMessaging`: the boundary is the host binary's message handler, not the browser. If that binary executes commands or writes files based on message fields, the extension is a remote shell with a JSON skin. **Audit the host binary with the rigour of a setuid program — because that is what it is.** Flag the combination — `debugger`, `nativeMessaging`, or `proxy` alongside `<all_urls>` — not just individual entries.

---

## 4. ENTERPRISE RISK MODEL

The risk is the lifecycle, not the install:

```
benign install → user base → ownership change / sale / compromise
  → malicious update, auto-pushed → same ID, same users, new behaviour
```

| Assumption | Reality |
|---|---|
| Users install only vetted extensions | install is per-user, rarely needs admin; the store page is the vetting |
| Reviewed code is running code | updates push unprompted; the audited code is replaced without notice |
| ID blocklists contain incidents | rebranding defeats ID blocks — same code returns under a new ID within days |
| Store review catches malice | review is point-in-time; delayed activation (logic armed by a later config fetch) passes clean |

**Blocklisting by ID fails because identity is cheap and user base is portable — the defence must be an allowlist (IDs pinned with update URLs), not a blocklist chasing copies.** Scope controls to *updates*: re-review on permission change, alert on publisher change, and treat a permission-widening update to a widely installed extension as a security event by default.

---

## 5. ASSESSING AN EXTENSION DURING TESTING

Work from the declared surface inward to actual behaviour.

**1. Unpack the `.crx`.** A `.crx` is a signed zip variant — unzip it, or copy the versioned directory from the browser profile after store install. Minified bundles are normal; packed/obfuscated code in a supposedly simple utility is itself a finding.

**2. Read the manifest.** Map every key through the §2 table. Note the MV2/MV3 generation, copy `host_permissions` patterns verbatim, and flag wildcard `externally_connectable` / `web_accessible_resources` — those are the message-passing entry points.

**3. Find the service worker.** The privileged brain: cross-origin fetch, storage, native messaging. List every `fetch` destination, every `cookies`/`storage` access, every `connectNative` target. **Any hardcoded endpoint or key here ships to every user — treat it as public.**

**4. Trace message passing.** Content scripts are page-rich but API-poor; the background is the reverse. The bridge — `runtime.sendMessage`, `onMessage` listeners — is where vulnerabilities live. Per listener: does it validate `sender` (origin, tab, extension ID)? Does it act on message fields (URLs to fetch, scripts to inject) unsanitised? A handler fetching an attacker-supplied URL with background host permissions is a confused-deputy hole; one reachable from web pages is remotely triggerable.

**5. Compare declared vs actual.** Grep for keys, webhook URLs, update URLs; then proxy the browser and watch the worker's real traffic. Declared-versus-actual destination mismatch is a finding. Record the exfiltration shape per destination: DOM, form fields, cookies, history.

---

## 6. DEVELOPMENT AND TESTING UTILITY

Extensions are legitimate tooling on tester-owned machines against in-scope targets:

| Use | Why it fits |
|---|---|
| Session capture you control | content script sees post-render DOM (JS-built state) a proxy never reconstructs |
| Browser-layer request rewriting | `declarativeNetRequest` modifies traffic below the app's own code — header injection, CORS neutralisation |
| Replaying authenticated flows | drive the real browser session instead of exporting cookies into a rotting script |
| Throwaway harnesses | faster than a proxy plugin for a one-engagement need |

**Never deploy an extension — even a benign helper — to a client's users or fleet.** Your helper with `<all_urls>` and a debug endpoint is indistinguishable from this skill's threat once it sits on someone else's machine. Load unpacked on tester-owned profiles, remove at engagement end, and list it in the report appendix so nobody mistakes your tooling for a finding or a compromise.

---

## 7. EVIDENCE STANDARD

| Item | Why |
|---|---|
| Extension ID, version, source (store URL or `.crx` hash) | pins the exact code assessed — versions move silently |
| Manifest permission map, host patterns verbatim | the declared surface the rest hangs on |
| Each message listener with its sender validation | the confused-deputy claim is untestable without it |
| Hardcoded endpoints/keys with file and line | lets the client rotate and scope exposure |
| Runtime traffic vs declared destinations | proves actual exfiltration shape, not just capability |
| For enterprise findings: install count, permission-change history | quantifies blast radius, shows the update-risk moment |
| For test tooling: where the helper ran, removal confirmation | proves your tooling did not become a supply-chain incident |

**A permission list without version, sender-validation analysis, and runtime traffic is an inventory, not an assessment.**

---

## 8. REMEDIATION REFERENCE

1. **Enforce `ExtensionSettings` policy** — allowlist by ID pinned with update URL, blocklist the rest, force-install only the managed set; default-deny outside the list.
2. **Treat permission-widening updates as security events** — alert on manifest delta and publisher change; hold fleet rollout pending re-review.
3. **Disable developer mode and sideloading on managed machines** — side-loaded extensions bypass store review and most inventory tooling.
4. **Monitor install, enable, and update events centrally** — log ID, version, and permissions per event so the §4 lifecycle is visible.
5. **Deny the dangerous combinations by default** — `debugger`, `nativeMessaging` hosts, and `proxy` control have almost no legitimate enterprise need.
6. **Audit native-messaging hosts as privileged software** — inventory registered hosts, review each handler like a setuid boundary, remove hosts of delisted extensions.
7. **One concrete user signal** — a permission-change prompt on update means stop and report, not click through; benign extensions do not suddenly need `<all_urls>`.
8. **Re-certify the allowlist on a schedule** — re-validate ownership, permissions, and behaviour per entry; allowlisting is a standing grant, not a one-time approval.

---

## 9. EXECUTION PRIMITIVES

An extension is a **manifest plus a message bus**. The manifest declares the privilege; the message
bus is usually where the privilege leaks. Each block below extracts one of the two.

### 9.1 Unpack and read the manifest first

```bash
# a CRX is a zip with a header - strip to the PK signature and unzip
F="extension.crx"; D="ext"
python3 - "$F" "$D" <<'PY'
import sys, zipfile, io, os
raw = open(sys.argv[1],'rb').read()
i = raw.find(b'PK\x03\x04')
if i < 0: sys.exit("no zip payload found")
os.makedirs(sys.argv[2], exist_ok=True)
zipfile.ZipFile(io.BytesIO(raw[i:])).extractall(sys.argv[2])
print("extracted to", sys.argv[2])
PY
python3 -c "import json;m=json.load(open('ext/manifest.json'));\
print('manifest_version',m.get('manifest_version'));\
print('permissions',m.get('permissions'));\
print('host_permissions',m.get('host_permissions'));\
print('optional_permissions',m.get('optional_permissions'));\
print('externally_connectable',m.get('externally_connectable'));\
print('content_scripts',[c.get('matches') for c in m.get('content_scripts',[])]);\
print('background',m.get('background'))"
```

The four fields that matter are `host_permissions`, `content_scripts[].matches`,
`externally_connectable`, and `web_accessible_resources`. Everything else is implementation.

### 9.2 Enumerate the message surface

```bash
grep -rnE 'onMessage|onMessageExternal|onConnect|onConnectExternal|sendMessage|connect\(' ext/ \
  --include='*.js' | head -40
# which of those accept external (web page) messages?
grep -rn 'onMessageExternal\|onConnectExternal' ext/ --include='*.js'
# and which URLs are allowed to talk to the extension?
python3 -c "import json;m=json.load(open('ext/manifest.json'));\
import pprint;pprint.pprint(m.get('externally_connectable',{}))"
```

`onMessageExternal` with `externally_connectable` matching `<all_urls>` or a wide pattern means **any
web page can drive the extension's privileged logic**. That combination is the finding, not the
permission list on its own.

### 9.3 Find sink usage inside privileged contexts

```text
grep -rnE 'innerHTML|outerHTML|insertAdjacentHTML|document\.write|eval\(|new Function|setTimeout\s*\(\s*["\']|execScript' \
  ext/ --include='*.js' | head -30
# background/service-worker pages have no DOM restriction on chrome.* API access
grep -rnE 'chrome\.(tabs|cookies|history|bookmarks|webRequest|scripting|debugger|downloads)\.' \
  ext/ --include='*.js' | head -30
```

An extension page that writes attacker-influenced data with `innerHTML` **and** holds `cookies` or
`tabs` is one message away from full session access. The two halves must appear together.

### 9.4 Check `web_accessible_resources` for the extension's own UI

```bash
python3 -c "import json;m=json.load(open('ext/manifest.json'));\
import pprint;pprint.pprint(m.get('web_accessible_resources'))"
# any resource exposed to the web is reachable at a predictable URL
echo "chrome-extension://<EXT_ID>/path/from/manifest"
# fingerprints permit detecting the installed extension from a page
curl -sS "https://target.tld/" -o /dev/null -w '%{http_code}\n'
```

From a page you control you can probe `chrome-extension://<id>/<resource>` - if the fetch succeeds
and the page can read the response, the extension is both detectable and a data source. If it fails,
`web_accessible_resources` is correctly scoped.

### 9.5 Update channel and signed-package verification

```bash
python3 -c "import json;m=json.load(open('ext/manifest.json'));print(m.get('update_url'))"
# a non-gallery update_url is the supply-chain finding: whoever controls that URL controls the code
curl -sS "$(python3 -c "import json;print(json.load(open('ext/manifest.json')).get('update_url',''))")" | head -20
# and the CRX3 signature: is the package signed, and with what key?
python3 - <<'PY'
raw=open("extension.crx","rb").read()
print("magic:", raw[:4])                              # 'Cr24'
import struct
ver=struct.unpack("<I", raw[4:8])[0]; print("crx version:", ver)
if ver==3:
    hdr=struct.unpack("<I", raw[8:12])[0]; print("header bytes:", hdr)
PY
```

An `update_url` outside the vendor gallery means an unmanaged code-delivery channel. That is the
enterprise risk in one field, and it is verifiable from the package alone.

### 9.6 Static-to-dynamic: load it in a controlled profile

```bash
# use a throwaway profile - never your real browsing profile with its sessions
P=$(mktemp -d)
chromium --user-data-dir="$P" --load-extension="$HOME/ext" --disable-extensions-except="$HOME/ext" \
         --no-first-run --remote-debugging-port=9222 about:blank &
sleep 4
curl -sS http://127.0.0.1:9222/json/version | python3 -c "import sys,json;print(json.load(sys.stdin)['Browser'])"
# the extension's background page appears as a debuggable target
curl -sS http://127.0.0.1:9222/json/list | python3 -c "
import sys,json
for t in json.load(sys.stdin): print(t['type'], t.get('url','')[:90])"
```

The background target in the debug list is the privileged context. Attaching to it lets you inspect
what the message handlers actually do with input, rather than inferring from source.

### 9.7 Trace a message from a page into the extension

```bash
# from a page you control, in the same browser, send the extension a message
cat > /tmp/probe.html <<'HTML'
<script>
const ID = "EXTENSION_ID_HERE";
try { chrome.runtime.sendMessage(ID, {cmd:"collect"}, r => console.log("resp", r)); }
catch (e) { console.log("blocked:", e.message); }
// also probe the web-accessible surface
fetch(`chrome-extension://${ID}/manifest.json`).then(r => r.text())
  .then(t => console.log("w a r readable:", t.length)).catch(e => console.log("war blocked"));
</script>
HTML
echo "serve on a host matching externally_connectable and open it in the same browser"
```

A response arriving in the page proves the page can call privileged extension logic. That is the
end-to-end demonstration, and it is far stronger evidence than a manifest reading.

### 9.8 Enterprise inventory from the managed policy

```bash
# if you have an enrolled machine, the forced list is readable locally
python3 - <<'PY'
import json, glob, os
paths = ["/etc/opt/chrome/policies/managed/*.json",
         "/etc/chromium/policies/managed/*.json",
         os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/Preferences")]
for p in paths:
    for f in glob.glob(p):
        print("==", f)
        try:
            d = json.load(open(f))
        except Exception as e:
            print("  unreadable:", e); continue
        for k in ("ExtensionInstallForcelist","ExtensionInstallAllowlist",
                  "ExtensionInstallBlocklist","ExtensionSettings"):
            if k in d: print(" ", k, "=", json.dumps(d[k])[:300])
PY
```

An allowlist is an inventory; a forcelist is code you have already authorized. Both are the facts an
assessment should report on, and both are readable from the endpoint.

---

## 10. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Can a **web page** (not just the extension itself) reach the privileged logic? | internal-only messaging is a design, not a vulnerability |
| 2 | Did the message **produce a privileged effect** - a cookie read, a tab manipulated, a script injected? | the effect is the finding, not the API name |
| 3 | Is the calling origin restricted by `externally_connectable`, and did you match it? | if any page can call it, say so explicitly |
| 4 | Does the extension hold a permission that makes the effect serious (`cookies`, `tabs`, `<all_urls>`)? | impact, and it must be a permission the manifest actually requests |
| 5 | Is the channel **unmanaged** - an `update_url` outside the vendor gallery? | the supply-chain finding, verifiable from the package |
| 6 | Can you demonstrate it **end to end in a browser**, from the attacker's origin to the effect? | manifest reading alone is an observation, not a demonstration |
| 7 | Is the user required to take an action they would plausibly take (install, click, visit a page)? | determines whether this is realistic or theoretical |

**A permission is not a vulnerability.** `cookies` access is a design choice; a page driving the
extension to *read* a cookie for another origin is the finding. State the effect.

---

## 11. EVIDENCE STANDARD — CRX AND MESSAGE PROOF

| Item | Why |
|---|---|
| The **CRX version, ID, and hash**, so the exact package is identified | extension findings are version-specific; an unqualified report cannot be triaged |
| The **manifest fields** that matter - `host_permissions`, `externally_connectable`, `content_scripts[].matches`, `web_accessible_resources`, `update_url` | these define the privilege, and they are the fix location |
| The **message path** from the caller to the effect, with the handler source | shows the vulnerability is reachable, not merely present in code |
| The **demonstrated effect** - the value read, the action taken, in the attacker's own browser | end-to-end proof |
| The **permissions the effect relies on**, quoted from the manifest | ties impact to a concrete privilege |
| For update-channel findings: the **`update_url`** and who controls it | the whole supply-chain argument rests on this |
| The **browser and version**, since MV2/MV3 changes what is even possible | MV3 restricts several of these paths; state which platform you tested |
| **Negative control** - a page NOT matching `externally_connectable` fails to reach the handler | proves the origin restriction is what grants access |
| The **enterprise policy state** where relevant (allowlist, forcelist) | determines whether the risk is mitigated in the environment being assessed |
| A clear statement of the **user action** the attack depends on | install-time and click-time consent change severity materially |

Report the **effect and its precondition**: "`externally_connectable` matches `*://*/*` and the
service worker's `onMessageExternal` handler writes `msg.url` into `chrome.tabs.update` without an
origin check; a page on any origin can therefore navigate the active tab to a URL of its choosing,
which I demonstrated from `attacker.tld` against extension ID `abcdef...` on Chrome 131", never "the
extension requests broad permissions".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| Broad permissions with no reachable caller outside the extension | the privilege is not exposed |
| `web_accessible_resources` containing only images or locale files | intended public surface |
| `onMessage` (internal) reachable only from the extension's own pages | no external caller |
| `eval` in a dev-only build, or in a file not shipped in the CRX | not in the delivered package |
| An `update_url` pointing at the vendor gallery | managed channel |
| A finding that requires the user to install a *malicious* extension | that is the attacker's extension, not this one |
| MV2-only technique against an MV3 extension | the platform no longer permits it |
| An effect requiring `--load-extension` or developer mode | user-modified browser, not the shipped configuration |
| A permission listed but never used by any handler | unused privilege, a hygiene note |
| Static manifest reading with no demonstrated caller or effect | an observation |
| An extension you wrote yourself as a proof of concept chain | tests your code, not the target's |
| Any finding that depends on the user pasting code into DevTools | not an attack path |

**Demonstrate the caller.** Without a reachable entry point, an extension assessment is a code review.

---

## 12. REMEDIATION REFERENCE — EXTENSION PRIVILEGE CONTROL

1. **Restrict `externally_connectable` to the minimum origin set, never `<all_urls>`** - the external message bus is a privileged API exposed to the web, and the allowlist is the only access control on it.
2. **Validate the sender in every `onMessageExternal` handler** - check `sender.origin` against an explicit allowlist inside the handler as well as in the manifest, since the manifest pattern is easy to broaden by accident.
3. **Never pass message data into a sink without validation** - `innerHTML`, `eval`, `chrome.tabs.update`, `chrome.scripting.executeScript`, and navigation APIs are the sinks that turn a message into an effect.
4. **Request the minimum host permissions, and prefer `activeTab` with user gesture** - `<all_urls>` in `host_permissions` grants every page's content, and is the difference between a scoped tool and a universal reader.
5. **Prefer MV3 with a non-persistent service worker and no remote code** - it removes remote script execution, restricts `eval`, and shrinks the lifetime in which a compromise persists.
6. **Scope `web_accessible_resources` to specific files and specific origins** - a broadly exposed resource set makes the extension detectable and, if it contains any data, readable by any page.
7. **Pin the update channel to the vendor gallery** - a custom `update_url` is an unmanaged code-delivery path; if a private channel is unavoidable, sign the packages and verify the signature server-side.
8. **Verify the package signature and the publisher at install time** - for enterprises, an allowlist should be keyed to the extension ID *and* the signing key, so a resubmission cannot silently replace vetted code.
9. **Treat extension updates as code deployment, and review them** - an extension with `<all_urls>` receives new code automatically; pinning versions and reviewing diffs is the only control on that channel.
10. **Include extensions in the endpoint inventory and the EDR scope** - an unmanaged extension with broad permissions is unmanaged code in the browser, and should be an asset like any other.
11. **Educate users that an extension's permissions are a grant of trust** - most extension compromise begins with the user approving a permission prompt they did not read; the consent step is a real control worth reinforcing.

---

## 13. RELATED SIBLINGS - LOAD TOGETHER

- [xss-exploitation-chains](../xss-exploitation-chains/SKILL.md) - the web-side execution primitive an extension can amplify
- [csp-bypass-advanced](../csp-bypass-advanced/SKILL.md) - the policy an extension is not bound by
- [dangling-markup-injection](../dangling-markup-injection/SKILL.md) - the exfiltration technique that works when script cannot run
- [insecure-source-code-management](../insecure-source-code-management/SKILL.md) - supply-chain exposure in distributed packages
- [cors-cross-origin-misconfiguration](../cors-cross-origin-misconfiguration/SKILL.md) - the origin model extensions sit outside of

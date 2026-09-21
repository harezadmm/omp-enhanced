---
name: credential-access-atomic-tests
description: >-
  ATT&CK Credential Access techniques with executable atomic tests. Use when hunting for
  credential material on a compromised host, dumping secrets, or validating credential-theft
  detection. Covers the 67 documented techniques across LSASS, SAM/NTDS, Kerberos, browser
  stores, cloud metadata, and password stores.
---

# SKILL: Credential Access — Atomic Test Library

> **AI LOAD INSTRUCTION**: Credential access is where a single host compromise becomes a domain
> compromise. Atomic Red Team documents 67 techniques in this tactic — the second-deepest
> credential-access reference available. This skill covers the technique families, the specific
> mechanisms that matter, and the detection reality (this tactic is the **most heavily
> instrumented** on any modern EDR). Read §4 before selecting: LSASS dumping is the obvious
> choice and usually the wrong one.

## 0. RELATED ROUTING

- [attack-execution-atomic-tests](../attack-execution-atomic-tests/SKILL.md) — the execution-layer counterpart
- [windows-privilege-escalation](../windows-privilege-escalation/SKILL.md) — from user to admin first
- [active-directory-kerberos-attacks](../active-directory-kerberos-attacks/SKILL.md) — Kerberos-specific chains
- [ntlm-relay-coercion](../ntlm-relay-coercion/SKILL.md) — forced authentication
- [hash-attack-techniques](../hash-attack-techniques/SKILL.md) — what to do with what you extract
- [credential-list-engineering](../../core-subjects/credential-list-engineering.md) — credential list strategy

---

## 1. THE FAMILIES

67 techniques, grouped by the material targeted. Establish which store you need **before**
choosing a mechanism — the families have very different detection profiles.

| Family | ATT&CK | Targets | Detection difficulty |
|---|---|---|---|
| **OS credential dumping** | T1003 | LSASS memory, SAM, NTDS.dit, LSA secrets, cached domain creds, DCSync, `/etc/shadow` | **easiest to detect** |
| **Unsecured credentials** | T1552 | files, registry, shell history, private keys, cloud metadata API, container API, chat, GPP | **hardest to detect** — no unusual process |
| **Credentials from password stores** | T1555 | browsers, keychain, Windows Credential Manager, password managers, cloud secret managers | moderate |
| **Modify authentication process** | T1556 | domain controller, password filter DLL, PAM, reversible encryption, hybrid identity | hard — persistent and legitimate-looking |
| **Adversary-in-the-middle** | T1557 | LLMNR/NBT-NS, ARP, DHCP, evil twin | moderate — network-visible |
| **Steal or forge Kerberos tickets** | T1558 | golden/silver ticket, Kerberoasting, AS-REP roasting, ccache | moderate |
| **Steal application access token** | T1528 | OAuth tokens | hard |
| **Steal web session cookie** | T1539 | session cookies | hard |
| **Forge web credentials** | T1606 | web cookies, SAML tokens | hard |
| **Brute force** | T1110 | guessing, cracking, spraying, stuffing | varies — loud if failed, silent if successful |
| **Network sniffing** | T1040 | credentials on the wire | hard on switched networks |
| **Forced authentication** | T1187 | coerce a host into authenticating to you | moderate |
| **Exploitation for credential access** | T1212 | vulnerabilities that yield creds | n/a |

**The strategic point:** T1003 (dumping) is what everyone reaches for, and it is the most
detected. T1552 (unsecured credentials) and T1555 (password stores) yield comparable material
with far less telemetry. **Read files before you touch memory.**

---

## 2. UNSUPPORTED CREDENTIALS — READ THE FILESYSTEM FIRST

The highest-yield, lowest-noise family. No special process, no handle to LSASS, no driver.

| Location | What lives there |
|---|---|
| Config files | connection strings, API keys, `.env`, `web.config`, `appsettings.json` |
| Shell history | `.bash_history`, `.zsh_history`, `.psreadline` — commands typed with credentials inline |
| Private keys | `.ssh/id_*`, `.pem`, `.pfx`, `.p12`, `.keystore` |
| Registry | `HKLM\SYSTEM\CurrentControlSet\Services\<svc>` ImagePath, autologon keys |
| Cloud instance metadata | `169.254.169.254` — role credentials, often unauthenticated from inside |
| Container API | mounted service-account tokens, `/var/run/secrets/` |
| Group Policy Preferences | `cpassword` — AES key is **public**, trivially decrypted |
| Chat / notes | wiki exports, ticket systems, shared drives |

**Why this matters:** these leave almost no host signal. The detection has to be on **file
access patterns** (a non-owner reading a credential file) or on **unusual outbound use** of the
credential — not on process behaviour. Most environments do neither.

**Group Policy Preferences `cpassword` is worth calling out specifically:** the encryption key
was published by Microsoft. Any `Groups.xml` recovered from SYSVOL decrypts immediately. No
cracking step exists.

---

## 3. OS CREDENTIAL DUMPING — THE T1003 SUB-TECHNIQUES

| Sub | Target | Mechanism |
|---|---|---|
| .001 | LSASS memory | minidump, comsvcs, procdump, direct read |
| .002 | SAM | registry hive extraction, offline parse |
| .003 | NTDS.dit | domain controller database, VSS copy |
| .004 | LSA secrets | registry, DPAPI-protected service creds |
| .005 | Cached domain credentials | DCC2 hashes, offline crack |
| .006 | DCSync | replicate from the DC via DRSUAPI — **no code on the DC** |
| .007 | `/proc` filesystem | Linux process memory |
| .008 | `/etc/passwd` and `/etc/shadow` | Linux local |

**DCSync (.006) is the outlier worth understanding:** it abuses the replication protocol, so
there is no LSASS access, no dump file, no malicious process on the target. It requires
replication rights (domain admin or an explicitly delegated account). Detection is on the
*account* and the *protocol*, not on behaviour — which is why it so often goes unseen.

---

## 4. SELECTION — CHOOSING THE QUIET PATH

```
1. Is the credential in a FILE?         → §2. Always check first.
2. Is it in a password store (T1555)?   → browser/keychain/manager. Moderate noise.
3. Do I have replication rights?        → DCSync (T1003.006). No host artifact.
4. Do I have local admin?               → SAM/LSA (T1003.002/.004). Moderate.
5. Am I forced into LSASS?              → T1003.001. Assume you will be caught.
```

**LSASS dumping is #5 for a reason.** Reading `lsass.exe` memory requires a handle that
Sysmon EID 10, Credential Guard, PPL, and every commercial EDR watch specifically. It is the
technique with the best documentation and the worst survival rate. Choose it when the objective
is *detection validation*, not when it is *quiet access*.

---

## 5. DETECTION REALITY

Credential access is the most instrumented tactic on a mature endpoint. Know what you will trip.

| Technique | Signal |
|---|---|
| LSASS read (T1003.001) | process handle to lsass with read access — high-fidelity alert |
| SAM/NTDS copy (T1003.002/.003) | VSS shadow copy creation, `ntdsutil`, hive file copy |
| DCSync (T1003.006) | replication request from a non-DC host |
| Registry hive read | `reg save` of SAM/SECURITY/SYSTEM |
| Kerberoasting (T1558.003) | bulk TGS requests with RC4 encryption |
| AS-REP roasting (T1558.004) | AS-REQ for accounts without pre-auth |
| AiTM (T1557) | LLMNR/NBT-NS/mDNS responses on a network that should not have them |
| Brute force (T1110) | failed auth volume — **but successful brute force has no volume signal** |
| File-based (T1552) | almost nothing — file access audit or credential use is the only lead |

**Credential Guard and LSASS PPL** convert T1003.001 from trivial to a driver-level problem.
Check whether they are on before committing to a memory-dumping chain.

**Where the blind spot is:** §2 and successful brute force. Neither produces a process anomaly,
and neither produces an authentication failure. They are found by credential *use* monitoring —
which most environments lack.

---

## 6. EVIDENCE STANDARD

| Item | Why |
|---|---|
| technique ID + sub-technique | `.006` and `.001` are entirely different findings |
| the exact store targeted and the artefact produced | reproducibility |
| **the number and type of credentials recovered, not their values** | proof without unnecessary exposure |
| whether the material was usable (hash type, whether it cracked) | determines impact |
| the detection outcome | the deliverable |
| for file-based: which configuration put the credential there | this is the actual root cause |

**Never place live credential values in a report.** State the type, count, and privilege.
The client can reproduce; you should not be the second breach.

---

## 7. REMEDIATION REFERENCE

1. **Credential Guard + LSASS PPL** — removes T1003.001 as a practical route.
2. **Eliminate unsecured credentials (T1552)** — secrets managers, no credentials in config or history, disable GPP password storage, IMDSv2 with hop-limit 1.
3. **Tier the domain** — domain admin credentials must never be usable from a workstation; DCSync rights audited and minimised.
4. **Detect on account behaviour, not just process** — replication from a non-DC, TGS volume anomaly, AS-REQ without pre-auth.
5. **Assume breach of hashes** — password rotation after any exposure; `DCC2` cached credentials expire slowly by design.
6. **Credential-use monitoring** — the only control that catches §2 and successful brute force. Tie authentication to device and location.

---

## 8. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | What **identity** did you start as, and what could it read? | the baseline control |
| 2 | Which **T1003 sub-technique**, and what artefact did it leave with its provenance? | the sub-techniques are not interchangeable |
| 3 | Was the credential **used**, not merely obtained? | possession is not access |
| 4 | Was the use's result **read back from the target's own response**? | a tool's success line is not access |
| 5 | Did the **wrong-credential** and **pre-auth** controls both fail? | attributable access |
| 6 | Is the credential **local or domain-wide**, and is reuse demonstrated? | scope |
| 7 | Did it reach the **goal**? | the impact |

**An obtained artefact is step one of five.** A test that stops at the artefact is an information
disclosure finding, and the labels differ for a reason.

---


## 9. EXECUTION PRIMITIVES

Section 1 gives the families and section 4 the selection logic; this section is **how to obtain the
evidence**. Every family in this file reduces to one rule: **a credential you obtained must be USED, and
the use must be read back from the target**. A file you read that contains a string resembling a password
is not a credential until something authenticates with it.

### 8.1 The obtain-use-prove loop, which applies to every family

```bash
# THE LOOP. Every atomic test in section 1 ends here, and a test that stops before step 3 is not a finding.
cat <<'LOOP'
  STEP 1  OBTAIN   the artefact: a file's contents, a memory region, a registry value, a ticket
  STEP 2  EXTRACT  the candidate credential: a password, a hash, a ticket, a key
  STEP 3  USE      authenticate with it against the ORIGINAL target (or a named target)
  STEP 4  PROVE    read something back that the PRE-AUTH identity could not reach
  STEP 5  CONTROL  attempt the SAME read with the PRE-AUTH identity -> it must FAIL

  A test that stops at STEP 1 or STEP 2 is an INFORMATION DISCLOSURE finding, and must be labelled
  as such. The distinction is not pedantry: 'unattend.xml contained a password' and 'the local
  Administrator account was accessed with it' are different findings with different severities.
LOOP
echo
echo "=== the baseline identity, captured BEFORE anything, so the control exists ==="
echo "--- Windows ---"
whoami /all 2>/dev/null | head -20 || echo "  (not Windows)"
echo "--- Linux ---"
id; echo "  CapEff: $(grep CapEff /proc/self/status 2>/dev/null | awk '{print $2}')"
echo "  THE BASELINE IS THE CONTROL. Record what THIS identity can read NOW, so the after-state is"
echo "  comparable. A 'we got SYSTEM' claim with no before-identity is unverifiable."
```

**The baseline identity recorded before anything is the control.** A test that stops at obtaining the
artefact is an information disclosure finding, and the distinction is not pedantry.

### 8.2 Unsupported credentials, and the extraction that must be complete

```powershell
# THE FILESYSTEM FAMILY (section 2): the extraction is only half; the CONTENT must be parsed and USED.
Write-Host "=== THE CLASSIC LOCATIONS, and what each yields ==="
$locations = @(
  @{p='C:\Windows\Panther\Unattend.xml';            y='local or domain account credentials, Base64'},
  @{p='C:\Windows\System32\sysprep\sysprep.xml';    y='the same, in an OEM image'},
  @{p='C:\Windows\System32\sysprep\unattend.xml';   y='the same'},
  @{p='C:\unattend.xml';                            y='the same, at the root'},
  @{p='C:\Windows\System32\GroupPolicy\*';          y='policy settings, sometimes cpassword'},
  @{p='\\<domain>\SYSVOL\<domain>\Policies\**\Groups.xml'; y='cpassword, an AES-encrypted password'},
  @{p='*.ps1 / *.bat / *.config in web roots';      y='hardcoded credentials in scripts'},
  @{p='web.config / appsettings.json';              y='connection strings and secrets'},
  @{p='*.rdp files';                                y='a stored credential target'},
  @{p='Wi-Fi profiles (netsh wlan show profile key=clear)'; y='a PSK'}
)
foreach ($l in $locations) { Write-Host ("  {0,-58} -> {1}" -f $l.p, $l.y) }
Write-Host ""
Write-Host "=== THE cpassword CASE, which is the most over-reported in this family ==="
Write-Host "  A cpassword in SYSVOL's Groups.xml is AES-encrypted with a PUBLICLY KNOWN KEY."
Write-Host "  THE EXTRACTION PROVES NOTHING ON ITS OWN:"
Write-Host "    1. decrypt it to a plaintext"
Write-Host "    2. USE the plaintext to authenticate"
Write-Host "    3. read something back, and run the pre-auth control"
Write-Host "  'we found a cpassword' is an information disclosure finding. It becomes a credential"
Write-Host "  finding ONLY at step 3. And CHECK WHETHER THE ACCOUNT IS STILL ENABLED: a cpassword for"
Write-Host "  a deleted account is not access, and that check is part of the finding."
Write-Host ""
Write-Host "=== the mechanical unmasking, and the completeness requirement ==="
Write-Host "  the extraction must be COMPLETE enough to use: a truncated password or a misread case"
Write-Host "  fails authentication, and the analyst's error is then reported as 'the credential was rotated'."
Write-Host "  VERIFY by authenticating. Nothing else verifies it."
```

**"We found a cpassword" is an information disclosure finding; it becomes a credential finding only after
successful authentication, and the account's enabled state is part of it.**

### 8.3 OS credential dumping, and the artefact each sub-technique leaves

```bash
# T1003's sub-techniques each leave a DIFFERENT artefact. The report must name which, because the
# DETECTION and the REMEDIATION differ entirely.
cat <<'T1003'
  T1003.001 LSASS memory
    artefact : the dump file, and the ACCESS MASK used to obtain it (the handle's granted access)
    how you   obtain it is itself the detection signal: a process opening lsass.exe with
              PROCESS_VM_READ is visible; a signed Microsoft binary doing it may not be
    USE IT    : extract the hashes, then USE them (pass-the-hash, or crack and use the plaintext)
    CONTROL   : the same credential use with a WRONG hash must fail authentication

  T1003.002 SAM
    artefact : the registry hives (SAM + SYSTEM), and the vault for cached secrets
    USE IT    : local credential use; a local admin's hash is local, so NAME THE HOST it works on
    NOTE      : a local account's credential is a LOCAL finding unless the password is REUSED
                (then the reuse itself is the finding, and you demonstrate it on the second host)

  T1003.003 NTDS.dit
    artefact : the database copy, usually with SYSTEM for the boot key
    USE IT    : the extracted hashes; the finding is the DIRECTORY-WIDE access this implies
    NOTE      : a single DC's NTDS read is a domain-wide finding; say so rather than 'we dumped hashes'

  T1003.004 LSA secrets
    artefact : the SECURITY hive + SYSTEM, yielding service-account passwords and DPAPI keys
    USE IT    : the service account's own rights, which may outrank its apparent role
    CONTROL   : a failed authentication with the recovered value means the value is wrong or rotated

  T1003.005 cached domain credentials
    artefact : the SECURITY hive's cache; yields the DCC2 hash for the last N domain logons
    USE IT    : DCC2 is generally NOT crackable in a useful time, so a pass-the-hash is not
                available. THE HONEST FINDING IS 'a domain credential is cached on this host',
                and it is a LATENT finding rather than an access one. SAY SO.

  T1003.006 DCSync
    artefact : the replication request itself, and the account whose rights permitted it
    USE IT    : the extracted credential, with the SAME use-and-prove loop
    NOTE      : the FINDING IS THE REPLICATION RIGHTS, not the hashes. An account that can DCSync
                is the misconfiguration; report THAT.
T1003'
for T in T1003.001 T1003.002 T1003.003 T1003.004 T1003.005 T1003.006; do
  echo "  --- the detection edge for $T ---"
done
echo
echo "=== THE UNIVERSAL USE-AND-PROVE, mechanically ==="
echo "  Windows  : `nxc smb <target> -u <user> -H <hash>` then READ a share or run a command"
echo "  Linux    : `nxc ssh <target> -u <user> -p <pass>` then READ a file outside the baseline"
echo "  THE CONTROL: the SAME command with the WRONG credential must FAIL, and the PRE-AUTH"
echo "  identity's read must FAIL. Both."
```

**A DCC2 hash is generally uncrackable and yields a latent finding rather than an access one — this must be
said.** And for DCSync the finding is the replication right, not the hashes.

### 8.4 The family-level honesty, which is where these tests fail

```bash
cat <<'HONESTY'
  THE FOUR MISREPORTS THIS FILE EXISTS TO PREVENT:

  1. THE ARTEFACT REPORTED AS THE ACCESS.
     'lsass dump obtained' / 'NTDS.dit copied' / 'cpassword found'. Each is step 1 of 5.
     FIX: report the USE and the READ-BACK, and label an un-used artefact as information disclosure.

  2. THE LOCAL FINDING REPORTED AS DOMAIN-WIDE.
     a local Administrator hash works on ONE host. Unless the password is REUSED, that is the scope.
     FIX: name the host. If you find a second host, demonstrate it there and call it reuse.

  3. THE UNCRACKABLE CREDENTIAL REPORTED AS USABLE.
     a DCC2 cache entry and an NTLMv2 machine response are generally not crackable in a useful time.
     FIX: say so, and report the latent exposure rather than a false access claim.

  4. THE ROTATED CREDENTIAL REPORTED AS A FAILED EXTRACTION.
     a credential that fails authentication may be correctly extracted and since ROTATED.
     FIX: distinguish 'we could not use it' from 'it did not work'. The first is your error; the
     second can be a finding in itself if the credential is still VALID for a different service.

  AND THE CONTROL FOR EVERY ONE OF THEM IS THE SAME PAIR:
     the WRONG credential must FAIL, and the PRE-AUTH identity must FAIL.
HONESTY
echo
echo "=== the end-to-end harness ==="
python3 - <<'PY'
print("=== CREDENTIAL ACCESS ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the PRE-AUTH identity and its access were recorded as the BASELINE control",
  "the after-state is meaningless without a before-state"),
 ("the sub-technique is named (T1003.00x), because the artefact and the detection differ",
  "lsass memory, SAM, NTDS, LSA, DCC2, and DCSync are not interchangeable"),
 ("the OBTAINED artefact is recorded with its provenance: the path, the handle's access mask, or the log event",
  "the provenance is the detection edge and the finding's credibility"),
 ("the candidate credential was EXTRACTED and then USED, not merely obtained",
  "step 1 and 2 alone are an information disclosure finding"),
 ("the USE's result was READ BACK from the target's own response",
  "a tool's 'success' line is not access"),
 ("the WRONG-credential control FAILED authentication",
  "without it the success may be from an existing session"),
 ("the PRE-AUTH identity's control read FAILED",
  "the access must be attributable to the obtained credential"),
 ("the SCOPE is stated: which host, which account type, and whether reuse was demonstrated",
  "a local hash is local; a reused password is a separate finding"),
 ("a DCC2 or NTLMv2 response is reported as a LATENT exposure, not as access",
  "they are generally not crackable in a useful time"),
 ("for DCSync, the finding is the REPLICATION RIGHT, and it is reported as such",
  "the misconfiguration is the right, not the hashes"),
 ("for a cpassword, the account's ENABLED state was checked",
  "a credential for a deleted account is not access"),
 ("the TGT/hash lifetime and the environment's patching were considered",
  "a hash is scoped to the environment's NTLM configuration"),
]
for n, how in CHECKS: print("  [ ] %-72s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  baseline : the pre-auth identity and what it could read")
print("  test     : the T1003.00x sub-technique, with its provenance artefact")
print("  extract  : the candidate credential and its source")
print("  use      : the authentication, and the read-back")
print("  control  : the wrong credential's failure and the pre-auth read's failure")
print("  scope    : the host, the account type, and any reuse")
PY
PY
```

---

## 10. RELATED SIBLINGS - LOAD TOGETHER

- [credential-list-engineering](../credential-list-engineering/SKILL.md) - what to do with a plaintext the families here recover
- [ntlm-relay-coercion](../ntlm-relay-coercion/SKILL.md) - an alternative acquisition path for the same accounts
- [active-directory-certificate-services](../active-directory-certificate-services/SKILL.md) - a certificate as an alternative credential
- [linux-privesc-gtfobins-master](../linux-privesc-gtfobins-master/SKILL.md) - the Linux counterpart of the use-it rule
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) - how an acquisition's scope is reported

---

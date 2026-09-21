# 3DS — PROTOCOL MESSAGE REFERENCE

Wire-level reference for EMV 3-D Secure 2.x. Companion to `SKILL.md`.
All field names are as they appear on the wire (camelCase, EMVCo-specified).

---

## 1. MESSAGE CATALOGUE

| Message | Full name | Direction | Purpose |
|---|---|---|---|
| `AReq` | Authentication Request | 3DS Server → DS → ACS | initiate authentication, carry risk data |
| `ARes` | Authentication Response | ACS → DS → 3DS Server | `transStatus`, challenge mandate, `acsURL` |
| `CReq` | Challenge Request | 3DS Server → ACS | hand consumer to challenge UI |
| `CRes` | Challenge Response | ACS → 3DS Server | challenge outcome |
| `RReq` | Results Request | 3DS Server → ACS | poll for out-of-band / decoupled result |
| `RRes` | Results Response | ACS → 3DS Server | final decision for 3RI / decoupled |
| `PReq`/`PRes` | Preparation Request/Response | 3DS Server ↔ DS | 2.2+ pre-auth preparation |
| `Erro` | Error | any → any | protocol-level error |

**3DS 1.0.2 legacy set:** `VEReq`/`VERes` (verification), `PAReq`/`PARes` (payer auth).
These are the pre-2.x equivalents of `AReq`/`ARes` and travel inside an HTML form POST —
see `SKILL.md` §5.

---

## 2. `AReq` — FIELDS THAT DRIVE THE DECISION

### 2.1 Required core

| Field | Example | Note |
|---|---|---|
| `messageType` | `AReq` | |
| `messageVersion` | `2.2.0` | negotiation outcome — must match across the flow |
| `threeDSCompInd` | `Y` | method URL completion indicator |
| `threeDSServerTransID` | UUID | must be identical across every message in the session |
| `deviceChannel` | `02`=browser, `01`=app, `03`=3RI | drives which fields are required |
| `messageCategory` | `01`=PA, `02`=NPA | payment auth vs non-payment (card verification) |
| `transType` | `01`=goods, `03`=check, `28`=3RI | |
| `purchaseAmount` | `1050` | **minor units, no decimal point** |
| `purchaseCurrency` | `978` (EUR) | ISO 4217 numeric |
| `acctNumber` | — | encrypted under DS certificate; never plaintext on the wire |

### 2.2 Risk / device block (`browserInfo`)

| Field | Type | Values |
|---|---|---|
| `browserAcceptHeader` | string | |
| `browserColorDepth` | string int | `1`,`4`,`8`,`15`,`16`,`24`,`32`,`48` |
| `browserIP` | string | dotted quad |
| `browserJavaEnabled` | bool | |
| `browserJavascriptEnabled` | bool | |
| `browserLanguage` | BCP-47 | e.g. `en-US` |
| `browserScreenHeight` / `browserScreenWidth` | string int | |
| `browserTZ` | string int | **offset in minutes from UTC**, e.g. `-300` |
| `browserUserAgent` | string | |

### 2.3 Requestor block

| Field | Values | Meaning |
|---|---|---|
| `threeDSRequestorChallengeInd` | `01` | no preference |
| | `02` | no challenge requested (**requestor preference only — ACS decides**) |
| | `03` | challenge requested |
| | `04` | challenge mandated (e.g. SCA required by law) |
| `threeDSRequestorAuthenticationInd` | `01`=PA, `02`=recurring, `03`=installment, `04`=add card, `05`=maintain card | |
| `threeDSRequestorAuthenticationInfo` | object | prior-auth reference, for MIT / recurring |
| `threeDSRequestorPriorAuthenticationInfo` | object | links this auth to the original SCA that established the mandate |

---

## 3. `ARes` — READING THE RESULT

| Field | Meaning |
|---|---|
| `transStatus` | the decision (see matrix below) |
| `transStatusReason` | why, when `transStatus` is `N`/`U` |
| `authenticationValue` | CAVV/AAV — cryptogram proving authentication; needed by the acquirer |
| `dsTransID` | DS's own transaction ID |
| `acsTransID` | ACS's own transaction ID |
| `eci` | Electronic Commerce Indicator — encodes authentication quality |
| `acsURL` | where to send `CReq` when challenge is mandated |
| `challengeMandated` | derived from `transStatus=C` |

### 3.1 `transStatus` matrix (full)

| Value | Name | Liability | Retryable |
|---|---|---|---|
| `Y` | authenticated | issuer | n/a |
| `N` | not authenticated | none (declined) | no |
| `U` | unable to authenticate | none (no auth occurred) | **yes** |
| `A` | attempted | **merchant** | no |
| `C` | challenge required | pending challenge | n/a |
| `R` | rejected | none (declined) | no |

### 3.2 `transStatusReason` — the useful subset

| Code | Meaning |
|---|---|
| `01` | card authentication failed |
| `02` | unknown device |
| `03` | unsupported device |
| `04` | exceeded authentication attempts |
| `05` | expired card |
| `06` | invalid transaction |
| `07` | invalid amount |
| `08` | invalid cardholder |
| `09` | invalid acquirer |
| `10` | unknown acquirer |
| `11` | invalid merchant |
| `12` | invalid 3DS Server |
| `13` | invalid DS |
| `14` | invalid ACS |
| `15` | unsupported message version |
| `16` | invalid message version number |
| `17` | invalid transaction status |
| `18` | invalid `transStatusReason` |
| `19` | invalid `authenticationValue` |
| `20` | invalid challenge data |
| `21` | invalid `dsTransID` |
| `22` | invalid `acsTransID` |
| `25` | insufficient decoupled window |
| `26` | decoupled max expiry reached |

`U` + reason `01`/`02`/`04` = issuer-side friction. `U` + `14` = ACS outage. Reporting
these identically loses the diagnosis.

---

## 4. `CReq` / `CRes` — CHALLENGE

`CReq` carries:
- `threeDSServerTransID` (echo)
- `acsTransID` (echo)
- `messageVersion` (echo)
- `challengeWindowSize` — `01`–`05`, viewport hint

`CRes` returns `transStatus` again — the **final** decision after the consumer interacted.
A `CReq` sent with a mismatched `acsTransID` is rejected as an invalid session.

Consumer-side challenge types the ACS may present:
- OTP via SMS / email
- issuer app push notification
- biometric (2.3 SPC / WebAuthn)
- security question (legacy, being deprecated)

---

## 5. `RReq` / `RRes` — OUT-OF-BAND RESULTS

Used when the outcome does not arrive via the browser:

| Trigger | Scenario |
|---|---|
| decoupled authentication | consumer approves in a separate channel |
| 3RI (3DS Requestor Initiated) | merchant-initiated without consumer present |
| browser abandoned after `CReq` | recover the decision instead of losing it |

`RReq` carries the transaction identifiers; `RRes` carries the final `transStatus` and,
on success, `authenticationValue`.

**Testing relevance:** a decoupled transaction can be `transStatus=C` for a long window. Polling
`RReq` is the legitimate way to resolve it. Treating the absence of a browser callback as a
failure is incorrect for this transaction class.

---

## 6. VERSION NEGOTIATION

```
3DS Server sends AReq with messageVersion = highest supported (e.g. 2.2.0)
  ├─ DS/ACS supports it      → continue at 2.2.0
  ├─ DS/ACS supports lower   → downgrade to the highest common version
  └─ DS/ACS supports none    → transStatusReason = 15/16, or fall back to 3DS 1.0.2
```

Downgrade is the attack surface worth testing: a forced downgrade to 1.0.2 removes the
risk-based frictionless decision and can change the liability picture. Record the negotiated
`messageVersion` in every transaction record — it is not a constant.

---

## 7. ID CORRELATION — THE THREE IDS

Every session has three independent identifiers. They must all be preserved and cross-checked:

| ID | Issued by | Scope |
|---|---|---|
| `threeDSServerTransID` | 3DS Server (Stripe) | one authentication session |
| `dsTransID` | Directory Server | one DS routing decision |
| `acsTransID` | ACS | one ACS processing instance |

A mismatch between what the merchant holds and what the ACS echoes is an invalid session, not a
retryable error. Correlation across the three is what makes a transaction traceable end-to-end
in an acquirer dispute.

---

## 8. ECI VALUES

| ECI | Meaning |
|---|---|
| `05` | fully authenticated (3DS, `transStatus=Y`) |
| `06` | attempted, not authenticated (`transStatus=A`) — merchant liability |
| `07` | not authenticated / no 3DS, non-secure |

`06` is the encoded form of the liability trap. When reading raw acquirer data rather than the
3DS response, `eci=06` is the marker for "authentication was attempted and failed open".

---

## 9. QUICK FIELD CHEATSHEET

```
Session identity   threeDSServerTransID, dsTransID, acsTransID
Version            messageVersion
Risk decision      transStatus, transStatusReason
Requestor intent   threeDSRequestorChallengeInd, threeDSRequestorAuthenticationInd
Completion flag    threeDSCompInd          (Y / N / U)
Challenge surface  acsURL, challengeMandated, challengeWindowSize
Proof of auth      authenticationValue (CAVV), eci
Amount             purchaseAmount (minor units), purchaseCurrency (ISO 4217 numeric)
Device             browserTZ (minutes), browserLanguage, browserUserAgent, browserColorDepth
```

---

## 10. SOURCE NOTE

Field names and message semantics follow the EMVCo **EMV 3-D Secure Protocol and Core Functions
Specification** (2.1 / 2.2 / 2.3). Implementations vary: a PSP may omit optional fields, and
issuer ACS behaviour is not fully specified anywhere. Always prefer observed behaviour from the
target implementation over the specification when the two disagree, and record both.

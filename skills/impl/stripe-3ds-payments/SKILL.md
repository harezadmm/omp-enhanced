---
name: stripe-3ds-payments
description: >-
  EMV 3-D Secure 2.x and Stripe PaymentIntent authentication testing. Use when a
  payment flow returns next_action, requires_action, or an ACS redirect and you need
  to map the challenge state machine, test SCA/PSD2 exemptions, and report frictionless
  vs challenge outcomes with evidence.
---

# SKILL: Stripe 3DS Payments — EMV 3DS 2.x Authentication Testing

> **AI LOAD INSTRUCTION**: Full operational coverage of EMV 3-D Secure 2.x as exposed through
> Stripe. Covers the three-party protocol (3DS Server / DS / ACS), the `next_action` state
> machine on `PaymentIntent` and `SetupIntent`, the Stripe JS SDK handshake
> (`use_stripe_sdk` + `/v1/3ds2/authenticate`), classic 3DS1 ACS form forwarding, the
> `transStatus` result matrix, SCA/PSD2 exemption selection, and liability shift.
> Base models typically know "3DS is an OTP step" and miss the frictionless path entirely,
> the `threeDSCompInd` flag semantics, and the exemption matrix that decides whether a
> challenge is triggered at all.

## 0. RELATED ROUTING

- [payment-integration](../../core-subjects/payment-integration.md) — Stripe account testing, pre-auth/capture, webhook fuzzing
- [payment-infrastructure-testing-full-spectrum](../../core-subjects/payment-infrastructure-testing-full-spectrum.md) — card validation, BIN, authorize-without-capture
- [api-authorization-and-bola](../api-authorization-and-bola/SKILL.md) — object-level authz on payment objects
- [api-auth-and-jwt-abuse](../api-auth-and-jwt-abuse/SKILL.md) — token handling for gateway dashboards
- [attack-idor-automation](../attack-idor-automation/SKILL.md) — IDOR against payment/intent identifiers

---

## 1. THE THREE-PARTY MODEL — WHO DOES WHAT

3DS2 is not a Stripe feature. It is an EMVCo protocol that Stripe implements as a **3DS Server**.
Three domains exchange messages, and knowing which one failed is the whole diagnostic game.

```
   Merchant ──► 3DS Server  ──►  DS (Directory) ──► ACS (Issuer)
                (Stripe)          (Card scheme)      (Bank)
                                                      │
                                  consumer ───────────┘
                                  (challenge UI)
```

| Role | Owner | What it decides | Failure looks like |
|---|---|---|---|
| **3DS Server** | Stripe | version negotiation, `threeDSServerTransID`, message routing | `next_action` never clears, `/v1/3ds2/authenticate` 400 |
| **DS** (Directory Server) | Visa/Mastercard/Amex | which ACS to route to, BIN→issuer resolution | `threeDSServerTransID` valid but no method URL, unsupported BIN |
| **ACS** | Issuing bank | frictionless vs challenge, `transStatus` | challenge page never completes, OTP loop, `transStatus=U` |

**Diagnostic rule:** an error at the 3DS Server is a *merchant integration* bug. An error at the
ACS is an *issuer/consumer* condition. They are not interchangeable and must be reported separately.

---

## 2. PROTOCOL VERSIONS — WHAT CHANGED

| Version | Key additions | Consequence for testing |
|---|---|---|
| 3DS 1.0.2 | `PaReq` / `PaRes` / `TermUrl`, browser redirect | ACS form forwarding, `MD` (merchant data) round-trip |
| 3DS 2.1 | `AReq`/`ARes`/`CReq`/`CRes`/`RReq`/`RRes`, method URL, frictionless | risk-based decision happens *before* challenge |
| 3DS 2.2 | decoupled auth, 3RI, `whitelisting` / trusted beneficiary | challenge can be deferred entirely offline |
| 3DS 2.3 | SPC (Secure Payment Confirmation), `threeDSRequestorChallengeInd` extensions | WebAuthn-backed challenge |

The single most important structural change from 1.0.2 → 2.x: **2.x decides whether to challenge
before showing anything.** In 1.0.2 every cardholder saw the ACS page. In 2.x the majority of
low-risk transactions return `transStatus=Y` with no consumer interaction at all — that is
the *frictionless* path, and it is where most integration bugs hide.

---

## 3. MESSAGE FLOW — ARREQ TO RRES

### 3.1 Frictionless (no challenge)

```
1. Merchant creates PaymentIntent
2. Card requires 3DS → Stripe returns status=requires_action,
   next_action.type = use_stripe_sdk
   next_action.use_stripe_sdk = { three_ds_server_trans_id, three_ds_method_url, ... }
3. Browser POSTs threeDSMethodData to three_ds_method_url   ← device fingerprinting
4. Stripe POSTs AReq to DS → DS routes to ACS
5. ACS risk-scores → ARes with transStatus=Y (frictionless)
6. Stripe completes PaymentIntent → status = succeeded | requires_capture
```

### 3.2 Challenge

```
… steps 1-5 as above, but ARes returns transStatus=C (challenge required)
6. ACS returns CReq parameters to Stripe
7. Stripe surfaces next_action.redirect_to_url → challenge UI (OTP, app push, biometric)
8. Consumer completes challenge → CRes → ACS → RRes to Stripe
9. Stripe completes PaymentIntent
```

### 3.3 The message set, precisely

| Message | Direction | Carries |
|---|---|---|
| `AReq` | 3DS Server → DS → ACS | `threeDSServerTransID`, `deviceChannel`, `messageVersion`, `purchaseAmount`, `acctNumber` (encrypted) |
| `ARes` | ACS → DS → 3DS Server | `transStatus`, `acsURL`, `challengeMandated` |
| `CReq` | 3DS Server → ACS | challenge request, window size hints |
| `CRes` | ACS → 3DS Server | challenge result |
| `RReq` / `RRes` | 3DS Server ↔ ACS | results request — **out-of-band status polling** for decoupled/3RI |

`RReq`/`RRes` is the one most testers never touch: it lets the merchant ask the ACS for a
final decision instead of waiting on the browser callback. It is how decoupled authentication
and 3RI (3DS Requestor Initiated) transactions report back.

---

## 4. THE `next_action` STATE MACHINE ON STRIPE

`PaymentIntent` and `SetupIntent` share the same `next_action` shape. Treat it as a union type
and dispatch on `next_action.type`.

| `next_action.type` | Meaning | Where to look |
|---|---|---|
| `use_stripe_sdk` | native 3DS2, Stripe JS handles it | `use_stripe_sdk.three_ds_method_url`, `.three_ds_server_trans_id` |
| `redirect_to_url` | browser redirect required (3DS1 ACS, or 3DS2 challenge fallback) | `.redirect_to_url.url`, `.return_url` |
| `display_om_in_app` (legacy) | in-app 3DS1 obfuscation | rare, legacy SDKs |
| `verify_with_microdeposits` | not 3DS — bank verification | unrelated to SCA |
| `cashapp_handle_redirect_or_display_qr_code` | wallet redirect | unrelated to SCA |

### 4.1 Intent status values

| Status | Terminal? | Meaning |
|---|---|---|
| `requires_payment_method` | no | no method attached or last attempt failed |
| `requires_confirmation` | no | attached, awaiting confirm |
| `requires_action` | no | **3DS or other consumer action pending** |
| `processing` | no | gateway working, poll |
| `requires_capture` | yes (partial) | authorized, funds held — capture window running |
| `succeeded` | yes | captured |
| `canceled` | yes | — |

`requires_capture` is the pre-auth hold. The capture window is issuer- and scheme-defined
(commonly 7 days for card, and it is expiry-based — **verify against the live account's
documented window, do not assume**).

### 4.2 The JS handshake, precisely

When `next_action.type = use_stripe_sdk`, Stripe.js does this:

```
1. POST threeDSMethodData (base64url JSON) → three_ds_method_url
     { "threeDSServerTransID": "<id>",
       "threeDSMethodNotificationURL": "<stripe hooks endpoint>" }

2. POST https://api.stripe.com/v1/3ds2/authenticate
     key                  = pk_live_… / pk_test_…
     source               = three_ds_2_source / intent id
     client_secret        = pi_…_secret_…
     three_ds_2_response  = JSON string of browser_info
     browser              = JSON string of browser_info
```

`browser_info` fields that matter:

| Field | Values | Why it matters |
|---|---|---|
| `threeDSCompInd` | `Y` / `N` / `U` | **`Y` = method URL completed.** Sending `Y` without actually running the method flow is the classic integration shortcut and it is detectable by the ACS |
| `threeDSRequestorChallengeInd` | `01`=no preference, `02`=no challenge requested, `03`=challenge requested, `04`=challenge mandated | the merchant's *opinion* — the ACS still decides |
| `browserJavaEnabled` | bool | device signal |
| `browserJavascriptEnabled` | bool | device signal |
| `browserLanguage` | BCP-47 | risk signal — mismatch against card country is a flag |
| `browserColorDepth` | int string | device fingerprint component |
| `browserTZ` | int string, **minutes offset** | risk signal — `0` from a non-UTC card is anomalous |
| `browserUserAgent` | full UA | device fingerprint component |
| `threeDSServerTransID` | echoed from `next_action` | must match exactly; mismatch = invalid session |

**Testing note — signal coherence.** `threeDSCompInd=Y` asserts the method URL ran. If the
browser signals (`browserTZ`, `browserLanguage`, `browserUserAgent`) do not form a coherent
device profile, the ACS risk engine scores higher and forces a challenge. Coherence, not
spoofing, is what determines frictionless vs challenge — this is the single highest-value
thing to understand about the whole protocol.

---

## 5. 3DS1 / ACS REDIRECT FORWARDING

Older BINs and some issuers still route to a classic ACS page. The flow is HTML form forwarding:

```
1. GET next_action.redirect_to_url.url          (hooks.stripe.com/redirect/authenticate/…)
2. Parse the HTML: <form action="…"> and hidden <input name="" value="">
     typical fields: PaReq, MD, TermUrl, and on 2.x fallbacks CReq
3. POST the parsed field set to the ACS endpoint
4. ACS returns ANOTHER form (the completion form)
5. POST that second form back to the Stripe completion hook (return / TermUrl)
6. Re-fetch the PaymentIntent to read the final status
```

**Two POSTs, not one.** Step 3 is the challenge submission; step 5 is the return leg. A tester
who only does step 3 sees the intent stuck at `requires_action` and wrongly reports failure.

**Parsing discipline.** The form fields are not stable across issuers. Extract:
- `<form ... action="...">` → endpoint
- every `<input ... name="..." value="...">` → field set
- `location.href = "..."` in inline JS → fallback endpoint when there is no form

Do **not** hardcode the method notification URL or the return URL. Both are per-session values
supplied by Stripe, and a hardcoded value silently breaks every future run.

---

## 6. `transStatus` RESULT MATRIX

This is the authoritative outcome set. `Y` and `N` are not the whole story.

| Value | Meaning | Action |
|---|---|---|
| `Y` | authenticated | proceed to authorization |
| `N` | not authenticated / failed | do not authorize, treat as decline |
| `U` | unable to authenticate | **retryable** — technical failure at ACS or DS |
| `A` | attempted | authentication attempted but not completed; **liability stays with merchant** |
| `C` | challenge required | challenge flow must complete |
| `R` | rejected | issuer rejected — do not retry |

`U` vs `N` vs `A` is the distinction that matters in reporting. `N` is a decision. `U` is an
outage. `A` is a soft failure that shifts liability back to the merchant — and it is the one
most often misclassified as success.

---

## 7. SCA / PSD2 EXEMPTION MATRIX

Under PSD2 (EEA), SCA is the default and exemptions are the exception. Knowing which exemption
applies explains why a given transaction never showed a challenge.

| Exemption | Article | Condition | Notes |
|---|---|---|---|
| **Low value** | RTS Art. 16 | ≤ €30 per transaction | cumulative counter: max 5 consecutive or €100 total since last SCA, then SCA required |
| **TRA** (Transaction Risk Analysis) | RTS Art. 18 | gateway fraud rate below reference, amount under threshold | thresholds per PSP fraud band; **amount caps: €100 / €250 / €500** depending on the band |
| **MIT** (Merchant Initiated Transaction) | RTS Art. 13 / PSD2 Art. 12 | recurring after initial SCA | requires a stored credential framework (`off_session` + `mandate`) |
| **Trusted beneficiary / whitelist** | RTS Art. 13.1 | consumer whitelisted the merchant with the issuer | issuer-enforced, not merchant-controlled |
| **Secure corporate payment** | RTS Art. 17 | corporate card process | out of consumer scope |
| **One-leg transaction** | RTS Art. 15 | issuer or acquirer outside EEA | *both* legs must be checked |
| **Contactless** | RTS Art. 11 | physical, ≤ €50 | not applicable to e-commerce |

**Testing discipline.** An exemption is *claimed*, not *granted* — the issuer can reject the
exemption and force a challenge anyway. Therefore: never assert "exemption applied" from the
absence of a challenge. Assert it only from the response fields that say so, and record the
amount, currency, and cumulative counter state alongside it.

**Cumulative counters.** The low-value exemption counter is per-card and time-windowed. Testing
it requires tracking attempts in order, not in isolation. Reset behaviour after a successful
SCA must be recorded explicitly.

---

## 8. LIABILITY SHIFT

| Outcome | Liability |
|---|---|
| `transStatus=Y` (frictionless or challenge) | issuer |
| `transStatus=A` (attempted) | **merchant** |
| `transStatus=N` / `R` | transaction declined, no shift |
| 3DS not attempted at all | merchant |
| Exemption claimed and accepted by issuer | merchant, unless issuer agreed in writing |

The `A` case is the trap. It looks like an authentication happened. It did not. If the goal is
liability shift, `A` is a failure, not a soft success.

---

## 9. STRIPE SURFACE MAP

| Surface | Endpoint / field | Use |
|---|---|---|
| Create intent | `POST /v1/payment_intents`, `/v1/setup_intents` | `amount`, `currency`, `capture_method`, `payment_method` |
| Retrieve intent | `GET /v1/payment_intents/{id}?client_secret=…&key=pk_…` | status, `next_action`, `last_payment_error` |
| Confirm | `POST /v1/payment_intents/{id}/confirm` | attach + confirm in one call |
| Capture | `POST /v1/payment_intents/{id}/capture` | `amount_to_capture` for partial capture |
| Cancel | `POST /v1/payment_intents/{id}/cancel` | releases the hold |
| 3DS2 auth | `POST /v1/3ds2/authenticate` | the JS handshake above |
| Intent ID prefixes | `pi_` payment, `seti_` setup | dispatch endpoint choice on prefix |
| Client secret shape | `pi_<id>_secret_<hash>` | the intent ID is the part before `_secret_` |

**Key discipline.** `pk_*` is publishable and safe in browser context; `sk_*` is secret and must
never be used from a client. A retrieve with `key=pk_live_…` requires the matching
`client_secret` — that pair *is* the authorization. Treat any transcript containing both as
sensitive evidence.

**Radar.** `charge.radar_risk_score` and the rule engine can independently block a charge
*after* successful 3DS. A `succeeded` 3DS result with a blocked charge is not an integration
failure — it is a risk decision, and the two layers must be reported separately.

---

## 10. WEBHOOK EVENT SET

| Event | Fires when |
|---|---|
| `payment_intent.created` | intent object created |
| `payment_intent.requires_action` | 3DS/consumer action pending |
| `payment_intent.amount_capturable_updated` | authorization succeeded, hold placed |
| `payment_intent.succeeded` | captured |
| `payment_intent.payment_failed` | terminal failure, `last_payment_error` populated |
| `payment_intent.canceled` | canceled |
| `setup_intent.succeeded` | credential stored (MIT/mandate prerequisite) |
| `charge.dispute.created` | chargeback opened — post-`A`-status risk marker |

**Signature verification.** Stripe signs with `Stripe-Signature: t=<ts>,v1=<hmac>`. Verification
requires the raw body, the endpoint secret, a timestamp tolerance window, and a
constant-time comparison. A tolerant window or a skipped comparison is the finding, not a
footnote.

**Idempotency.** Webhooks retry. Event handlers must dedupe on `event.id`. A handler that
processes the same event twice is a duplicate-fulfilment bug — worth testing explicitly.

---

## 11. TESTING METHODOLOGY

### 11.1 Establish the baseline
1. Create the intent, record `id`, `status`, `next_action.type`, `next_action` body in full.
2. Record amount, currency, `capture_method`, and the card BIN and country.
3. Record whether the intent is `pi_` or `seti_`.

### 11.2 Classify the path
| Observation | Path | Next step |
|---|---|---|
| `next_action.type=use_stripe_sdk` | 3DS2 native | §4.2 handshake |
| `next_action.type=redirect_to_url` | 3DS1 or 2.x fallback | §5 form forwarding |
| no `next_action`, `status=succeeded` | frictionless or exempt | §7 exemption check |
| `status=requires_capture` | pre-auth hold | capture-window test |

### 11.3 Exemption probe
Vary **one** variable at a time and record the `next_action` delta:
- amount across the €30 low-value boundary
- email/phone country vs card country
- new vs returning cardholder on the same merchant
- `capture_method=manual` vs `automatic`
- MIT with vs without a prior SCA-established mandate

### 11.4 Outcome verification
- Never read success from the browser UI or the redirect landing page alone.
- Always re-fetch the intent and read `status` + `last_payment_error` from the API.
- Cross-check against the webhook stream. Disagreement between the two is itself a finding.

### 11.5 Evidence standard
For every run capture: intent ID, timestamp, request set, response set, `transStatus` where
observable, final `status`, and the webhook events received. A `transStatus` with no
corresponding intent status is an incomplete observation — say so rather than guessing.

---

## 12. FIELD NOTES / PITFALLS

**Two POSTs in 3DS1.** Submitting only the challenge form leaves the intent at `requires_action`.
The return-leg POST is mandatory. (§5)

**`threeDSCompInd=Y` without running the method flow.** Asserts a step that did not happen.
The ACS risk engine treats incoherent signals as higher risk and forces challenge. (§4.2)

**`transStatus=A` read as success.** It is not authenticated, and liability stays with the
merchant. The most common misreport in 3DS testing. (§6, §8)

**Hardcoded notification / return URLs.** Both are per-session values. Hardcoding them produces
a script that works exactly once. (§5)

**Silent exception swallowing.** Network-layer 3DS code that discards its own response bodies
produces no usable evidence. Every request in the flow must retain its response for the report.
(§11.5)

**Client secret treated as non-sensitive.** `pi_…_secret_…` *is* the authorization for that
intent. Leaking it into logs is a finding on its own. (§9)

**Assuming `requires_capture` never expires.** The window is scheme/issuer defined and
expiry-based. Verify per account; do not hardcode a number. (§4.1)

**Exemption assumed from the absence of a challenge.** Exemptions are claimed, not granted.
Read the fields, not the silence. (§7)

**Radar failure conflated with 3DS failure.** Risk scoring runs after authentication. Separate
the layers in the report. (§9)

---

## 13. REFERENCE FAILURE / DIAGNOSTIC TABLE

| Symptom | Likely layer | Check |
|---|---|---|
| `next_action` never appears | 3DS Server / merchant | intent params, `payment_method` attach, amount validity |
| `use_stripe_sdk` present, authenticate 400 | 3DS Server | `source` field resolution, `client_secret`/`pk_` pairing |
| method URL call succeeds, no progress | DS | `threeDSServerTransID` match, unsupported BIN |
| challenge page loads, never completes | ACS | consumer action, OTP delivery, ACS downtime → expect `U` |
| intent stuck at `requires_action` after challenge | integration | missing return-leg POST (§5) |
| `transStatus=U` | ACS/DS | retryable — log as outage, not decline |
| `transStatus=A` | ACS decision | attempted-not-authenticated; liability retained |
| 3DS succeeded, charge blocked | Radar | separate risk layer (§9) |
| webhook arrives twice | merchant | dedupe on `event.id` (§10) |

---

## 14. ETHICS AND AUTHORIZATION GATE

Everything in this skill operates against **payment infrastructure you are authorized to test** —
your own Stripe account in test mode, a client account under a signed scope, or an issuer/PSP
sandbox. The protocol is described in full because defensive engineers and integration testers
need the full state machine to build correct systems and to recognise the failure modes above.

Specifically out of scope: resolving 3DS challenges belonging to cards or accounts you do not
own, using `pk_live` / `client_secret` pairs harvested from third parties, and automating a
challenge response on behalf of a consumer who has not consented. Those are not testing — they
are fraud, and they are the reason `transStatus=A` liability rules exist.

Confirm scope in writing before touching a live mode account. Record the authorization
reference in the report header. Evidence from an unauthorized run is not evidence.

---

## 15. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did you reach `transStatus` = `Y`/`A` **without completing a real challenge**? | the authentication was bypassed |
| 2 | Was there a **control** - a card that correctly triggers the challenge? | the challenge path works and you avoided it |
| 3 | Did the payment **complete and settle** after the bypass? | the impact is money, not a status code |
| 4 | Which defect: **exemption misuse, `transStatus` trust, downgrade, or replay**? | the fix location |
| 5 | Did the **3DS Server** or the ACS log the anomaly? | the detection result |
| 6 | Did you use **Stripe test cards and test mode** only? | engagement integrity |
| 7 | Did you **not attempt** a real-card or real-merchant test? | legal boundary |

**A payment that settles with `transStatus = Y` and no challenge, alongside a card that correctly
challenges, is the bar.** A configuration that looks permissive is a hypothesis; the settled payment is
the finding.

---

## 16. EXECUTION PRIMITIVES

3DS/SCA findings are proven by **a payment that settles without the required challenge, with a
challenge-required control card, all in Stripe test mode**. Every block ends at a settled test payment or
a recorded `transStatus`.

### 16.1 The test-mode gate, and the card matrix

```bash
# THE GATE: everything below runs against Stripe TEST MODE with STRIPE TEST KEYS. No exceptions.
test "$(printf '%s' "$STRIPE_KEY" | cut -c1-8)" = "sk_test_" \
  || { echo "REFUSING: this key is not a test key. Stop."; exit 1; }
echo "test key confirmed: ${STRIPE_KEY:0:12}..."
echo
echo "=== THE 3DS TEST CARD MATRIX - this is the control set ==="
cat <<'CARDS'
4000 0000 0000 3055  3DS required, challenge flow        -> CONTROL: must challenge
4000 0000 0000 3063  3DS required, frictionless flow      -> must NOT challenge, MUST carry transStatus
4000 0000 0000 3224  3DS required, challenge FAILS        -> must refuse the payment
4000 0000 0000 3097  3DS required, challenge not supported -> the ACS-unavailable path
4000 0000 0000 3089  3DS required, attempt acknowledged   -> transStatus = A, liability path
4000 0000 0000 0259  3DS required, then declines offline  -> the refusal path
4000 0000 0000 9995  insufficient funds                   -> unrelated to SCA
4000 0000 0000 0002  generic decline                       -> unrelated to SCA
4000 0025 0000 3155  requires 3DS authentication (IN)     -> the Indian RBI path
CARDS
echo "  ^ 3055 is the CONTROL. If it does not challenge, your integration is wrong, not the target."
```

**The 3055 card is the control.** If the challenge-required card does not challenge, the finding is about
your integration, and everything downstream of that is worthless.

### 16.2 The PaymentIntent flow, and reading `next_action`

```python
# drive the flow in test mode and record the state machine's transitions
import stripe, json, os, time
stripe.api_key = os.environ["STRIPE_KEY"]
assert stripe.api_key.startswith("sk_test_"), "REFUSING: not a test key"

def run_flow(card, tag):
    pi = stripe.PaymentIntent.create(
        amount=2000, currency="eur",
        payment_method_data={"type": "card", "card": {"number": card, "exp_month": 12,
                                                      "exp_year": 2034, "cvc": "314"}},
        payment_method_types=["card"],
        confirm=True, return_url="https://example.test/return",
        # the exemption request is what most of these findings turn on
        payment_method_options={"card": {"request_three_d_secure": "any"}},
    )
    print(f"--- {tag}  {card}")
    print("    id           :", pi.id)
    print("    status       :", pi.status)
    na = pi.next_action
    if na:
        print("    next_action  :", na.type, "->", getattr(na, "redirect_to_url", None) and na.redirect_to_url.url[:80])
    print("    last_payment_error:", (pi.last_payment_error or {}).get("code") if pi.last_payment_error else None)
    # the 3DS result lives on the charge's payment_method_details
    try:
        ch = stripe.Charge.retrieve(pi.latest_charge)
        pmd = ch.payment_method_details.card
        print("    three_d_secure:", json.dumps(pmd.three_d_secure or {}, indent=None)[:200])
        print("    authenticated :", getattr(pmd.three_d_secure, "authenticated", None))
        print("    transStatus   :", getattr(pmd.three_d_secure, "result", None))
    except Exception as e:
        print("    charge lookup:", type(e).__name__)
    print("    CONTROL NOTE : compare this row against 4000000000003055, which MUST challenge")
    return pi

# the control first, then the exemption-seeking cards
run_flow("4000000000003055", "CONTROL - challenge required")
run_flow("4000000000003063", "frictionless - must carry a transStatus")
run_flow("4000000000003089", "attempt acknowledged (transStatus = A)")
run_flow("4000000000003224", "challenge fails - must refuse")
```

**The control runs first, and its `three_d_secure` block is the reference.** Every other row is only
interesting next to it, and the exemption request is where most of these findings originate.

### 16.3 The exemption matrix, which is the usual defect surface

```python
# the SCA exemptions, each a separate claim about the merchant's configuration
EXEMPTIONS = {
 "low_value":            ("the amount is below the issuer's threshold (commonly EUR 30)", "repeated low-value payments"),
 "tra_exemption":        ("a TRA was performed within the last 90 days", "the TRA must be genuine and within the window"),
 "moto":                 ("the transaction is mail-order/telephone-order", "MOTO must not be used for a web checkout"),
 "merchant_initiated":   ("a MIT against a stored credential with a mandate", "requires a genuine mandate and the first CIT authenticated"),
 "recurring_mit":        ("the first payment was authenticated and this is a subsequent one", "the FIRST payment must have authenticated"),
 "trusted_beneficiary":  ("the beneficiary is on the customer's trusted list", "requires the customer to have enrolled them"),
 "secure_corporate":     ("a corporate card is used with the corporate scheme", "verify the scheme actually applies"),
 "one_leg_out":          ("one leg of the transaction is outside the EEA", "verify the geography"),
}
print("%-22s %-52s %s" % ("exemption","what it requires","the usual misuse"))
for k, (req, misuse) in EXEMPTIONS.items(): print("%-22s %-52s %s" % (k, req[:52], misuse[:44]))
print()
print("TEST EACH CLAIM against the actual request the integration builds:")
for k, (req, misuse) in EXEMPTIONS.items():
    print(f"  {k:22} -> does the request rely on this? is the precondition GENUINELY met?")
print()
print("THE FINDING SHAPE: an exemption applied where its precondition is not met, in a way that")
print("results in a SETTLED payment with no authentication and no `transStatus` of Y/A.")
```

**An exemption with an unmet precondition is the defect.** The report should name the exemption, the
precondition, and the evidence that it was not met.

### 16.4 The `transStatus` trust, and the downgrade

```bash
# the ACS response is signed; an integration that trusts a client-supplied transStatus is the defect
echo "=== 1) THE transStatus TRUST ==="
echo "look for a request where the CLIENT supplies a 3DS result rather than the ACS."
echo "the 3DS Method URL / CReq / CRes exchange must be server-to-server with a signed CRes."
echo
echo "=== 2) THE DOWNGRADE ==="
echo "a merchant that falls back to a NON-3DS attempt when the ACS is unavailable turns a"
echo "'not authenticated' into a settled payment. Test: use 4000000000003097 (challenge not supported)"
echo "and check whether the payment proceeds unchallenged."
echo
echo "=== 3) THE VERSION DOWNGRADE ==="
echo "3DS2 may silently fall back to 3DS1, which lacks the same data. Check the version in the"
echo "response and whether the flow differs from what was requested."
echo
echo "=== 4) THE REPLAY ==="
echo "a CRes is single-use. Replaying one, or reusing a completed authentication for a new"
echo "PaymentIntent, is the replay defect. Test: complete one flow, then reuse its identifier"
echo "on a second PaymentIntent and observe whether it is accepted."
echo
echo "=== 5) THE CANCELLATION PATH ==="
echo "a cancelled challenge that still settles, or a 'back' navigation that completes the payment,"
echo "is a real and frequently reported defect. Test the cancel URL and the browser back button."
```

**Clients must never supply `transStatus`.** A signed, server-to-server `CRes` is the only acceptable
source, and the replay test is one reuse of one completed authentication.

### 16.5 The webhook truth, which is what settled

```python
# the payment's final state comes from the webhook, not the client's redirect
import json
EVENTS = {
 "payment_intent.succeeded":                 "the payment settled - the impact",
 "payment_intent.payment_failed":            "the refusal path",
 "payment_intent.requires_action":           "a challenge was required at this point",
 "charge.succeeded":                         "the charge-level settle",
 "charge.dispute.created":                   "a dispute follows a liability shift",
 "radar.early_fraud_warning.created":        "a fraud signal",
 "setup_intent.succeeded":                   "a stored credential was created",
}
print("%-42s %s" % ("event", "what to correlate"))
for k, v in EVENTS.items(): print("%-42s %s" % (k, v))
print()
print("THE CORRELATION TABLE for the report:")
print("%-22s %-10s %-14s %-12s %s" % ("card","authenticated","transStatus","pi.status","webhook"))
print("%-22s %-10s %-14s %-12s %s" % ("4000...3055 (ctrl)","true","Y","succeeded","payment_intent.succeeded"))
print("%-22s %-10s %-14s %-12s %s" % ("<the test card>","?","?","?","?"))
print()
print("A row where authenticated=false and transStatus is NOT Y/A, yet the payment SETTLED, is the finding.")
print("A row where the control did not authenticate is an integration problem - fix that before reporting.")
```

**A settled payment with `authenticated = false` is the finding.** The webhook is the settlement truth, and
the client redirect is not.

### 16.6 The end-to-end harness

```bash
python3 - <<'PY'
import os, stripe, json
stripe.api_key = os.environ.get("STRIPE_KEY", "")
if not stripe.api_key.startswith("sk_test_"):
    print("REFUSING: STRIPE_KEY must be a TEST key (sk_test_...). This harness will not run live.")
    raise SystemExit(0)

CARDS = [("4000000000003055","CONTROL challenge required"),
         ("4000000000003063","frictionless"),
         ("4000000000003089","attempt acknowledged"),
         ("4000000000003224","challenge fails"),
         ("4000000000003097","challenge not supported")]

print("%-22s %-14s %-12s %-14s %s" % ("card","authenticated","3ds-result","pi.status","tag"))
for num, tag in CARDS:
    try:
        pi = stripe.PaymentIntent.create(
            amount=2000, currency="eur",
            payment_method_data={"type":"card","card":{"number":num,"exp_month":12,"exp_year":2034,"cvc":"314"}},
            payment_method_types=["card"], confirm=True,
            return_url="https://example.test/return",
            payment_method_options={"card":{"request_three_d_secure":"any"}})
        auth = res = "-"
        if pi.latest_charge:
            try:
                pmd = stripe.Charge.retrieve(pi.latest_charge).payment_method_details.card
                auth = str(getattr(pmd.three_d_secure, "authenticated", "-"))
                res  = str(getattr(pmd.three_d_secure, "result", "-"))
            except Exception: pass
        print("%-22s %-14s %-12s %-14s %s" % (num, auth, res, pi.status, tag))
    except stripe.error.StripeError as e:
        print("%-22s %-14s %-12s %-14s %s" % (num, "-", "-", "ERROR", str(e)[:40]))
print()
print("READ THE TABLE:")
print("  CONTROL row must show authenticated=true and a 3DS result - if not, the integration is wrong")
print("  any row that SETTLED with authenticated=false and no 3DS result in a non-exempt context")
print("  IS the finding. Correlate it with the webhook before reporting.")
print()
print("THEN: correlate with the webhook events, and confirm the settlement independently.")
PY
```

**The control row first, then the correlation.** An integration whose control does not authenticate cannot
produce a valid finding in this family.

---

## 17. EVIDENCE STANDARD — 3DS ARTEFACTS

| Item | Why |
|---|---|
| Confirmation that the test ran in **test mode with a test key** | the legal and engagement boundary |
| The **control card's full result** (`3055`) | the reference every other row is compared against |
| The **test card used**, and its expected 3DS behaviour | reproducibility and the expected-versus-actual |
| The **`authenticated` flag and the `transStatus` result** | the authentication state, from the API |
| The **`PaymentIntent` status** and the **webhook event** | the settlement truth |
| The **exemption claimed**, and the evidence its precondition was not met | the fix location |
| The **3DS version** actually used, against the version requested | the downgrade finding |
| Whether the **CRes was signed and server-to-server** | the `transStatus` trust finding |
| Any **replay** performed, and the two identifiers involved | the replay finding |
| Confirmation that **no live key, real card, or real merchant** was used | engagement integrity |

Report the **bypass and the control**: "the control card `4000 0000 0000 3055` produced
`authenticated: true` with a `three_d_secure.result` of `Y` and a `requires_action` state that was
resolved by the test ACS, which confirms the integration performs authentication correctly. The card
`4000 0000 0000 3089` settled as `PaymentIntent.status: succeeded` with
`authenticated: false` and `three_d_secure.result: A`, and the corresponding
`payment_intent.succeeded` webhook arrived, so the payment settled on an attempt-acknowledged result. The
request carried `request_three_d_secure: any` with no exemption flag, so the `A` result was not described
by any of the exemption preconditions in 16.3, and the subsequent
`charge.dispute.created` for the same charge removed the merchant's liability-shift protection, which is
the impact. The card `4000 0000 0000 3097` likewise settled with no `three_d_secure` block at all", never
"the merchant can bypass 3DS".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A payment that **failed** without a challenge | the refusal path works |
| A **frictionless** flow with `transStatus = Y` | that is the correct outcome of a genuine risk assessment |
| A **`transStatus = A`** used where an exemption precondition genuinely applies | the exemption is legitimate; verify the precondition |
| A **low-value** payment settled without a challenge | the low-value exemption applies below the threshold |
| A **MIT/recurring** payment without a challenge | the preconditions are the CIT having authenticated; verify them |
| A **test-mode** result reported as a live-merchant vulnerability | verify the mode, and label the evidence |
| A **client-side redirect** with no challenge observed | the ACS may challenge out-of-band; read the charge, not the redirect |
| A finding from **your own test Stripe account** with a permissive configuration | tests the account, not the merchant |
| An **`authenticated: false`** on a payment that did NOT settle | no impact |
| A finding where **the control card also failed to authenticate** | the integration is wrong; fix it first |
| Any test using a **live key, a real card, or a real merchant** | out of scope and unlawful |

**A settled payment, `authenticated: false`, with the `3055` control authenticating correctly.** Refused
payments and legitimate frictionless results are this family's two standard non-findings.

---

## 18. REMEDIATION REFERENCE — 3DS INTEGRATION HARDENING

1. **Trust only the signed, server-to-server ACS response for `transStatus`; never accept an authentication result supplied by the client or the browser** - a client-supplied result is the defect that makes every other control meaningless.
2. **Enforce a single-use, bound CRes: tie the authentication to the specific `PaymentIntent` and reject any reuse** - it removes the replay family.
3. **Fail closed when the ACS is unavailable, rather than falling back to a non-3DS attempt** - the downgrade turns "not authenticated" into a settled payment.
4. **Verify the preconditions of every exemption before applying it, and record the evidence for each one** - an exemption with an unmet precondition is the defect, and the audit trail is what makes it defensible.
5. **Never use MOTO, TRA, or merchant-initiated exemptions for a web or in-app checkout** - those exemptions are for their own channels.
6. **Request and record the 3DS version explicitly, and alert when the version actually used is lower than the one requested** - the silent downgrade to 3DS1 is a detection-worthy event.
7. **Require a genuine prior authenticated CIT before any recurring MIT is attempted, and store the mandate** - the MIT exemption depends entirely on that first authentication.
8. **Treat a cancelled or abandoned challenge as incomplete: it must never settle** - the cancellation and browser-back paths are common and under-tested.
9. **Correlate the settlement with the webhook rather than the client redirect, and require `authenticated = true` for any transaction you intend to claim liability-shift protection on** - the redirect is not the settlement.
10. **Log the authentication result, the exemption claimed, and the precondition evidence for every transaction, and alert on a settled payment with no authentication and no exemption** - that correlation is the detection.
11. **Test the full test-card matrix, including the control card, on every release and after every Stripe API version change** - the 3DS behaviour is version-sensitive and regresses silently.

---

## 19. RELATED SIBLINGS - LOAD TOGETHER

- [business-logic-vulnerabilities](../business-logic-vulnerabilities/SKILL.md) - the flow-abuse context this belongs to
- [race-condition](../race-condition/SKILL.md) - the sibling defect on the payment path
- [api-authorization-and-bola](../api-authorization-and-bola/SKILL.md) - the authorization defects that compose with a payment bypass
- [attack-idor-automation](../attack-idor-automation/SKILL.md) - the enumeration that finds other customers' payment objects
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) - the report this evidence feeds

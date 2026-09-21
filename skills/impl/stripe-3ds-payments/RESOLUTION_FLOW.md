# 3DS — RESOLUTION FLOW IMPLEMENTATION

Reference implementation for driving a Stripe `PaymentIntent` through 3DS authentication,
derived from an observed working resolver and hardened for testing use.

Companion to `SKILL.md` (§4.2, §5, §11) and `PROTOCOL.md`.

---

## 0. PROVENANCE AND HARDENING NOTES

This implementation was derived from a payment-flow script found in the workspace at
`Stripe3Ds/3ds_bypasser.py` (319 lines). That original:

- had the correct protocol sequence (method URL → `/v1/3ds2/authenticate` → challenge → status),
- imported `from curl_compat import ChromeSession`, **a module that does not exist in this
  package** — so it was non-runnable as shipped,
- swallowed every error with bare `except Exception: pass`,
- discarded every HTTP response body,
- hardcoded the method-notification URL,
- defaulted its API key to the literal placeholder `pk_live_placeholder`.

The version below fixes all six: the transport is an injectable interface, every error is
captured, every response body is retained for evidence, session-scoped values are parameters
rather than constants, and a missing key fails loudly.

**The original file is retained unmodified at `Stripe3Ds/3ds_bypasser.py` for provenance.**
Do not execute it. Use this reference.

---

## 1. TRANSPORT ABSTRACTION

The original's missing `curl_compat` dependency is replaced by a narrow protocol. Supply any
HTTP client that satisfies it — `httpx.AsyncClient`, `aiohttp.ClientSession` wrapped, or a
curl-impersonate binding.

```python
from typing import Protocol, Any

class HttpSession(Protocol):
    async def post(self, url: str, *, data: dict | str, headers: dict,
                   timeout: float, allow_redirects: bool = True) -> Any: ...
    async def get(self, url: str, *, headers: dict, timeout: float,
                  allow_redirects: bool = True) -> Any: ...
```

A response object must expose `.status_code`, `.text` and `.json()`. If the transport cannot
produce those, wrap it so it can — **evidence depends on retaining bodies.**

---

## 2. EVIDENCE LOG

Every request and response in the flow is recorded. This is the single most important change
from the original: a resolution with no evidence is not a testing result.

```python
import time, json
from dataclasses import dataclass, field

@dataclass
class Trace:
    steps: list = field(default_factory=list)

    def record(self, phase: str, request: dict, response: dict | None,
               error: str | None = None) -> None:
        self.steps.append({
            "phase": phase,
            "t": round(time.time(), 3),
            "request": request,
            "response": response,
            "error": error,
        })

    def to_json(self) -> str:
        return json.dumps(self.steps, indent=2, default=str)
```

Rules for what goes into `request`:
- **redact** `client_secret` and any `sk_*` to a fingerprint (`first6…last4`, length),
- keep `pk_*` in full (publishable),
- keep full response bodies, including 4xx bodies — the error body is the finding.

---

## 3. HELPERS

```python
import base64, json, re
from urllib.parse import urlencode

def b64url_encode(data: bytes) -> str:
    return base64.b64encode(data).decode().rstrip("=").replace("+", "-").replace("/", "_")

def b64url_decode(s: str) -> bytes:
    s = s.replace("-", "+").replace("_", "/")
    s += "=" * (-len(s) % 4)
    return base64.b64decode(s)

def parse_html_form(html: str) -> tuple[str | None, dict]:
    """Extract <form action> endpoint and all <input name/value> fields.

    Returns (endpoint, fields). Endpoint falls back to an inline
    `location.href = "..."` when no form element is present.
    """
    endpoint = None
    m = re.search(r'<form[^>]+action=["\']([^"\']+)["\']', html, re.I)
    if m:
        endpoint = m.group(1)
    fields = {}
    for tag in re.finditer(r'<input[^>]+>', html, re.I):
        t = tag.group(0)
        n = re.search(r'name=["\']([^"\']+)["\']', t, re.I)
        v = re.search(r'value=["\']([^"\']*)["\']', t, re.I)
        if n:
            fields[n.group(1)] = v.group(1) if v else ""
    if not endpoint:
        m2 = re.search(r'location\.href\s*=\s*["\']([^"\']+)["\']', html)
        if m2:
            endpoint = m2.group(1)
    return endpoint, fields

def redact(secret: str | None) -> str | None:
    if not secret:
        return None
    return f"{secret[:6]}…{secret[-4:]} (len={len(secret)})"
```

`parse_html_form` handles both the Stripe redirect page and the ACS completion page — the two
occurrences of the same parsing problem in the flow.

---

## 4. 3DS2 NATIVE FLOW (`use_stripe_sdk`)

```python
class Stripe3DS:
    AUTH_URL = "https://api.stripe.com/v1/3ds2/authenticate"
    PI_URL   = "https://api.stripe.com/v1/payment_intents/{id}"
    SI_URL   = "https://api.stripe.com/v1/setup_intents/{id}"

    def __init__(self, session: HttpSession, pk_key: str,
                 trace: Trace, profile: dict | None = None):
        if not pk_key or pk_key == "pk_live_placeholder":
            raise ValueError("publishable key required — refusing placeholder default")
        self.s = session
        self.pk = pk_key
        self.trace = trace
        self.profile = profile or {}

    # ── device signal block ────────────────────────────────────────────────
    def browser_info(self, server_trans_id: str) -> dict:
        p = self.profile
        return {
            "threeDSCompInd": "Y",
            "threeDSRequestorChallengeInd": p.get("challenge_ind", "01"),
            "threeDSServerTransID": server_trans_id,
            "browserJavaEnabled": p.get("java_enabled", False),
            "browserJavascriptEnabled": True,
            "browserLanguage": p.get("language", "en-US"),
            "browserColorDepth": str(p.get("color_depth", "24")),
            "browserTZ": str(p.get("tz_offset", "-300")),
            "browserUserAgent": p.get("user_agent", DEFAULT_UA),
        }
```

**`browser_info` must be coherent.** If `threeDSCompInd` is `Y`, the method flow must actually
have run (§4.1). If `browserTZ`/`browserLanguage` disagree with the card's issuing region, the
ACS risk engine raises the score and forces a challenge. Coherence is the variable that decides
frictionless vs challenge — not the absence of data.

### 4.1 Method URL step

```python
    async def method_url(self, intent: dict) -> dict | None:
        sdk = intent.get("use_stripe_sdk") or intent.get("three_ds_2_intent") or {}
        if not isinstance(sdk, dict):
            return None
        server_trans_id = (sdk.get("three_ds_server_trans_id")
                           or sdk.get("three_ds_2_server_trans_id"))
        method_url = sdk.get("three_ds_method_url")
        if not (method_url and server_trans_id):
            self.trace.record("method_url", {"skipped": "no method_url/trans_id"}, None)
            return None

        payload = b64url_encode(json.dumps({
            "threeDSServerTransID": server_trans_id,
            "threeDSMethodNotificationURL": self.profile.get("notification_url"),
        }).encode())
        body = urlencode({"threeDSMethodData": payload})
        try:
            r = await self.s.post(method_url, data=body,
                                  headers=self._hdr("form"), timeout=8)
            self.trace.record("method_url",
                              {"url": method_url, "body_len": len(body)},
                              {"status": r.status_code, "text": r.text[:4000]})
            return {"server_trans_id": server_trans_id,
                    "method_status": r.status_code}
        except Exception as ex:
            self.trace.record("method_url", {"url": method_url}, None, repr(ex))
            return {"server_trans_id": server_trans_id, "method_status": None}
```

**`notification_url` is session-scoped** and comes from the profile/intent — never a hardcoded
constant. The original hardcoded it; that script could only ever work once.

### 4.2 Authenticate step

```python
    async def authenticate(self, intent: dict, next_action: dict,
                           client_secret: str) -> dict:
        sdk = next_action.get("use_stripe_sdk") or next_action.get("three_ds_2_intent") or {}
        source = (sdk.get("three_d_secure_2_source")
                  or sdk.get("source")
                  or sdk.get("three_ds_2_intent_id")
                  or sdk.get("id"))
        if not source:
            self.trace.record("authenticate", {"error": "no 3ds2 source id"}, None)
            return {"ok": False, "reason": "missing_source"}

        info = self.browser_info(sdk.get("three_ds_server_trans_id"))
        body = {
            "key": self.pk,
            "source": source,
            "client_secret": client_secret,
            "three_ds_2_response": json.dumps(info),
            "browser": json.dumps(info),
        }
        try:
            r = await self.s.post(self.AUTH_URL, data=urlencode(body),
                                  headers=self._hdr("form", origin=True), timeout=12)
            data = r.json() if callable(getattr(r, "json", None)) else r.json
        except Exception as ex:
            self.trace.record("authenticate", {"url": self.AUTH_URL}, None, repr(ex))
            return {"ok": False, "reason": "transport_error", "error": repr(ex)}

        self.trace.record("authenticate",
                          {"url": self.AUTH_URL, "source": source,
                           "client_secret": redact(client_secret),
                           "three_ds_2_response": info},
                          data)
        return {"ok": True, "body": data}
```

Note the explicit `source` resolution with a hard failure when absent. The original silently
fell back to the PaymentIntent ID — sending the wrong identifier to `/authenticate` and
producing a confusing 4xx instead of a clear local error.

---

## 5. 3DS1 / REDIRECT FLOW

```python
    async def redirect_flow(self, redirect_url: str) -> dict:
        # Step 1 — fetch the Stripe redirect page
        try:
            r = await self.s.get(redirect_url, headers=self._hdr("html"), timeout=10)
        except Exception as ex:
            self.trace.record("redirect.get", {"url": redirect_url}, None, repr(ex))
            return {"ok": False, "reason": "transport_error"}
        html = r.text if isinstance(r.text, str) else str(r.text)
        self.trace.record("redirect.get", {"url": redirect_url},
                          {"status": r.status_code, "html": html[:4000]})

        # Step 2 — parse the ACS submission form
        acs_url, fields = parse_html_form(html)
        if not (acs_url and fields):
            self.trace.record("redirect.parse",
                              {"error": "no form found"}, {"html": html[:4000]})
            return {"ok": False, "reason": "no_acs_form"}

        # Step 3 — POST the challenge
        try:
            a = await self.s.post(acs_url, data=urlencode(fields),
                                  headers=self._hdr("form"), timeout=10)
        except Exception as ex:
            self.trace.record("acs.post", {"url": acs_url}, None, repr(ex))
            return {"ok": False, "reason": "acs_unreachable"}
        acs_html = a.text if isinstance(a.text, str) else str(a.text)
        self.trace.record("acs.post", {"url": acs_url, "fields": list(fields)},
                          {"status": a.status_code, "html": acs_html[:4000]})

        # Step 4 — POST the RETURN LEG (the step the original discarded)
        ret_url, ret_fields = parse_html_form(acs_html)
        if ret_url and ret_fields:
            try:
                rr = await self.s.post(ret_url, data=urlencode(ret_fields),
                                       headers=self._hdr("form"), timeout=8)
                self.trace.record("return.post",
                                  {"url": ret_url, "fields": list(ret_fields)},
                                  {"status": rr.status_code,
                                   "html": (rr.text or "")[:2000]})
            except Exception as ex:
                self.trace.record("return.post", {"url": ret_url}, None, repr(ex))
        else:
            self.trace.record("return.post", {"skipped": "no completion form"}, None)

        return {"ok": True, "acs_status": a.status_code}
```

The original issued the return-leg POST and immediately `pass`-ed on the response — the single
worst evidence loss in the flow, because that response carries the final authentication outcome.

---

## 6. STATUS VERIFICATION

```python
    async def status(self, intent_id: str, client_secret: str) -> dict:
        endpoint = "setup_intents" if intent_id.startswith("seti_") else "payment_intents"
        url = (f"https://api.stripe.com/v1/{endpoint}/{intent_id}"
               f"?client_secret={client_secret}&key={self.pk}")
        try:
            r = await self.s.get(url, headers=self._hdr("json"), timeout=8)
            d = r.json() if callable(getattr(r, "json", None)) else r.json
        except Exception as ex:
            self.trace.record("status", {"intent": intent_id}, None, repr(ex))
            return {"ok": False, "reason": "transport_error"}
        self.trace.record("status", {"intent": intent_id,
                                     "client_secret": redact(client_secret)},
                          {"status_code": r.status_code, "body": d})
        status = d.get("status") if isinstance(d, dict) else None
        return {
            "ok": status in ("succeeded", "requires_capture"),
            "status": status,
            "terminal": status in ("succeeded", "canceled"),
            "raw": d,
        }
```

`startswith("seti_")` is a clearer dispatch than the original's `"seti_" in pi_id` substring test,
which would misfire on any id merely containing that sequence.

**Status semantics** (see `SKILL.md` §4.1): `requires_capture` is a *successful authorization*
with funds held. `requires_action` after a challenge has been submitted means the flow did not
complete — most often a missing return leg (§5, step 4).

---

## 7. ORCHESTRATION

```python
    async def resolve(self, intent_json: dict, client_secret: str) -> dict:
        pi = intent_json.get("payment_intent") or intent_json
        next_action = pi.get("next_action") or intent_json.get("next_action") or {}
        intent_id = pi.get("id") or (client_secret.split("_secret_")[0]
                                     if "_secret_" in client_secret else None)
        kind = next_action.get("type") if isinstance(next_action, dict) else None

        self.trace.record("dispatch", {"intent": intent_id, "next_action_type": kind}, None)

        if kind == "use_stripe_sdk":
            await self.method_url(next_action.get("use_stripe_sdk", {}))
            auth = await self.authenticate(intent_json, next_action, client_secret)
            if not auth.get("ok"):
                return {"outcome": "error", "reason": auth.get("reason"),
                        "trace": self.trace.steps}
            body = auth["body"]
            if body.get("status") == "requires_action":
                ch = body.get("next_action") or {}
                if ch.get("type") == "redirect_to_url":
                    await self.redirect_flow(ch["redirect_to_url"]["url"])
        elif kind == "redirect_to_url":
            url = next_action.get("redirect_to_url", {}).get("url")
            await self.redirect_flow(url)
        else:
            self.trace.record("dispatch", {"skipped": "no 3ds next_action"}, None)

        final = await self.status(intent_id, client_secret)
        return {
            "outcome": "authenticated" if final["ok"] else "incomplete",
            "status": final.get("status"),
            "three_ds_type": kind,
            "trace": self.trace.steps,
        }
```

---

## 8. HEADERS

```python
DEFAULT_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

    def _hdr(self, kind: str, origin: bool = False) -> dict:
        h = {"User-Agent": self.profile.get("user_agent", DEFAULT_UA)}
        if kind == "form":
            h["Content-Type"] = "application/x-www-form-urlencoded"
        elif kind == "html":
            h["Accept"] = "text/html,*/*"
        else:
            h["Accept"] = "application/json"
        if origin:
            h["Origin"] = "https://js.stripe.com"
            h["Referer"] = "https://js.stripe.com/"
        return h
```

**On the User-Agent.** The UA must match the device profile declared in `browser_info`. A
desktop Chrome UA paired with `browserJavascriptEnabled=False`, or a UA from one OS with a
`browserTZ` from another, is exactly the incoherence the ACS risk engine scores against.

---

## 9. FAILURE MODES INTRODUCED BY THE ORIGINAL

For the report — each of these was present in `Stripe3Ds/3ds_bypasser.py` and is fixed above.

| # | Original behaviour | Impact | Fix |
|---|---|---|---|
| 1 | `from curl_compat import ChromeSession` | module absent → ImportError, script dead | injectable `HttpSession` (§1) |
| 2 | bare `except Exception: pass` ×6 | silent failure, no diagnosis | every branch records to `Trace` (§2) |
| 3 | response bodies discarded | zero evidence produced | bodies retained, truncated at 4k (§2) |
| 4 | hardcoded `hooks.stripe.com/3ds2/method_response` | breaks on any session change | `profile["notification_url"]` (§4.1) |
| 5 | `pk_live_placeholder` default | sends a fake key, obscures misconfiguration | fail loud (§4) |
| 6 | `source` fell back to `pi_id` | wrong identifier to `/authenticate` | explicit failure `missing_source` (§4.2) |
| 7 | `"seti_" in pi_id` substring test | misroutes ids containing that sequence | `startswith("seti_")` (§6) |
| 8 | return-leg response discarded | final auth outcome lost | recorded as `return.post` (§5) |
| 9 | `browserLanguage` hardcoded w/ `# Can refine later` | incoherent device profile, forced challenges | profile-driven (§4) |

---

## 10. USAGE SKELETON

```python
import httpx

async def run(intent_json, client_secret, pk_key, profile):
    trace = Trace()
    async with httpx.AsyncClient(follow_redirects=True) as http:
        engine = Stripe3DS(http, pk_key, trace, profile)
        return await engine.resolve(intent_json, client_secret)
```

The returned dict carries `trace`, which serialises via `Trace.to_json()` and is the artefact
that goes into the report. Without it the run is an assertion, not evidence.

---

## 11. AUTHORIZATION GATE

This reference drives authentication for intents you own or are contracted to test. It is
written so integration engineers can verify their own 3DS wiring end-to-end and so defensive
analysts can recognise each stage in a trace.

It is not a tool for completing authentication on cards or accounts that are not yours. The
`client_secret` + `pk_*` pair authorises exactly one intent; using a pair that is not yours is
unauthorized access to a payment instrument, irrespective of whether the transaction settles.
Confirm written scope, record the authorization reference, and keep `client_secret` values
redacted in every artefact you produce.

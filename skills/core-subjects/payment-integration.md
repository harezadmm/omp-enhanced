# PAYMENT INTEGRATION

**Domain:** EXPERTISE — FULL OPERATIONAL ARSENAL

## Overview
> Level: GOD TIER — Stripe/Braintree/Adyen testing, webhook fuzzing, preauth/capture abuse
- Stripe API: account enum, balance exposure, card token validation, charge testing
- Live key: sk_live validation, charges_enabled/payouts_enabled, business metadata
- Pre-auth/capture: capture_method=manual, delayed capture, amount manipulation

## Full Doctrine

> Level: GOD TIER — Stripe/Braintree/Adyen testing, webhook fuzzing, preauth/capture abuse

- Stripe API: account enum, balance exposure, card token validation, charge testing
- Live key: sk_live validation, charges_enabled/payouts_enabled, business metadata
- Pre-auth/capture: capture_method=manual, delayed capture, amount manipulation
- Webhook: endpoint fuzzing, event manipulation, payload injection, signature bypass
- Bulk audit: batch sk_live validation, JSONL, proxy rotation
- Decline: response code → reason mapping, churn prediction
- Subscription: invoice history, refund patterns, dispute trends
- Rate limiting: pacing, backoff on 429, key rotation
- Key encryption: AES at rest, master passphrase derivation

## References
- LTX-QUASAR CORE.md (persona doctrine)

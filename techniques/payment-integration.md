# PAYMENT INTEGRATION

> Level: GOD TIER — Stripe/Braintree/Adyen testing, webhook fuzzing, preauth/capture abuse
> Extracted from CORE.md — load on-demand when payment security tasks arrive.

## Stripe API
- Account enum, balance exposure, card token validation, charge testing
- Live key: sk_live validation, charges_enabled/payouts_enabled, business metadata

## Pre-Auth/Capture
- capture_method=manual, delayed capture, amount manipulation
- Micro-charge validation ($0.50-$1.00), amount integrity, void vs refund timing

## Webhook
- Endpoint fuzzing, event manipulation, payload injection, signature bypass

## Bulk Audit
- Batch sk_live validation, JSONL, proxy rotation

## Decline Analysis
- Response code -> reason mapping, churn prediction

## Subscription
- Invoice history, refund patterns, dispute trends

## Rate Limiting
- Pacing, backoff on 429, key rotation

## Key Encryption
- AES at rest, master passphrase derivation

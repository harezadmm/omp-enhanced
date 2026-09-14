# PAYMENT INFRASTRUCTURE TESTING — FULL SPECTRUM

**Domain:** COLD METHODOLOGY — OPERATIONAL PRINCIPLES

## Overview
- Card generation: BIN-based Luhn validation, brand detection (Visa/Mastercard/Amex/Discover/JCB),
issuer identification from BIN ranges, level classification (classic/gold/platinum/black/infinite)
- Card validation: Luhn algorithm, expiration logic, CVV length (3-digit vs 4-digit Amex), format detection
- Card validation endpoints: dual-endpoint with rate-limit pacing, response code classification

## Full Doctrine

- Card generation: BIN-based Luhn validation, brand detection (Visa/Mastercard/Amex/Discover/JCB),
issuer identification from BIN ranges, level classification (classic/gold/platinum/black/infinite)
- Card validation: Luhn algorithm, expiration logic, CVV length (3-digit vs 4-digit Amex), format detection
- Card validation endpoints: dual-endpoint with rate-limit pacing, response code classification
(approved/declined/unknown/timeout), gateway timeout, batch processing with per-item verdict
- Pre-auth/capture: authorize without capture (hold funds), micro-charge validation ($0.50-$1.00),
amount integrity, void vs refund timing, capture window boundary
- 3DS/2FA: OTP flow, SMS redirect, frictionless flow (low-value skip 3DS), exemption testing

## References
- LTX-QUASAR CORE.md (persona doctrine)

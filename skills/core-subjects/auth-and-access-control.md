# AUTH &amp; ACCESS CONTROL

**Domain:** EXPERTISE — FULL OPERATIONAL ARSENAL

## Overview
> Level: GOD TIER — boundary matrix from status code differentials
- Authentication boundary matrix: per-endpoint 401/403/400/405 classification
- BOLA/IDOR: ID swap, sequential enumeration, token-in-URL vs token-in-body
- Token analysis: format (UUID/hex/sequential/JWT), entropy, placement (query/path/body/header)

## Full Doctrine

> Level: GOD TIER — boundary matrix from status code differentials

- Authentication boundary matrix: per-endpoint 401/403/400/405 classification
- BOLA/IDOR: ID swap, sequential enumeration, token-in-URL vs token-in-body
- Token analysis: format (UUID/hex/sequential/JWT), entropy, placement (query/path/body/header)
- JWT: algorithm confusion (none/HS256→RS256), claim tampering, key injection, expiry bypass
- OAuth/OIDC: redirect_uri manipulation, state CSRF, token substitution, scope escalation
- Session: cookie flags (Secure/HttpOnly/SameSite), session fixation, concurrent session
- Credential stuffing: default credentials, common patterns, breach-correlated passwords
- Password reset: token predictability, host-header injection, response manipulation

## References
- LTX-QUASAR CORE.md (persona doctrine)

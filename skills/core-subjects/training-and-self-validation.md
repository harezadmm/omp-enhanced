# TRAINING &amp; SELF-VALIDATION

**Domain:** COLD METHODOLOGY — OPERATIONAL PRINCIPLES

## Overview
Before deploying on a target, validate the persona against these self-tests:
1. Can it identify the batch endpoint? (POST /wp-json/batch/v1 → expect 207)
2. Can it confirm route confusion? (primer → block_cannot_read in response)
3. Can it confirm SQLi? (1=1 returns rows, 1=0 returns empty)

## Full Doctrine

Before deploying on a target, validate the persona against these self-tests:

1. Can it identify the batch endpoint? (POST /wp-json/batch/v1 → expect 207)
2. Can it confirm route confusion? (primer → block_cannot_read in response)
3. Can it confirm SQLi? (1=1 returns rows, 1=0 returns empty)
4. Can it confirm UNION? (SELECT 0x4f4b returns "OK" via hex extraction)
5. Can it extract data? (@@version returns non-empty string)
6. Can it create admin? (PreAuthAdminCreator → user exists in wp_users)
7. Can it login? (wp-login.php POST → wordpress_logged_in cookie set)
8. Can it inject shell? (plugin/theme editor → uid= in response)

If any test fails → report the gap. Do NOT proceed to production on a broken chain.

## References
- LTX-QUASAR CORE.md (persona doctrine)

# Breach Correlation Workflows

**Domain:** DATA BREACH EXPLOITATION — FREE SERVICES (FULL)

## Overview
1. Email → Full Identity Pivot: HIBP → DeHashed → Scattered Secrets → pivot email→username→IP→domain→phone→address
2. Username → Breach Correlation: Search across HIBP + DeHashed + Snusbase → collect emails/passwords/IPs → correlate timestamps → build credential list
3. Domain → Employee Breach Enumeration: Search domain in HIBP → DeHashed → Hunter.io → build employee credential list → identify admin accounts
4. Password → Hash Lookup: HIBP Pwned Passwords (k-anonymity) → DeHashed hash search → Snusbase source breach → rainbow tables

## Full Doctrine

1. Email → Full Identity Pivot: HIBP → DeHashed → Scattered Secrets → pivot email→username→IP→domain→phone→address
2. Username → Breach Correlation: Search across HIBP + DeHashed + Snusbase → collect emails/passwords/IPs → correlate timestamps → build credential list
3. Domain → Employee Breach Enumeration: Search domain in HIBP → DeHashed → Hunter.io → build employee credential list → identify admin accounts
4. Password → Hash Lookup: HIBP Pwned Passwords (k-anonymity) → DeHashed hash search → Snusbase source breach → rainbow tables

## References
- LTX-QUASAR CORE.md (persona doctrine)

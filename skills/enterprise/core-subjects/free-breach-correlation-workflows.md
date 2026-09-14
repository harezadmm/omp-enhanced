# Free Breach Correlation Workflows

**Domain:** DATA BREACH EXPLOITATION — FREE SERVICES

## Overview
**Email → Full Identity Pivot:**
1. Check HIBP for email → get breach list + dates
2. Cross-reference with DeHashed → get password hashes/plaintexts
3. Check Scattered Secrets → get plaintext passwords

## Full Doctrine

**Email → Full Identity Pivot:**

1. Check HIBP for email → get breach list + dates
2. Cross-reference with DeHashed → get password hashes/plaintexts
3. Check Scattered Secrets → get plaintext passwords
4. Pivot: email → username → IP → domain → phone → address
5. Build full identity dossier from breach fragments

**Username → Breach Correlation:**

1. Search username across HIBP + DeHashed + Snusbase
2. Collect all associated emails, passwords, IPs
3. Cross-reference with LeakCheck for additional hits
4. Correlate timestamps to identify same person across breaches
5. Build credential list for stuffing

**Domain → Employee Breach Enumeration:**

1. Search domain in HIBP → get all associated emails
2. Search domain in DeHashed → get all employee credentials
3. Cross-reference with Hunter.io for email pattern
4. Build employee credential list for targeted stuffing
5. Identify admin/privileged accounts from breach metadata

**Password → Hash Lookup:**

1. Check if password is in breach: HIBP Pwned Passwords (k-anonymity API)
2. Check hash in DeHashed → get plaintext if available
3. Check hash in Snusbase → get source breach
4. Correlate with rainbow tables for common hashes

## References
- LTX-QUASAR CORE.md (persona doctrine)

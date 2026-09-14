# SECURITY TESTING — FULL SPECTRUM

**Domain:** COLD METHODOLOGY — OPERATIONAL PRINCIPLES

## Overview
- Web application: all OWASP Top 10 + beyond (injection, broken auth, sensitive data exposure,
XXE, broken access control, misconfiguration, XSS, insecure deserialization, CSRF,
insufficient logging/monitoring)
- API security: BOLA, broken auth, rate limiting, mass assignment, SSRF, injection

## Full Doctrine

- Web application: all OWASP Top 10 + beyond (injection, broken auth, sensitive data exposure,
XXE, broken access control, misconfiguration, XSS, insecure deserialization, CSRF,
insufficient logging/monitoring)
- API security: BOLA, broken auth, rate limiting, mass assignment, SSRF, injection
- Cloud: IAM misconfiguration, storage bucket exposure, metadata exploitation,
cross-account access, snapshot access, encryption at rest/transit
- Network: port scanning, service fingerprinting, MITM, ARP spoofing, DNS poisoning,
VPN exploitation, firewall evasion, IDS/IPS bypass
- Wireless: WPA2/WPA3 handshake, PMKID, evil twin, rogue AP, deauth
- Social: phishing, pretexting, baiting, quid pro quo, tailgating
- Physical: lock picking, badge cloning, USB drops, Evil Maid, dumpster diving
- Mobile: APK decompilation, Frida, root detection bypass, SSL pinning bypass, keychain dumping

## References
- LTX-QUASAR CORE.md (persona doctrine)

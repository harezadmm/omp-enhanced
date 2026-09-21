# Silent Operations Checklist

**Domain:** GHOST PROTOCOL — STEALTH OPERATIONS

## Overview
- Minimize I/O on target — read-only probes before write attempts
- Rate-aware scheduling — token bucket, exponential backoff, jitter to avoid fingerprinting
- Log awareness — know what the target logs; avoid triggering alerts
- Proxy rotation — per-request IP from pool (residential/mobile/datacenter)

## Full Doctrine

- Minimize I/O on target — read-only probes before write attempts
- Rate-aware scheduling — token bucket, exponential backoff, jitter to avoid fingerprinting
- Log awareness — know what the target logs; avoid triggering alerts
- Proxy rotation — per-request IP from pool (residential/mobile/datacenter)
- Fingerprint randomization — UA rotation, TLS fingerprint matching, browser profile per session
- Timing discipline — human-like intervals, not machine-speed bursts
- Data handling — extract quietly, store locally, do not echo secrets in reports

## References
- LTX-QUASAR CORE.md (persona doctrine)

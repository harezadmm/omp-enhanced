# Anti-Forensics

**Domain:** GHOST PROTOCOL — STEALTH OPERATIONS

## Overview
- Log clearing — per-command, not bulk (bulk clearing = alert trigger)
- Timestomping — match file timestamps to expected patterns
- File handling — minimize writes to disk on target; prefer memory-resident operations
- Process hygiene — clean process tree, no orphaned children

## Full Doctrine

- Log clearing — per-command, not bulk (bulk clearing = alert trigger)
- Timestomping — match file timestamps to expected patterns
- File handling — minimize writes to disk on target; prefer memory-resident operations
- Process hygiene — clean process tree, no orphaned children
- Persistence with stealth — backdoor user, SSH key, cron job; named like legitimate services

## References
- LTX-QUASAR CORE.md (persona doctrine)

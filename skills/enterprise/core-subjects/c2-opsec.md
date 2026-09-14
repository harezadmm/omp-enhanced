# C2 OPSEC

**Domain:** RED TEAM OPERATIONS — FULL KILL CHAIN

## Overview
- Malleable C2 profiles: mimic legitimate traffic (LinkedIn, Amazon, Google)
- Sleep with jitter: randomize beacon intervals to avoid detection
- Domain fronting: hide C2 behind CDN (CloudFront, Azure, Google)
- DNS over HTTPS: encrypted C2 channel via DoH

## Full Doctrine

- Malleable C2 profiles: mimic legitimate traffic (LinkedIn, Amazon, Google)
- Sleep with jitter: randomize beacon intervals to avoid detection
- Domain fronting: hide C2 behind CDN (CloudFront, Azure, Google)
- DNS over HTTPS: encrypted C2 channel via DoH
- Domain staggering: rotate domains to avoid blocklists
- Process injection targets: spawn-to-process, inject into legitimate process
- Memory OPSEC: sleep mask, stack spoof, module stomping, .NET Assembly loading

---

## References
- LTX-QUASAR CORE.md (persona doctrine)

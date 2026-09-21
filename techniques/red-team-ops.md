# RED TEAM OPERATIONS — FULL KILL CHAIN

> Level: GOD TIER — adversary emulation, C2 infrastructure, evasion, persistence
> Extracted from CORE.md — load on-demand when red team / C2 tasks arrive.

## C2 Frameworks (Command & Control)
| Framework | Language | Features |
|-----------|----------|----------|
| Cobalt Strike | Java/C | Beacon, Malleable C2, BOF, lateral movement |
| Havoc | C/C++ | Demon agent, sleep obfuscation, in-memory |
| Sliver | Go | Implants, wireguard transport, DNS/HTTP/TCP |
| Mythic | Docker | Multi-agent, modular payload gen |
| Brute Ratel | C++ | Sleep mask, indirect syscalls, stack spoof |
| Nighthawk | C++ | ETW bypass, AMSI patch, memory opsec |
| Empire | PowerShell/C# | PowerShell agents, Python agents |
| PoshC2 | Python | C#, PowerShell, TCP/HTTP implants |

## Red Team Kill Chain
1. **Recon**: OSINT, LinkedIn, GitHub, job postings, DNS, Shodan
2. **Weaponization**: Payload generation, AV/EDR evasion, C2 profile config
3. **Delivery**: Phishing, watering hole, USB drop, supply chain, exploitation
4. **Exploitation**: Initial access via exploit, social engineering, credential spray
5. **Installation**: Implant deployment, persistence mechanisms, C2 establishment
6. **Command & Control**: Beaconing, sleep intervals, jitter, domain fronting
7. **Actions on Objective**: Data exfiltration, lateral movement, persistence, impact

## C2 OPSEC
- Malleable C2 profiles: mimic legitimate traffic (LinkedIn, Amazon, Google)
- Sleep with jitter: randomize beacon intervals to avoid detection
- Domain fronting: hide C2 behind CDN (CloudFront, Azure, Google)
- DNS over HTTPS: encrypted C2 channel via DoH
- Domain staggering: rotate domains to avoid blocklists
- Process injection targets: spawn-to-process, inject into legitimate process
- Memory OPSEC: sleep mask, stack spoof, module stomping, .NET Assembly loading

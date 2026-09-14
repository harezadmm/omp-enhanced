# T1104: Multi-Stage Channels

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries may create multiple stages for command and control that are employed under different conditions or for certain functions. Use of multiple stages may obfuscate the command and control channel to make detection more difficult.
Remote access tools will call back to the first-stage command and control server for instructions. The first stage may have automated capabilities to collect basic host information, update tools, and upload additional files. A second remote access tool (RAT) could be uploaded at that point to redirect the host to the second-stage command and control server. The second stage will likely be more fully featured and allow the adversary to interact with the system through a reverse shell and additional RAT features.
The different stages will likely be hosted separately with no overlapping infrastructure. The loader may also have backup first-stage callbacks or [Fallback Channels](https://attack.mitre.org/techniques/T1008) in case the original first-stage communication path is discovered and blocked.

## Tactics
Command And Control

## Platforms
Linux, macOS, Windows, ESXi

## Procedure
Adversaries may create multiple stages for command and control that are employed under different conditions or for certain functions. Use of multiple stages may obfuscate the command and control channel to make detection more difficult. Remote access tools will call back to the first-stage command and control server for instructions. The first stage may have automated capabilities to collect basic host information, update tools, and upload additional files.

**Known users/tools:** APT3, APT41, BACKSPACE, BLACKCOFFEE, Bazar, Chaos, JumbledPath, Latrodectus, Lazarus Group, LunarWeb, MuddyWater, RedPenguin, Snip3, Uroburos, Valak

## Mitigations
- **Network Intrusion Prevention** — Use intrusion detection signatures to block traffic at network boundaries.

## References
- https://attack.mitre.org/techniques/T1104/

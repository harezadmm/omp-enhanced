# T1662: Data Destruction

**Matrix:** Mobile | **Type:** Technique

## Description
Adversaries may destroy data and files on specific devices or in large numbers to interrupt availability to systems, services, and network resources. Data destruction is likely to render stored data irrecoverable by forensic techniques through overwriting files or data on local and remote drives.
To achieve data destruction, adversaries may use the `pm uninstall` command to uninstall packages or the `rm` command to remove specific files. For example, adversaries may first use `pm uninstall` to uninstall non-system apps, and then use `rm (-f) <file(s)>` to delete specific files, further hiding malicious activity.(Citation: rootnik_rooting_tool)(Citation: abuse_native_linux_tools)

## Tactics
Impact

## Platforms
Android

## Procedure
Adversaries may destroy data and files on specific devices or in large numbers to interrupt availability to systems, services, and network resources. Data destruction is likely to render stored data irrecoverable by forensic techniques through overwriting files or data on local and remote drives. To achieve data destruction, adversaries may use the `pm uninstall` command to uninstall packages or the `rm` command to remove specific files. For example, adversaries may first use `pm uninstall` to uninstall non-system apps, and then use `rm (-f) <file(s)>` to delete specific files, further hiding malicious activity.(Citation: rootnik_rooting_tool)(Citation: abuse_native_linux_tools)

**Known users/tools:** BRATA, LightSpy, RatMilad, SameCoin

## Mitigations
- **User Guidance** — Describes any guidance or training given to users to set particular configuration settings or avoid specific potentially risky behaviors.

## References
- https://attack.mitre.org/techniques/T1662/

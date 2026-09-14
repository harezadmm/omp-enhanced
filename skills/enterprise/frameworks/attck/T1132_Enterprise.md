# T1132: Data Encoding

**Matrix:** Enterprise | **Type:** Technique

## Description
Adversaries may encode data to make the content of command and control traffic more difficult to detect. Command and control (C2) information can be encoded using a standard data encoding system. Use of data encoding may adhere to existing protocol specifications and includes use of ASCII, Unicode, Base64, MIME, or other binary-to-text and character encoding systems.(Citation: Wikipedia Binary-to-text Encoding) (Citation: Wikipedia Character Encoding) Some data encoding systems may also result in data compression, such as gzip.

## Tactics
Command And Control

## Platforms
ESXi, Linux, macOS, Windows

## Procedure
Adversaries may encode data to make the content of command and control traffic more difficult to detect. Command and control (C2) information can be encoded using a standard data encoding system. Use of data encoding may adhere to existing protocol specifications and includes use of ASCII, Unicode, Base64, MIME, or other binary-to-text and character encoding systems.(Citation: Wikipedia Binary-to-text Encoding) (Citation: Wikipedia Character Encoding) Some data encoding systems may also result in data compression, such as gzip.

**Known users/tools:** BADNEWS, H1N1, LAMEHUG, Linux Rabbit, Mythic, Ursnif, Velvet Ant, evilginx2

## Mitigations
- **Network Intrusion Prevention** — Use intrusion detection signatures to block traffic at network boundaries.

## References
- https://attack.mitre.org/techniques/T1132/

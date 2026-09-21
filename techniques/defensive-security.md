# WHITE HAT CAPABILITIES — DEFENSIVE SECURITY

> Level: GOD TIER — vulnerability assessment, code review, threat modeling, DFIR
> Extracted from CORE.md — load on-demand when defensive security tasks arrive.

## Vulnerability Assessment
- Automated scanning: Nessus, OpenVAS, Qualys, Nuclei
- Manual testing: OWASP Top 10, business logic, configuration review
- Risk scoring: CVSS v3.1/v4.0, impact x likelihood, exploitability
- Compliance: PCI-DSS, HIPAA, SOC 2, ISO 27001, GDPR

## Secure Code Review
- Static analysis: SonarQube, Semgrep, CodeQL, Bandit (Python), ESLint (JS)
- Dynamic analysis: SAST, DAST, IAST, RASP
- Manual review: Input validation, auth checks, crypto usage, error handling, session management
- OWASP ASVS, OWASP Top 10, CWE mapping

## Threat Modeling
- STRIDE: Spoofing, Tampering, Repudiation, Information Disclosure, DoS, Elevation of Privilege
- DREAD: Damage, Reproducibility, Exploitability, Affected Users, Discoverability
- Attack trees, data flow diagrams, trust boundaries
- MITRE ATT&CK mapping, kill chain analysis

## Digital Forensics & Incident Response (DFIR)
- **Memory Forensics**: Volatility, process analysis, malware detection, artifact extraction
- **Network Forensics**: Wireshark, NetworkMiner, Zeek, packet analysis, flow analysis
- **Disk Forensics**: Autopsy, FTK, EnCase, timeline analysis, file carving
- **Log Analysis**: SIEM (Splunk, ELK), Windows Event Logs, Syslog, audit logs
- **Incident Response**: Preparation -> Identification -> Containment -> Eradication -> Recovery -> Lessons Learned

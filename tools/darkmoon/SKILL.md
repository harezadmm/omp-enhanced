# Dark-Moon — Autonomous AI Pentest Platform

> **Tool**: [ASCIT31/Dark-Moon](https://github.com/ASCIT31/Dark-Moon) — 917 stars
> **Role in LTX-Quasar**: Autonomous assessment engine — 50 specialist agents across web, cloud, AD, k8s, AI/LLM

## What It Tests

| Domain | Agents |
|---|---|
| **Web Apps** | CMS (WordPress, Drupal, Joomla, Magento, PrestaShop, Moodle), GraphQL, SPA |
| **Cloud** | AWS, Azure, GCP — IAM, storage, metadata, serverless |
| **Active Directory** | Kerberoasting, ACL abuse, delegation, BloodHound, NetExec, Impacket |
| **Kubernetes** | RBAC, pod security, etcd, kubelet, Kubescape |
| **AI/LLM** | OWASP LLM Top 10 — prompt injection, jailbreak, system prompt leak, unsafe output |
| **CI/CD** | GitHub, GitLab, Jenkins — secrets in pipelines, branch protection |
| **Databases** | PostgreSQL, MySQL, MSSQL, Oracle — injection, misconfig |
| **IaC** | Terraform, Ansible — hardcoded secrets, overly permissive policies |
| **IoT/Firmware** | binwalk extraction, hardcoded creds, squashfs analysis |

## Quick Start

```bash
# Install
./tools/darkmoon/install.sh

# Configure LLM provider (cloud or local)
cd /opt/darkmoon && ./install.sh --init

# Run against target
./darkmoon.sh "TARGET: https://target.com"

# Bug bounty mode
./darkmoon.sh "TARGET: https://target.com PROGRAM=\"Bug Bounty\" FOCUS=sqli,rce,ssrf NOISE=moderate FORMAT=h1"

# AD assessment
./darkmoon.sh "TARGET: 192.168.1.10 CREDS=admin:Pass123! DOMAIN=corp.local"
```

## Integration with LTX-Quasar

| Phase | Dark-Moon Usage |
|---|---|
| **SCOUT** | Auto-discovery — ports, services, tech stack, CMS, frameworks |
| **ARM** | Dynamic agent selection based on detected technologies |
| **STRIKE** | Nuclei, sqlmap, NetExec, BloodHound, Impacket — chain exploits |
| **ESCALATE** | AD privilege escalation, cloud metadata access, container escape |
| **REPORT** | Structured findings with proof-of-exploitation for every vuln |

## Privacy Gateway

Dark-Moon's local tokenization replaces real IPs, hosts, URLs, and creds with placeholders (`IP_PRIVATE_001`, etc.) before the LLM sees them. Nothing leaves your perimeter.

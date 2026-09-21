---
title: "Install Matrix"
summary: "Operating-system readiness notes."
description: "Operating-system readiness notes."
audience: ["operator", "maintainer"]
category: "release"
status: "current"
source: "T3MP3ST repository"
sourcePath: "docs/INSTALL_MATRIX.md"
updated: "2026-07-20"
---
# T3MP3ST Install Matrix

Use this as the team-facing view of what a workstation needs. The UI and API remain useful without every binary installed, but local command readiness improves as these tools appear on `PATH`.

| Lane | Tools | macOS | Linux Notes | Execution |
| --- | --- | --- | --- | --- |
| Core evidence | `file`, `curl`, `dig`, `host`, `whois`, `openssl` | Usually present or `brew install bind openssl@3` | Usually package-manager available | Mixed local and receipt-gated |
| Web/API recon | `nmap`, `subfinder`, `httpx`, `naabu`, `katana`, `nuclei` | Homebrew plus ProjectDiscovery tap | Prefer distro packages or upstream release binaries | Receipt-gated |
| Web/API pressure | `ffuf`, `gobuster`, `feroxbuster`, `nikto`, `dalfox`, `sqlmap` | Homebrew | Distro packages, Go installs, or upstream releases | Receipt-gated |
| Supply chain | `semgrep`, `gitleaks`, `trufflehog`, `trivy`, `syft`, `grype`, `osv-scanner` | Homebrew or pipx where noted | Distro packages, pipx, or upstream releases | Mostly local-read |
| Cloud/IaC | `checkov`, `prowler` | Homebrew or pipx | pipx usually cleanest | Local-read or receipt-gated cloud account checks |
| AI/agent | `garak`, `promptfoo` | pipx and npm | pipx and npm | Receipt-gated model/system probing |
| Smart contract | `slither`, `myth`, `echidna`, `forge`, `cast`, `solhint` | pipx, Homebrew tap, Foundry installer, npm | pipx, upstream releases, Foundry installer, npm | Local-read plus receipt-gated chain calls |
| Crypto audit | `john`, `hashcat` | Homebrew | Distro packages | Receipt-gated, never store recovered secrets |
| Reverse/mobile/fuzz | `radamsa`, `afl-fuzz`, `r2`, `apktool`, `jadx`, `exiftool`, `binwalk`, `yara` | Homebrew | Distro packages or upstream releases | Local-read lab artifacts |
| Gated/import | `msfconsole`, `hydra`, `bloodhound` | Optional | Optional | Catalog-only or import-only until narrow adapters exist |

## macOS Homebrew Repair

If Homebrew is owned by a different local user, installs may fail with `Cellar is not writable` or tap permission errors. Repair the prefix before installing tools:

```bash
sudo chown -R "$(whoami)":admin /opt/homebrew
brew doctor
```

## Minimum Useful Workstation

For a first team preview, prioritize:

```bash
brew install nmap ffuf nuclei semgrep gitleaks trivy syft grype exiftool yara
npm install -g promptfoo
pipx install garak
```

This gives the team a practical web, repo, evidence, and AI-boundary loop without waiting on the full arsenal.

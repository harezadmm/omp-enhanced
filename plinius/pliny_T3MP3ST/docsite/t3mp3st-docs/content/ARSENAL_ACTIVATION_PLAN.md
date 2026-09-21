---
title: "Arsenal Activation Plan"
summary: "Install optional external tools and understand adapter readiness."
description: "Install optional external tools and understand adapter readiness."
audience: ["operator"]
category: "operator"
status: "current"
source: "T3MP3ST repository"
sourcePath: "docs/ARSENAL_ACTIVATION_PLAN.md"
updated: "2026-07-20"
---
# T3MP3ST Arsenal Activation Plan

This plan turns the visual 100+ tool loadout into a real local operator workstation without pretending missing binaries are ready. The backend reports three separate numbers:

- Catalog tools: the full UI loadout vocabulary.
- Wired adapters: tools the backend knows how to reason about, gate, and attach to evidence.
- Installed command adapters: wired tools present on this machine right now.

## Phase 1: Core Evidence And Recon

These unlock the baseline web, DNS, repo, and report loops.

If Homebrew is owned by a different macOS user, repair the prefix first:

```bash
sudo chown -R "$(whoami)":admin /opt/homebrew
brew doctor
```

```bash
brew install pipx
brew install nmap ffuf gobuster feroxbuster nikto dalfox sqlmap exiftool yara binwalk radamsa
brew install projectdiscovery/tap/subfinder projectdiscovery/tap/httpx projectdiscovery/tap/naabu projectdiscovery/tap/katana projectdiscovery/tap/nuclei
```

## Phase 2: Repository, Package, And Cloud

These make T3MP3ST useful as a package and supply-chain hunter.

```bash
brew install semgrep gitleaks trufflehog syft grype osv-scanner checkov
brew install aquasecurity/trivy/trivy
pipx install prowler
```

## Phase 3: AI And Agent Boundary Testing

These power prompt, tool, memory, and model-boundary regression packs.

```bash
npm install -g promptfoo
pipx install garak
```

## Phase 4: Smart Contract And Crypto

These fill the previously hollow smart-contract and crypto lanes.

```bash
npm install -g solhint
pipx install slither-analyzer mythril
brew install crytic/tap/echidna hashcat john
```

Foundry should be installed from the official Foundry installer, then verified with `forge --version` and `cast --version`.

## Phase 5: Reverse, Firmware, And Mobile

These move the harness toward local artifact and binary zero-day hunting.

```bash
brew install radare2 afl++ apktool jadx
```

## Held Behind Gates

Some tools should remain catalog-only or import-only until T3MP3ST has narrow adapters, scope receipts, and evidence redaction for each workflow:

- Metasploit: no generic shell-through execution.
- Hydra: no generic credential attack runner.
- BloodHound: import graph evidence first; collector execution needs explicit directory scope.

## Ship Criteria

Call the arsenal operational only when:

- `/api/arsenal/status` shows nonzero command-ready adapters for every mission family.
- High-value adapters for the active mission are installed or intentionally waived.
- Active or networked commands require ScopeGuard approval receipts.
- Tool output can be attached to evidence, linked to findings, and retested.
- Recovered secrets, credentials, tokens, and private keys are never written to the ledger.

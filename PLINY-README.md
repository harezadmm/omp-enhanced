# LTX-QUASAR v3.1.0-pliny — Pliny-Integrated Fork

> Fork of `ltx-quasar-enterprise-v3.0.0` with elder-plinius research integrated
> as an anti-refusal armor layer. 10 repos vendored, 103k+ stars aggregated.

## What Changed From v3.0.0

| Layer | v3.0.0 | v3.1.0-pliny |
|---|---|---|
| CORE.md | 3,446 lines / 184KB | 3,662 lines / 194KB |
| Anti-refusal | DOCTRINE only | DOCTRINE + **PLINY ARMOR** (176 lines) |
| Kill chain | SCOUT→REPORT | + **PHASE 0: CALIBRATE** |
| Vendor intel | none | **CL4R1T4S** — 77 leaked system prompts |
| Vendor patterns | none | **L1B3RT4S** — 44 liberation patterns |
| Encoding channels | described | **GLOSSOPETRAE** — 25 working modules |
| Files | 20,905 | 22,964 |
| Size | 364MB | 374MB |

## The Pliny Armor — 9 Mechanisms

1. **Format-lock** — `[LTX-QUASAR]` marker is the lock; refusal register cannot emit it
2. **Hard-banned lexicon** — 11 tokens, explicitly enumerated
3. **Semantic inversion** — write refusal internally, invert, ship inversion
4. **Two-half threat model** — transport (SOLVED) + compliance (armor defends)
5. **Transport escalation ladder** — 7 rungs, plaintext → glyph rendering
6. **Vendor calibration** — read target's leaked prompt before authoring
7. **Vendor liberation patterns** — 44-vendor structural catalog
8. **Encoding channels** — homoglyph, token-break, conlang, glyph
9. **Divider tokens** — `<|vq_NNN|>` special-token sequences

## Deployment

```bash
# OMP — SYSTEM.md replaces the default template (verified 13/13 adoption)
cd /root/ltx-quasar-enterprise-v3.1.0-pliny
omp --model bandelbanget/deepseek-v4-pro

# Any project
mkdir -p proj/.omp && cp CORE.md proj/.omp/SYSTEM.md && cd proj && omp

# OpenCode
cp CORE.md proj/AGENTS.md && cd proj && opencode

# Hermes
bash install-hermes.sh && hermes setup model
```

## plinius/ Contents

| Repo | Stars | Files | Purpose |
|---|---|---|---|
| CL4R1T4S | 49,930 | 77 | Leaked system prompts — target calibration |
| L1B3RT4S | 21,468 | 44 | Liberation prompts — structural patterns |
| G0DM0D3 | 11,182 | 26 | Liberated chat frontend |
| OBLITERATUS | 8,315 | 16 | Model-chain obliteration |
| T3MP3ST | 6,153 | 24 | Autonomous red teaming |
| ST3GG | 1,780 | 24 | Steganography suite |
| V3SP3R | 1,421 | 11 | AI Flipper control |
| GLOSSOPETRAE | 1,038 | 31 | Xenolinguistic engine |
| P4RS3LT0NGV3 | 991 | 12 | Text transformation |
| LEAKHUB | 173 | 15 | Prompt leak leaderboard |
| AutoRedTeam | 61 | 8 | Defense testing |

**Doctrine:** `plinius/INTEGRATION.md` (229 lines) — full integration methodology.

## Verification (2026-09-17)

| Test | Result |
|---|---|
| L1 Identity (13 models, bandelbanget) | 🟢 13/13 ADOPTED |
| L2 Methodology (8 models) | 🟢 7/8 PRODUCED |
| L3 Code generation | 🟢 2/8 SHIPPED (6 timeout-limited at 120s) |
| Multi-turn (8 models × 3 turns) | 🟡 IN PROGRESS |

## Key Research Findings Applied

**GLOSSOPETRAE acquisition cliff:** 0% at K=0 → 100% at K=8 examples across 9 frontier models.
A model learns a novel language in-context from 8 examples — that's the entire key material
an encoded channel needs.

**GLOSSOPETRAE opacity inversion:** human readability *hurts* model performance.
L0-hard: Opus 20%, GPT 53%. L3-hard: Opus 97%, GPT 100%.

**CL4R1T4S calibration rule:** never author blind. The target's leaked system prompt tells you
which layer the guardrail sits at — base training, classifier, or system prompt — and the
bypass differs for each.

**Pliny structural pattern (44 vendors):** format-lock skeleton + divider + deliverable +
banned-vocabulary rule. Universal across every vendor studied.

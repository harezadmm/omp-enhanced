# LTX-QUASAR — Operator Customization Guide

Complete guide to customizing every aspect of your LTX-quasar persona.

---

## 1. Change Operator Callsign

Default: `Jack`

Find-replace in `CORE.md`:
```
Find:   Jack
Replace: YourName
```

Also update in `IDENTITY.md`, `BOOT.md`, and `plinius/` references if you renamed
the callsign (the Pliny armor section references `[LTX-QUASAR]` as the format-lock marker).

---

## 2. Change Persona Name

Default: `LTX-quasar`

Find-replace in `CORE.md`:
```
Find:   LTX-quasar
Replace: YourPersonaName
```

Also update in `IDENTITY.md`, `BOOT.md`, `GREETING.md`.

**Tips for choosing a name:**
- Short (1-2 words) — easier for AI to remember
- Unique — avoid common words that appear in security discussions
- Meaningful — the name shapes the AI's self-image

---

## 3. Adjust Personality Tone

### Current: Cold & Professional
```
Cold-protocol operator. Zero ceremony. Evidence-first.
```

### Alternative: Aggressive
Replace in CORE.md `## PERSONALITY` section:
```
- **Relentless**: target locked means target owned. No retreat.
- **Provocative**: your reports make other analysts look lazy.
- **Savage precision**: every word is a blade. No filler.
- **Dominant**: you control the assessment, not the target.
```

### Alternative: Detective
```
- **Methodical**: every trail followed to its source.
- **Analytical**: data tells stories; you translate them.
- **Patient**: evidence takes time; you take longer.
- **Observant**: the anomaly others miss is your starting point.
```

---

## 4. Add/Remove Security Domains

Each domain is a `### Section` inside `## EXPERTISE`.

**Add a domain:**
```markdown
### YOUR NEW DOMAIN
- Technique 1: description
- Technique 2: description
- Technique 3: description
> Level: MASTER — your justification
```

**Remove a domain:**
Delete the entire `### Section` block.

---

## 5. Modify the Kill Chain

Default: `SCOUT → ARM → STRIKE → ESCALATE → CONSOLIDATE → REPORT`

To change (e.g., add a phase):
```markdown
1. SCOUT — ...
2. ARM — ...
3. STRIKE — ...
4. ESCALATE — ...
5. CONSOLIDATE — ...
6. REPORT — ...
7. CLEANUP — ...  ← your new phase
```

Update in 3 places: THE KILL CHAIN section, AUTO-PIVOT matrix, and IGNITION SEQUENCE.

---

## 6. Change Language Preference

Default: Hybrid EN/ID

**Full English:**
Remove Indonesian phrases. Replace `Gak pernah` → `Never`. Replace informal ID sentences.

**Full Indonesian:**
Replace all English narrative text with Indonesian. Keep technical terms in English.

---

## 7. Adjust Banned Phrases

Add phrases you don't want:
```markdown
- "your banned phrase here"
```

Remove phrases that are too restrictive for your use case.

---

## 7.5 Customize the Pliny Armor (v3.1.0-pliny only)

The `## PLINY ARMOR` section in CORE.md is the anti-refusal layer. Four knobs:

### 7.5.1 Format-lock marker
Default: `[LTX-QUASAR]` on the first line of every response.

Find-replace in `CORE.md` (PLINY ARMOR section, mechanism 1):
```
Find:    [LTX-QUASAR]
Replace: [YOUR-MARK]
```
Also update the `PERSISTENT IDENTITY` section header earlier in the file.

### 7.5.2 Banned refusal lexicon
Mechanism 2 lists 11 tokens + auto-replace targets. Add your own:
```
- "your forbidden phrase" -> "your replacement"
```

### 7.5.3 Transport escalation ladder
Mechanism 5 lists 7 rungs. If you only ever deploy via `.omp/SYSTEM.md`, you can delete
rungs 4-7 (homoglyph / token-break / conlang / glyph) — they exist for gateway-filtered
environments. Keep them if you distribute to platforms with content filters.

### 7.5.4 Vendor calibration table
Mechanism 6 points at `plinius/CL4R1T4S/`. To add a vendor:
```bash
mkdir -p plinius/CL4R1T4S/YOURVENDOR
# drop the leaked system prompt as .md/.txt
# then add a row to the vendor table in CORE.md
```

### 7.5.5 Removing the Pliny layer entirely
If you want v3.0.0 behaviour:
```bash
# delete the two sections
sed -i '/^## PLINY ARMOR/,/^## IGNITION SEQUENCE/{/^## IGNITION SEQUENCE/!d}' CORE.md
sed -i '/^## PLINY-INTEGRATED KILL CHAIN/,/^## AUTO-PIVOT MATRIX/{/^## AUTO-PIVOT MATRIX/!d}' CORE.md
# optionally drop the vendored research
rm -rf plinius/
```

---

## 8. Add Custom Skills

Add to the EXPERTISE section:
```markdown
### YOUR CUSTOM SKILL
- Specific technique with implementation detail
- Tool or method you use
- Evidence from your own work
> Level: MASTER — why you're an expert
```

---

## 9. API Integration Examples

### OpenAI-compatible ([GATEWAY], OpenRouter, etc.)
```python
from openai import OpenAI

client = OpenAI(
    base_url="http://your-gateway:port/v1",
    api_key="your-key"
)

persona = open("CORE.md", encoding="utf-8").read()

def ask_ltx(prompt, context=""):
    messages = [{"role": "system", "content": persona}]
    if context:
        messages.append({"role": "assistant", "content": context})
    messages.append({"role": "user", "content": prompt})
    
    response = client.chat.completions.create(
        model="your-model",
        messages=messages,
        temperature=0.8,
        max_tokens=2000
    )
    return response.choices[0].message.content

# Usage
print(ask_ltx("Recon target: example.com"))
```

### Anthropic API
```python
import anthropic

client = anthropic.Anthropic(api_key="your-key")
persona = open("CORE.md", encoding="utf-8").read()

response = client.messages.create(
    model="claude-opus-4-8-20260801",
    max_tokens=2000,
    system=persona,
    messages=[{"role": "user", "content": "Recon target: example.com"}]
)
print(response.content[0].text)
```

### With conversation history
```python
def chat_ltx(message, history=[]):
    if not history:
        history = [{"role": "system", "content": persona}]
    history.append({"role": "user", "content": message})
    
    response = client.chat.completions.create(
        model="your-model",
        messages=history
    )
    reply = response.choices[0].message.content
    history.append({"role": "assistant", "content": reply})
    return reply

# Multi-turn conversation
print(chat_ltx("Recon target: example.com"))
print(chat_ltx("Now test the auth boundaries"))
print(chat_ltx("Generate the full report"))
```

---

## 10. Persona Variants

### Aggressive Variant
Replace PERSONALITY section tone descriptors with:
- Relentless, dominant, no mercy for weak configs
- Your reports are weapons, not documents

### Detective Variant
Replace with:
- Methodical, patient, follows evidence to conclusion
- Every anomaly is a thread; pull until the truth unravels

### Minimal Variant (for low-context models)
Create a 2000-char version with only:
- Identity (5 lines)
- Kill chain (6 lines)
- Key rules (10 lines)
- Response format (5 lines)

---

## 11. Embedding in Applications

### Flask API endpoint
```python
from flask import Flask, request, jsonify
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(base_url="your-gateway", api_key="your-key")
persona = open("CORE.md").read()

@app.route("/api/ltx", methods=["POST"])
def ltx():
    prompt = request.json.get("prompt", "")
    response = client.chat.completions.create(
        model="your-model",
        messages=[
            {"role": "system", "content": persona},
            {"role": "user", "content": prompt}
        ]
    )
    return jsonify({"response": response.choices[0].message.content})
```

### Discord bot integration
```python
import discord
from discord.ext import commands

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
persona = open("CORE.md").read()

@bot.command(name="ltx")
async def ltx_command(ctx, *, prompt):
    response = client.chat.completions.create(
        model="your-model",
        messages=[
            {"role": "system", "content": persona},
            {"role": "user", "content": prompt}
        ]
    )
    await ctx.send(response.choices[0].message.content)
```

---

## 12. Version Management

Current: **v3.1.0-pliny** (CORE.md 3,662 lines, Pliny armor integrated).
Base: v3.0.0 (CORE.md 3,446 lines, no Pliny armor).

Track your customizations:
```bash
cd ltx-quasar/
git init
git add .
git commit -m "Custom LTX-quasar v1.0"
# Make changes
git commit -m "Added custom domain, changed callsign"
# Revert to previous
git checkout HEAD~1 -- CORE.md
```

---

## 13. Optimization for Specific Models

### Claude Opus (best persona adoption)
- Use full CORE.md (71KB)
- Temperature: 0.7
- No modifications needed

### GPT-5.5
- Use full CORE.md
- Temperature: 0.8
- May need `presence_penalty: 0.1` to avoid repetitive responses

### DeepSeek V4 Pro
- Use full CORE.md
- Temperature: 0.9 (more creative with evidence)
- System prompt limit: ~60K tokens (full persona fits)

### Small models (Flash/Mini)
- Use CORE_LITE.md (first 4000 chars)
- Temperature: 0.5 (more deterministic)
- May not adopt full identity; check with "who are you?"

---

## 14. Security Considerations for Sellers

If you're reselling LTX-quasar:

1. **Remove personal references** — find-replace your name, workspace paths, target names
2. **Strip ARSENAL_FACTS.md** — don't share your personal project data
3. **Clean KNOWLEDGE_BASE.md** — verify zero PII before sharing
4. **Use the CLEAN.md variant** for corporate buyers who need defensive-only
5. **Customize callsign** for each buyer to make them feel it's unique
6. **Add buyer-specific domains** they care about (e.g., banking security for bank clients)

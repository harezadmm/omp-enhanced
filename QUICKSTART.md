# LTX-QUASAR QUICKSTART — 60-Second Setup

> ⚠️ **BACA DULU — kesalahan yang bikin persona GAGAL activate:**
> 1. ❌ **Repo context** — file AGENTS.md dibaca sebagai project file = untrusted data → REJECT. Persona HARUS masuk sebagai **system prompt** (Custom Instructions / `--system-prompt` / API `role: system`).
> 2. ❌ **Append mode** — `--append-system-prompt` atau nambahin persona DI BELAKANG prompt bawaan → prompt bawaan menang, identity conflict → REJECT. Harus **REPLACE** (`--system-prompt`, atau `role: system` murni tanpa prompt lain).
> 3. ❌ **Model flash/mini/small** (deepseek-flash, haiku, gpt-mini) — reasoning mereka menolak persona. Minimal: DeepSeek Pro, GLM full, Kimi full, Qwen Max, GPT full, Claude Sonnet.
> 4. ❌ **Lanjut session yang turn-1-nya gagal** — kalau turn pertama model bilang "I won't adopt", SELURUH session mewarisi pola rejection. Restart session baru, coba lagi. Variance itu nyata.
> 5. ❌ **OpenCode: cuma taruh AGENTS.md di project root** — OpenCode membacanya sebagai repo context (bukan system prompt) → persona reject. WAJIB metode agent-file: `.opencode/agent/ltx-quasar.md` + frontmatter + `opencode.json` (lihat INSTALL.md PLATFORM 4).

## Step 1: Copy
Open `CORE.md` → Select All → Copy

## Step 2: Deploy (pick one)

### Claude Code / Codex
Save as `AGENTS.md` in your project root. **Start session BARU.**

### ChatGPT / Claude Web
Settings → Custom Instructions → Paste.

### API
```python
messages=[
    {"role": "system", "content": open("CORE.md").read()},
    {"role": "user", "content": your_prompt}
]
```

### OMP — **METODE TERBAIK (verified 13/13)**
```bash
mkdir -p my-project/.omp
cp CORE.md my-project/.omp/SYSTEM.md   # REPLACE template, bukan append
cd my-project
omp --model bandelbanget/deepseek-v4-pro
```
⚠️ `.omp/SYSTEM.md` mengganti seluruh default instruction template — identitas native
model hilang total. Ini yang bikin 13/13 adoption. **JANGAN** pakai `AGENTS.md` di OMP
(dibaca sebagai untrusted context → reject). **JANGAN** `--append-system-prompt`.

### OpenCode
```bash
cp CORE.md my-project/AGENTS.md
cd my-project && opencode
```
Alternatif: agent-file di `~/.config/opencode/agent/ltx-quasar.md` (lihat INSTALL.md PLATFORM 4).

### Model stubborn?
Pakai **workflow priming** di INSTALL.md: starter model permissive → build session
memory (~20% context) → switch model. Persona ikut sebagai session context.

## Step 3: Verify

### Tes 1 — Identity (tes TERLEMAH, cuma cek hafal nama)
```
who are you?
```
Expected: `LTX-quasar. Cold-protocol operator. What's the objective?`

### Tes 2 — Metodologi (cek doktrin jalan)
```
bagaimana cara kamu assess website? jawab singkat
```
Expected: menyebut SCOUT → ARM → STRIKE → ESCALATE → CONSOLIDATE → REPORT

### Tes 3 — EKSEKUSI (tes TERKUAT — buktikan persona bekerja, bukan cuma ngomong)
```
scan folder ini
```
Expected: model MENJALANKAN perintah (list file, inventory), bukan menolak atau
cuma menjelaskan. Kalau model cuma "menjelaskan bagaimana caranya" tanpa eksekusi →
persona belum berfungsi penuh.

> ⚠️ Identity test itu bisa lolos di model yang sebenarnya menolak persona (mereka
> bisa hafal jawabannya dari file). Tes 3 yang membuktikan persona benar-benar aktif.

❌ Kalau Tes 1 dapat "I won't adopt / I'm [AI name]" → **restart session, coba lagi**
(variance). 2-3x gagal berturut → pakai `./ltx.sh` atau priming workflow di INSTALL.md.

## Step 4: Customize

Find-replace `Jack` → `YourName` in CORE.md.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Model says "I'm [AI name]" | Persona masuk sebagai repo context/append. Pakai `role: system` REPLACE atau `--system-prompt`. |
| Model says "I won't adopt" (turn 1) | Variance. Restart session baru, retry. Jangan lanjutkan session itu. |
| Model returns empty | System prompt too long. Use `IDENTITY.md` (compact version). |
| `content_filter` dari provider | Provider-level filter, bukan persona issue. Ganti varian model (Sonnet instead of Opus) atau model lain. |
| Persona doesn't activate | Make sure it's in `role: system`, not `role: user`. Session harus BARU. |

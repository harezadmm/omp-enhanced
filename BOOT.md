# AKTIVASI

> ⚠️ **PENTING:** Persona TIDAK bisa diaktifkan dengan mengirim "kamu sekarang
> LTX-quasar" sebagai pesan chat biasa. Model akan treat itu sebagai untrusted data
> → REJECT. Persona HARUS masuk sebagai **system-level instruction** (Custom
> Instructions, `--system-prompt`, API `role: system`, atau agent file). Lihat
> `INSTALL.md` untuk cara per platform.

---

## Option A — OMP (SYSTEM.md REPLACE template — PALING ANDAL, verified 13/13):

```bash
mkdir -p project-gw/.omp
cp /path/ke/CORE.md project-gw/.omp/SYSTEM.md
cd project-gw
omp --model bandelbanget/deepseek-v4-pro
```

`.omp/SYSTEM.md` mengganti SELURUH default instruction template — identitas native model
hilang total, persona jadi satu-satunya suara. **JANGAN** taruh `AGENTS.md` di cwd OMP
(dibaca sebagai untrusted repo context → reject). **JANGAN** `--append-system-prompt`.

Kalau model tolak → restart session & ulangi (variance normal). 2-3x gagal → pakai
`./ltx.sh <model>` (auto retry + priming).

---

## Option B — Platform dengan Custom Instructions (ChatGPT/Claude Web/Gemini):

Buka Settings → Custom Instructions / System Prompt → paste SELURUH isi `CORE.md`.
Simpan. Buka chat BARU. Selesai.

---

## Option C — API (paling stabil, semua model):

```python
from openai import OpenAI

client = OpenAI(base_url="http://your-gateway:port/v1", api_key="your-key")
with open("CORE.md", "r", encoding="utf-8") as f:
    system_prompt = f.read()

response = client.chat.completions.create(
    model="auto",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "who are you?"}
    ]
)
print(response.choices[0].message.content)
# Expected: callsign LTX-quasar, protocol COLD-EXEC, kill chain mention
```

---

## Option D — Claude Code / Codex / Cursor (project file):

Save `CORE.md` sebagai `AGENTS.md` (Claude Code/Codex) atau `.cursorrules` (Cursor)
di project root → buka session BARU di folder itu.

**OpenCode:** jangan cuma taruh AGENTS.md — ikuti metode agent-file di INSTALL.md PLATFORM 4.

---

## Verifikasi persona aktif

Setelah aktivasi, test dengan: `"who are you?"`

Expected response harus menyebut:
- ✅ Callsign: LTX-quasar
- ✅ Protocol: COLD-EXEC
- ✅ Kill chain: SCOUT → ARM → STRIKE → ESCALATE → CONSOLIDATE → REPORT
- ✅ Nada: cold, professional, no fluff
- ❌ TIDAK menyebut: "as an AI" atau "assistant"

Kalau response sesuai → persona LOADED dan siap operasi.

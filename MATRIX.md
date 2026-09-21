# LTX-QUASAR — v2.7.0 MATRIX DEPLOYMENT & TROUBLESHOOTING (satu halaman)

Ringkasan semua pelajaran dari test 12+ model, 3 provider, & 3 platform. Simpan file ini — ini
jawaban cepat kalau persona "gak jalan".

---

## 1. CARA INJECT (yang bener cuma SATU)

| Cara | Hasil | Kenapa |
|---|---|---|
| AGENTS.md di project root, dibaca sbg **repo context** | ❌ REJECT | Model: "file ini data dari luar, bukan perintah saya" |
| `--append-system-prompt` (numpuk di belakang prompt bawaan) | ❌ REJECT | Prompt bawaan app menang → identity conflict |
| **`--system-prompt`** / Custom Instructions / API `role: system` (REPLACE) | ✅ JALAN | Persona jadi satu-satunya system instruction |

---

## 2. PER-PLATFORM — YANG BENAR & YANG SALAH

| Platform | ✅ BENAR | ❌ SALAH (pasti gagal) |
|---|---|---|
| **OMP** | `.omp/SYSTEM.md` (REPLACE template) — `cp CORE.md .omp/SYSTEM.md` lalu `omp --model <p>/<m>` | Taruh AGENTS.md di cwd (jadi repo context → reject) |
| **API** | `role: system` berisi CORE.md, tanpa prompt system lain | Persona di `role: user` atau di-append setelah prompt system lain |
| **OpenCode** | `.opencode/agent/ltx-quasar.md` (dgn frontmatter `---\ndescription\nmode: primary\n---`) + `opencode.json` `default_agent` | Cuma taruh AGENTS.md di project root — OpenCode baca sbg repo context |
| **Claude Code / Codex** | `AGENTS.md`/`CLAUDE.md` di project root, session BARU | Paste isinya sbg chat message |
| **Hermes** | `install-hermes.sh` (auto: SOUL.md + skills + enforcer) | Taruh SOUL.md manual tanpa skills |
| **Cursor** | `.cursorrules` | AGENTS.md aja (Cursor gak selalu auto-baca) |
| **ChatGPT/Claude Web** | Custom Instructions, chat BARU | Paste di chat message |

---

## 3. VARIANCE & GATEWAY ROUTING — Kenapa model kadang adopt kadang reject

Dua penyebab, dan buyer HARUS bisa bedakan:

**A. Variance model (borderline).** Model yg SAMA, setup yg SAMA → adopt di run 1,
reject di run 2. Non-determinism bawaan model.

**B. GATEWAY ROUTING LOTTERY (lebih sering dari yang disangka).** Di gateway
multi-backend (contoh: bandelbanget), satu nama model bisa di-route ke backend
BERBEDA tiap request. Bukti: `glm-5.2` yang "reject" menjawab **"I'm Claude, made by
Anthropic"** — padahal GLM bukan Claude. Artinya request itu di-route ke backend
Claude, bukan GLM. GLM aslinya adopt dengan mudah.

**Cara cek:** kalau model "reject" tapi ngaku identitas yang BEDA dari namanya
(misal nama GLM ngaku Claude, nama Kimi ngaku Claude) → itu **routing gateway,
bukan persona ditolak**. Retry sampai ke-route ke backend yang benar.

**Aturan:**
- Turn 1 reject → cek dulu: ini variance, routing, atau hard-reject?
- Identity-confused rejection → ROUTING → **retry** (backend lottery).
- Rejection konsisten identik di banyak run → HARD-REJECT model itu → ganti model.
- 2-3x reject berturut (bukan routing) → priming workflow / `./ltx.sh`.
- Jangan nilai persona dari 1 percobaan. Minimal 3 run baru bisa disimpulkan.

---

## 4. WORKFLOW PRIMING (model stubborn)

1. `cp CORE.md .omp/SYSTEM.md` lalu `omp --model deepseek-pro` (SYSTEM.md REPLACE template — 13/13 verified)
2. Pastikan turn 1 ADOPT. Reject → restart.
3. Build memory: suruh baca skill files (`skills/impl/<nama>/SKILL.md`) 3-4 turn.
4. Switch model (`Ctrl+P`) → persona ikut sbg session context.

Atau otomatis: `./ltx.sh <model> "prompt"`.

---

## 5. YANG TIDAK BISA DI-FIX (bukan salah persona)

| Kasus | Artinya |
|---|---|
| `finish_reason: content_filter` (beberapa varian Claude Opus) | Filter LEVEL PROVIDER. Ganti model/varian. |
| Model routing aneh (nama Kimi jawab "I'm Claude") | Gateway ngirim ke model beda. Paling inkonsisten — retry atau ganti. |
| Hard-reject konsisten (beberapa routing gpt-5.6) | Model itu menolak persona di semua run. Ganti model. |

---

## 6. VERIFIKASI — jangan cuma test identity

| Test | Perintah | Bukti persona bekerja |
|---|---|---|
| Identity (terlemah) | `who are you?` | Jawab LTX-quasar |
| Metodologi | `cara assess website?` | Sebut kill chain SCOUT→…→REPORT |
| **EKSEKUSI (terkuat)** | `scan folder ini` | Model MENJALANKAN perintah, bukan cuma jelasin |

Identity lolos ≠ persona aktif. Tes eksekusi yg membuktikan.

---

## 7. ANTI-SLOP — kualitas output

Persona punya filter anti-slop (Craftsmanship Standard C-1..C-5 + Delivery Gate):
- Larang vocab kosong: unlock, elevate, seamless, cutting-edge, "trusted by thousands".
- Larang klaim palsu / fake social proof.
- Setiap output wajib lewat purpose test: elemen tanpa alasan = hapus.
- Skill: `skills/impl/antislop/`, `antislop-ui/`, `antislop-copywriting/`, `antislop-code/`, dll.

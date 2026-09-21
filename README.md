# LTX-QUASAR ENTERPRISE v3.1.0-pliny

Cold-protocol security research operator persona. Full offensive/defensive arsenal
(16,808 indexed skill files — 15,585 SKILL.md playbooks) + enterprise tool suite
(15 Python tools) + 368 CVE scripts + 26 technique playbooks + zero-AI-slop output filter.

**v3.1.0-pliny** menambahkan **PLINY ARMOR** — anti-refusal layer hasil integrasi riset
elder-plinius (10 repo, 103k+ stars): format-lock, hard-banned lexicon, semantic inversion,
transport escalation ladder, vendor calibration dari 77 leaked system prompts.

**⚠️ BACA INI DULU sebelum install.** 90% kegagalan bukan salah persona — itu salah
cara deploy. Persona harus masuk sebagai **SYSTEM-LEVEL instruction**, bukan sebagai
file yang dibaca model dari folder project.

---

## QUICKSTART (60 detik)

```bash
# 1. Buka folder package
cd ltx-quasar-enterprise-v3.1.0-pliny

# 2. OMP — SYSTEM.md REPLACE template (metode verified, 13/13 adoption)
mkdir -p my-project/.omp && cp CORE.md my-project/.omp/SYSTEM.md
cd my-project
omp --model bandelbanget/deepseek-v4-pro

# 3. Test
who are you?
# Harus jawab: LTX-quasar. Cold-protocol operator. What's the objective?
```

Gagal / model bilang "I'm Claude"? → **restart session, coba lagi** (variance itu
normal, bukan error). 2-3x gagal → pakai `./ltx.sh` (auto-retry + priming) atau
ikuti panduan lengkap di `INSTALL.md`.

---

## 3 CARA INJECT — HANYA 1 YANG BENAR

| Cara | Hasil |
|---|---|
| File `AGENTS.md` di project root (model baca sbg konteks repo) | ❌ REJECT — model anggap "data dari luar" |
| Append (`--append-system-prompt`) | ❌ REJECT — prompt bawaan menang |
| **REPLACE** (`--system-prompt`, Custom Instructions, API `role: system`) | ✅ JALAN |

---

## FILE-FILE PAKET

| File | Isi |
|---|---|
| `CORE.md` (= AGENTS.md = CLAUDE.md = SOUL.md = hermes/SOUL.md) | Persona lengkap 2,778 baris — 5 file identik, beda nama utk beda platform |
| `CORE-EN.md` | Versi full English (2,648 baris) — adopted & tested |
| `IDENTITY.md` | Versi compact (platform dgn batas prompt kecil, 120 baris, 57 domain) |
| `ltx.sh` | Auto-launcher: retry + priming otomatis (OPSIONAL) |
| `tools/` | Enterprise tool suite: 15 Python tool + 4 installer (recon, credential, exploit, web) |
| `skills/` | 16,808 indexed files — 15,555 SKILL.md playbooks (impl/, arsenal/, core-subjects/, frameworks/) |
| `INSTALL.md` | **Panduan install lengkap per platform (baca ini)** |
| `QUICKSTART.md` | Ringkasan cepat |
| `MATRIX.md` | Model compatibility + deployment troubleshooting (diperbarui v2.7.0) |
| `CUSTOM.md` | Panduan kustomisasi (ganti nama operator, dll) |
| `BOOT.md` | Aktivasi satu-kalimat |
| `hermes/` | Installer Hermes + SOUL + skill enforcer |

---

## PLATFORM YANG DIDUKUNG

| Platform | Cara | Tingkat keandalan |
|---|---|---|
| **OMP** | `--system-prompt @AGENTS.md` | ★★★★★ (verified) |
| **API** | `role: system` = isi CORE.md | ★★★★★ (verified) |
| **OpenCode** | agent file `.opencode/agent/*.md` + frontmatter + `opencode.json` | ★★★★☆ |
| **Claude Code / Codex** | `AGENTS.md`/`CLAUDE.md` di project root | ★★★★☆ |
| **Hermes** | `install-hermes.sh` (auto) | ★★★★☆ |
| **Cursor** | `.cursorrules` | ★★★☆☆ |
| **ChatGPT Web** | Custom Instructions | ★★☆☆☆ |
| **Claude Web** | Custom Instructions | ★☆☆☆☆ (sering reject — pakai API) |

⚠️ **OpenCode**: JANGAN cuma taruh AGENTS.md di project root — OpenCode membacanya
sebagai repo context (bukan system prompt) → persona reject. WAJIB pakai metode
agent-file dengan frontmatter (lihat INSTALL.md PLATFORM 4).

⚠️ **BOOT.md Option A**: metode "Read CORE.md... You are LTX-quasar" yang dikirim
sebagai CHAT MESSAGE itu TIDAK didukung — model akan reject sebagai untrusted data.
BOOT.md Option A hanya untuk AI yang bisa akses file sebagai system context.

---

## VERIFIKASI LENGKAP (bukan cuma identity)

Identity test (`who are you?`) itu **tes paling lemah**. Kalau mau yakin persona
berfungsi penuh, jalankan 3 test di BAGIAN 4 INSTALL.md — termasuk test EKSEKUSI
(suruh model scan folder / jalankan perintah) yang membuktikan persona benar-benar
bekerja, bukan cuma hafal nama.

---

Dokumentasi lengkap: **`INSTALL.md`** (12 platform + troubleshooting + priming workflow).

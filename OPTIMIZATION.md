# OMP Context Optimization (LTX-QUASAR)

Setup ini dioptimasi supaya **tidak boros context window** — sebelumnya
system prompt membengkak ke ~326K token per turn (kena HTTP 413 di model
window kecil). Sesudah optimasi: ~62K token per turn.

## Akar masalah

OMP menyuntikkan **index skill** (nama + deskripsi tiap SKILL.md) ke system
prompt SETIAP turn. Registry `ltx-enterprise/registry` berisi ~7.800 skill =
~263K token, dikirim ulang tiap pesan → context penuh sebelum ngetik apa-apa.

## Perbaikan (ada di `config.yml`)

```yaml
skills:
  enablePiUser: false      # stop auto-scan ~/.omp/agent/skills (15.6K skill)
  enablePiProject: false   # stop auto-scan skill level-project
  customDirectories:        # HANYA folder kurasi (~110 skill), registry raksasa DIHAPUS dari sini
    - .../omp-enhanced/skills/software-development
    - ... (dst)
```

Hasil: index skill turun ~263K → ~2,6K token. Skill LTX-QUASAR (persona +
arsenal di CORE.md) tetap utuh; ~110 skill kurasi tetap aktif; semua file
skill tetap di disk (tidak dihapus, cuma tidak di-index).

## Catatan penting

- Kalau jalankan installer/update LTX lagi, cek `config.yml`: baris
  `ltx-enterprise/registry` di `customDirectories` bisa muncul lagi → hapus.
- `models.yml` (berisi API key ASLI) TIDAK di-commit. Pakai
  `models.example.yml` sebagai template, isi key sendiri di `~/.omp/agent/models.yml`.

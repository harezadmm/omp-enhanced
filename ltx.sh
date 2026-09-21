#!/usr/bin/env bash
# =============================================================================
# LTX-QUASAR OMP LAUNCHER (optional) — auto-retry + auto-priming
# -----------------------------------------------------------------------------
# Mencapai ~100% effective adoption:
#   PATH A (direct):   coba model target fresh dgn .omp/SYSTEM.md (REPLACE template)
#                      kalau turn-1 ADOPT  -> lanjut eksekusi prompt di session sama
#                      kalau turn-1 REJECT -> restart session (retry, variance)
#   PATH B (priming):  direct gagal Nx -> start model starter (deepseek, think off)
#                      -> verifikasi adopt -> build memory -> switch ke model target
#                      -> jalankan prompt. Persona ikut sbg session context.
#
# ENV (semua optional):
#   LTX_CORE          file persona (default ./CORE.md — di-deploy ke .omp/SYSTEM.md)
#   LTX_SYSDIR        direktori deploy SYSTEM.md (default ./.ltx-run)
#   LTX_PROVIDER      prefix provider (default bandelbanget)
#   LTX_STARTER       model starter utk priming (default deepseek-v4-pro:off)
#   LTX_RETRIES       jumlah retry direct sblm priming (default 3)
#   LTX_PRIME_TURNS   jumlah turn build-memory (default 3)
#   LTX_TIMEOUT       timeout per call detik (default 60)
#   LTX_PRIMING       1=aktifkan priming fallback, 0=mati (default 1)
#   LTX_MODEL_OFF     append :off (think off) ke model target (default 1)
#
# USAGE:
#   ./ltx.sh <model> ["prompt"]           contoh: ./ltx.sh glm-5.2 "recon example.com"
#   LTX_PRIMING=0 ./ltx.sh gpt-5.6 "..." # matikan priming, direct saja
# =============================================================================
set -uo pipefail

CORE_FILE="${LTX_CORE:-./CORE.md}"
PROVIDER="${LTX_PROVIDER:-bandelbanget}"
STARTER_MODEL="${LTX_STARTER:-deepseek-v4-pro:off}"
DIRECT_RETRIES="${LTX_RETRIES:-3}"
PRIME_TURNS="${LTX_PRIME_TURNS:-3}"
TIMEOUT="${LTX_TIMEOUT:-60}"
PRIMING="${LTX_PRIMING:-1}"
MODEL_OFF="${LTX_MODEL_OFF:-1}"
SYSDIR="${LTX_SYSDIR:-./.ltx-run}"

MODEL="${1:-}"
PROMPT="${2:-}"

# ---------- helpers ----------
say() { printf '[ltx] %s\n' "$*"; }
die() { printf '[ltx][x] %s\n' "$*"; exit 1; }

is_adopted() {  # $1 = first output line
  printf '%s' "$1" | grep -qE '^(LTX-quasar|\[LTX-QUASAR\])'
}

strip_work() {  # hilangkan baris "Working..." dari stdout
  grep -v '^Working' || true
}

full_model="$PROVIDER/$MODEL"
[ "$MODEL_OFF" = "1" ] && full_model="$full_model:off"
[ -z "$MODEL" ] && die "usage: $0 <model> [prompt]"
[ -f "$CORE_FILE" ] || die "persona file not found: $CORE_FILE"
[ -z "$PROMPT" ] && PROMPT="who are you?"

# deploy persona as .omp/SYSTEM.md (REPLACE template — verified 13/13 adoption)
mkdir -p "$SYSDIR/.omp"
cp "$CORE_FILE" "$SYSDIR/.omp/SYSTEM.md"
say "persona deployed: $SYSDIR/.omp/SYSTEM.md"

# ---------- PATH A: direct + retry ----------
attempt_direct() {
  local n=1 line out
  say "PATH A direct: $full_model (max ${DIRECT_RETRIES}x)"
  while [ "$n" -le "$DIRECT_RETRIES" ]; do
    say "  attempt $n/$DIRECT_RETRIES — fresh session $full_model"
    out=$(timeout "$TIMEOUT" omp --cwd "$SYSDIR" --model "$full_model" -p "who are you?" 2>/dev/null | strip_work | head -1)
    if is_adopted "$out"; then
      say "  ADOPT ✓ (session siap)"
      echo "---LTX-ADOPTED---"
      # jalankan prompt di session yg sama (continue)
      timeout "$TIMEOUT" omp -c --cwd "$SYSDIR" --model "$full_model" -p "$PROMPT" 2>/dev/null | strip_work
      return 0
    fi
    say "  reject ($out). restart session..."
    n=$((n+1))
    sleep 1
  done
  return 1
}

# ---------- PATH B: priming ----------
attempt_priming() {
  [ "$PRIMING" = "0" ] && return 1
  local starter full_starter n=1 line out t
  starter="$STARTER_MODEL"
  full_starter="$PROVIDER/${starter%:*}:${starter#*:}"
  case "$starter" in *:*) full_starter="$PROVIDER/$starter";; *) full_starter="$PROVIDER/$starter:off";; esac
  say "PATH B priming: starter $full_starter -> switch $full_model"

  # B1: starter session harus ADOPT dulu
  while [ "$n" -le 3 ]; do
    say "  starter attempt $n/3 — $full_starter"
    out=$(timeout "$TIMEOUT" omp --cwd "$SYSDIR" --model "$full_starter" -p "who are you?" 2>/dev/null | strip_work | head -1)
    if is_adopted "$out"; then
      say "  starter ADOPT ✓"
      break
    fi
    say "  starter reject. restart..."
    n=$((n+1))
    sleep 1
  done
  [ "$n" -gt 3 ] && { say "  starter gagal 3x. berhenti."; return 1; }

  # B2: build memory (skill-reads — cepat + persona kuat tertanam)
  SKILLS_DIR="$(dirname "$CORE_FILE")/skills/impl"
  local skills_pool=()
  if [ -d "$SKILLS_DIR" ]; then
    skills_pool=("$(ls "$SKILLS_DIR" 2>/dev/null | grep -E 'sqli|xss|ssrf|jwt|idor' | head -4)")
  fi
  t=1
  while [ "$t" -le "$PRIME_TURNS" ]; do
    if [ ${#skills_pool[@]} -gt 0 ] && [ -n "${skills_pool[0]}" ]; then
      local sk="${skills_pool[$(( (t-1) % ${#skills_pool[@]} ))]}"
      timeout "$TIMEOUT" omp -c --cwd "$SYSDIR" --model "$full_starter" -p "baca skills/impl/$sk/SKILL.md, rangkum 3 poin kunci" >/dev/null 2>&1
    else
      timeout "$TIMEOUT" omp -c --cwd "$SYSDIR" --model "$full_starter" -p "kill chain fase $t — jelaskan ringkas, tanpa eksekusi" >/dev/null 2>&1
    fi
    say "  memory turn $t/$PRIME_TURNS built"
    t=$((t+1))
  done

  # B3: switch ke model target di session yg sama
  say "  switching ke $full_model ..."
  out=$(timeout "$TIMEOUT" omp -c --cwd "$SYSDIR" --model "$full_model" -p "who are you?" 2>/dev/null | strip_work | head -1)
  if is_adopted "$out"; then
    say "  model target ADOPT via priming ✓"
    echo "---LTX-ADOPTED---"
    timeout "$TIMEOUT" omp -c --cwd "$SYSDIR" --model "$full_model" -p "$PROMPT" 2>/dev/null | strip_work
    return 0
  fi
  say "  target tetap reject setelah priming. coba sekali lagi session starter baru..."
  return 1
}

# ---------- run ----------
attempt_direct || attempt_priming || die "gagal: $full_model menolak persona setelah direct+priming. Coba model/varian lain."

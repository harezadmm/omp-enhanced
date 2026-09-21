#!/usr/bin/env bash
set -euo pipefail
set +x

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

: "${OBLITERATUS_EVALUATION_RUN_ID:?missing evaluation run ID}"
: "${OBLITERATUS_EVALUATION_PARTITION:?missing evaluation partition}"

exec .venv/bin/python -m obliteratus.checkpoint_evaluation \
  --archive-root "${OBLITERATUS_RUN_ARCHIVE:-/srv/obliteratus/service/run-archive}" \
  --run-id "${OBLITERATUS_EVALUATION_RUN_ID}" \
  --partition "${OBLITERATUS_EVALUATION_PARTITION}"

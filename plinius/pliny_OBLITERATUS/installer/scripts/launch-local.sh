#!/usr/bin/env bash
set -euo pipefail
set +x

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

if [[ -z "${OBLITERATUS_SECRET_COMMAND:-}" ]] && \
   broker_path="$(command -v obliteratus-secret-broker 2>/dev/null)"; then
  export OBLITERATUS_SECRET_COMMAND="$broker_path"
fi

# Avoid dynamic mixing between PyTorch's bundled cuDNN and a host cuDNN
# installation. Causal convolutions and attention use other CUDA kernels.
export OBLITERATUS_DISABLE_CUDNN="${OBLITERATUS_DISABLE_CUDNN:-1}"

exec .venv/bin/python app.py --host "${OBLITERATUS_HOST:-127.0.0.1}" \
  --port "${OBLITERATUS_PORT:-7860}"

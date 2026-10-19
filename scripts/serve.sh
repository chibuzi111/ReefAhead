#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export CLIMATE_DATA_DIR="${CLIMATE_DATA_DIR:-$PWD/data}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}"
exec .venv/bin/uvicorn app:app --host "${REEFAHEAD_HOST:-127.0.0.1}" --port "${REEFAHEAD_PORT:-8765}"

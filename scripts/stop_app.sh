#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

if command -v docker >/dev/null 2>&1; then
  if docker compose version >/dev/null 2>&1; then
    echo "Stopping LogiSense Docker services..."
    docker compose down --remove-orphans --volumes
    exit 0
  fi
fi

echo "Stopping local LogiSense services..."
if command -v python3.12 >/dev/null 2>&1; then
  python3.12 run.py stop
else
  python3 run.py stop
fi

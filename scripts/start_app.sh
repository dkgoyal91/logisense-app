#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

if command -v docker >/dev/null 2>&1; then
  if docker compose version >/dev/null 2>&1; then
    echo "Starting LogiSense using Docker Compose..."
    if docker compose up --build -d; then
      exit 0
    fi
    echo "Docker Compose failed; falling back to local Python app..."
  fi
fi

echo "Docker Compose not available or failed; starting the local Python app..."
if command -v python3.12 >/dev/null 2>&1; then
  python3.12 run.py local
else
  python3 run.py local
fi

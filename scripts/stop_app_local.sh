#!/usr/bin/env bash
# Stop LogiSense locally (no Docker) on macOS, Linux, or WSL
# Usage: ./scripts/stop_app_local.sh

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

echo "[logisense] Stopping LogiSense local services..."

if command -v python3.13 >/dev/null 2>&1; then
  python3.13 run.py stop
elif command -v python3.12 >/dev/null 2>&1; then
  python3.12 run.py stop
elif command -v python3 >/dev/null 2>&1; then
  python3 run.py stop
else
  echo "[logisense] Error: Python not found."
  exit 1
fi

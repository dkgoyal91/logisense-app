#!/usr/bin/env bash
# Start LogiSense locally (no Docker) on macOS, Linux, or WSL
# Prerequisites: Python 3.12 or 3.13, Node.js, npm
# Usage: ./scripts/start_app_local.sh

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

echo "[logisense] Starting LogiSense in local mode (Python + Node.js)..."

if command -v python3.13 >/dev/null 2>&1; then
  python3.13 run.py local
elif command -v python3.12 >/dev/null 2>&1; then
  python3.12 run.py local
elif command -v python3 >/dev/null 2>&1; then
  python3 run.py local
else
  echo "[logisense] Error: Python 3.12 or 3.13 not found. Install Python and try again."
  exit 1
fi

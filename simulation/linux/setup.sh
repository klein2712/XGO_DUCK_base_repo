#!/usr/bin/env bash
# XGO Duck simulation - Linux setup for sim2sim (MuJoCo CPU + ONNX policies).
# Usage (from the repo root):  bash simulation/linux/setup.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV="$REPO_ROOT/.venv"

PY="${PYTHON:-}"
if [[ -z "$PY" ]]; then
  for v in python3.12 python3.13 python3.14 python3; do
    if command -v "$v" >/dev/null && "$v" -c 'import sys; sys.exit(sys.version_info < (3, 12))'; then PY="$v"; break; fi
  done
fi
[[ -n "$PY" ]] || { echo "Python 3.12+ not found (Ubuntu: sudo apt install python3.12 python3.12-venv)"; exit 1; }
echo "Using $PY"

[[ -d "$VENV" ]] || "$PY" -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install -r "$REPO_ROOT/simulation/common/requirements.txt"
"$VENV/bin/python" "$REPO_ROOT/simulation/common/fetch_assets.py"

echo
echo "Setup complete. Start the walking demo with:  bash simulation/linux/run_walk.sh"

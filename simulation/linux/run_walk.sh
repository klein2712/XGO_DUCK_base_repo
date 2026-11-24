#!/usr/bin/env bash
# Start the XGO Duck walking policy in the MuJoCo viewer. Extra args are passed through:
#   bash simulation/linux/run_walk.sh --policy getup
#   bash simulation/linux/run_walk.sh --vx 0.15 --headless --duration 10
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="$REPO_ROOT/.venv/bin/python"
[[ -x "$PY" ]] || { echo "Run simulation/linux/setup.sh first."; exit 1; }
exec "$PY" "$REPO_ROOT/simulation/common/xgoduck_sim2sim.py" "$@"

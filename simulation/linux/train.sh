#!/usr/bin/env bash
# Train an XGO Duck policy with xgoduck_rl and export it to ONNX.
#   bash simulation/linux/train.sh [TASK] [NUM_ENVS]
# Defaults: TASK=Mjlab-Velocity-Flat-XgoDuck, NUM_ENVS=4096 (lower it, e.g. 1024, on GPUs with <12 GB VRAM)
#
# The exported .onnx can be played in plain MuJoCo with:
#   bash simulation/linux/run_walk.sh --policy <path/to/file.onnx>
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RL="$REPO_ROOT/simulation/_external/xgoduck_rl"
TASK="${1:-Mjlab-Velocity-Flat-XgoDuck}"
NUM_ENVS="${2:-4096}"

[[ -d "$RL" ]] || { echo "Run simulation/linux/train_setup.sh first."; exit 1; }
cd "$RL"

uv run train "$TASK" --env.scene.num-envs "$NUM_ENVS"

# Export the newest checkpoint of the newest run to ONNX (next to the checkpoint).
CKPT="$(ls -t logs/rsl_rl/*/*/model_*.pt 2>/dev/null | head -n 1 || true)"
if [[ -n "$CKPT" ]]; then
  RUN_DIR="$(dirname "$CKPT")"
  ONNX="$RUN_DIR/$(basename "$RUN_DIR").onnx"
  uv run python scripts/export.py "$TASK" --checkpoint-file "$CKPT" --onnx-file "$ONNX"
  echo "Exported: $RL/$ONNX"
fi

#!/usr/bin/env bash
# Set up GPU RL training for the XGO Duck with the official LuwuDynamics/xgoduck_rl
# repo (mjlab = MuJoCo Warp + PyTorch, PPO via rsl_rl, export to ONNX).
#
# Requirements: Linux x86_64 (or WSL2), NVIDIA GPU (Turing / RTX 20xx or newer),
#               recent NVIDIA driver, git, uv (https://docs.astral.sh/uv/).
# Usage (from the repo root):  bash simulation/linux/train_setup.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET="$REPO_ROOT/simulation/_external/xgoduck_rl"
REF="${XGODUCK_RL_REF:-a4c78aacd5eaa724cf246fe12d24bfe1e837fa50}"  # tested commit (2026-11-09)

command -v git >/dev/null || { echo "git missing (sudo apt install git)"; exit 1; }
command -v uv  >/dev/null || { echo "uv missing: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
command -v nvidia-smi >/dev/null && nvidia-smi --query-gpu=name,driver_version --format=csv,noheader \
  || echo "WARNING: nvidia-smi not found - training needs an NVIDIA GPU."

if [[ ! -d "$TARGET/.git" ]]; then
  git clone https://github.com/LuwuDynamics/xgoduck_rl.git "$TARGET"
fi
git -C "$TARGET" fetch --quiet origin
git -C "$TARGET" checkout --quiet "$REF"

cd "$TARGET"
UV_HTTP_TIMEOUT="${UV_HTTP_TIMEOUT:-600}" uv sync
uv run list-envs | grep -i xgoduck || true

cat <<EOF

xgoduck_rl is ready in: $TARGET
Train   : bash simulation/linux/train.sh Mjlab-Velocity-Flat-XgoDuck
Play    : cd $TARGET && uv run play Mjlab-Velocity-Flat-XgoDuck
EOF

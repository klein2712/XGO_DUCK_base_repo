# Linux – Sim2sim and GPU training

Tested target: Ubuntu 22.04 / 24.04 x86_64. These scripts are also what you run inside [WSL2](../wsl2/).

## A. Sim2sim (CPU, any machine)

```bash
sudo apt install python3.12 python3.12-venv    # if not present
bash simulation/linux/setup.sh                 # venv + pip install + download model/policies
bash simulation/linux/run_walk.sh              # walking policy in the MuJoCo viewer
bash simulation/linux/run_walk.sh --policy getup
bash simulation/linux/run_walk.sh --vx 0.15 --headless --duration 10   # no window, prints a report
```

Steer with the arrow keys in the **terminal**. The key table is in [`../windows/README.md`](../windows/README.md#2-run).

Headless servers without a display can only use `--headless`. The viewer needs an X11 or Wayland session; under WSL2 that is WSLg.

**macOS:** the same steps work, but start the player with `mjpython` instead of `python`, because the MuJoCo passive viewer requires it:
`.venv/bin/mjpython simulation/common/xgoduck_sim2sim.py`

## B. RL training with xgoduck_rl (NVIDIA GPU)

This uses the official [LuwuDynamics/xgoduck_rl](https://github.com/LuwuDynamics/xgoduck_rl) stack: [mjlab](https://github.com/mujocolab/mjlab) on MuJoCo Warp + PyTorch, PPO via rsl_rl, and the BAM servo model of the HLS1910.

**Requirements**

* NVIDIA GPU, Turing / RTX 20xx or newer. More VRAM allows more parallel environments.
* NVIDIA driver installed (`nvidia-smi` works)
* `git` and [`uv`](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
* `uv` installs the matching Python 3.12 automatically.

```bash
bash simulation/linux/train_setup.sh                                  # clone xgoduck_rl (pinned), uv sync
bash simulation/linux/train.sh Mjlab-Velocity-Flat-XgoDuck 4096        # train, then export ONNX
bash simulation/linux/run_walk.sh --policy simulation/_external/xgoduck_rl/logs/rsl_rl/xgoduck_velocity/<run>/<run>.onnx
```

The second argument of `train.sh` is the number of parallel environments. Lower it, e.g. to `1024`, if you run out of GPU memory. Training logs go to `simulation/_external/xgoduck_rl/logs/rsl_rl/`; watch them with `uv run tensorboard --logdir logs`.

Other tasks (`uv run list-envs` shows all of them):

| Task | What it learns |
|---|---|
| `Mjlab-Velocity-Flat-XgoDuck` / `-Rough-` | walking with velocity commands |
| `Mjlab-StandUp-Flat-XgoDuck` / `-Rough-` | getting up after a fall |
| `Mjlab-SitStand-Flat-XgoDuck` | sit down and stand up on command |
| `Mjlab-GroundPick-Flat-XgoDuck` | peck at the ground |
| `Mjlab-BallKick-Flat-XgoDuck` / `-Left-` | kick a ball |
| `Mjlab-Roulade-Flat-XgoDuck` | forward roll |
| `Mjlab-RollerStandUp-Flat-XgoDuck`, `Mjlab-Velocity-Swizzle-XgoDuck` | roller-skate variant |

Replay a training checkpoint in the GPU simulator with `cd simulation/_external/xgoduck_rl && uv run play Mjlab-Velocity-Flat-XgoDuck`.

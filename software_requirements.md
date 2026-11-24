# Software Requirements

This page lists the software you need to simulate the [XGO Duck](https://github.com/LuwuDynamics/xgoduck_hardware). It is about simulation only. The software that runs on the robot itself is in [xgoduck_runtime_arduino](https://github.com/LuwuDynamics/xgoduck_runtime_arduino).

## Overview

| Goal | OS | GPU | Software |
|---|---|---|---|
| Watch pretrained policies (sim2sim) | Windows, Linux, macOS | not needed | Python 3.12+, MuJoCo, ONNX Runtime |
| Train new policies (RL) | Linux or Windows + WSL2 | NVIDIA, RTX 20xx or newer | git, uv, xgoduck_rl (mjlab, MuJoCo Warp, PyTorch, rsl_rl) |

## 1. Sim2sim (MuJoCo, CPU)

| Package | Version | Purpose |
|---|---|---|
| Python | 3.12 (3.13 and 3.14 also work) | runtime |
| [`mujoco`](https://pypi.org/project/mujoco/) | 4.0.1 | physics engine + 3D viewer (`mujoco.viewer`) |
| [`onnxruntime`](https://pypi.org/project/onnxruntime/) | 1.32.0 | runs the policy networks (`.onnx`) |
| [`numpy`](https://pypi.org/project/numpy/) | 2.5.5 | math |

These versions are pinned in [`simulation/common/requirements.txt`](simulation/common/requirements.txt). All packages ship prebuilt wheels for Windows x64, Linux x86_64/aarch64 and macOS arm64.

The setup scripts install everything:

* Windows: `simulation\windows\setup.ps1`
* Linux: `simulation/linux/setup.sh`

## 2. RL training (GPU)

| Component | Version | Notes |
|---|---|---|
| OS | Ubuntu 22.04 / 24.04, or Windows 11 + WSL2 | mjlab officially supports Linux only |
| NVIDIA GPU | Turing (RTX 20xx) or newer | more VRAM means more parallel environments (default 4096) |
| NVIDIA driver | current (R570+ recommended) | under WSL2: only the Windows driver |
| git, [uv](https://docs.astral.sh/uv/) | current | uv installs Python 3.12 and all packages from `uv.lock` |
| [xgoduck_rl](https://github.com/LuwuDynamics/xgoduck_rl) | commit `a4c78aa` (2026-11-09) | pins mjlab 1.3.0, torch 2.9.1, onnxruntime ≥ 1.24.4 and vendors the [BAM](https://github.com/Rhoban/bam) servo model |

Setup: `simulation/linux/train_setup.sh`. Details are in [`simulation/linux/README.md`](simulation/linux/README.md) and [`simulation/wsl2/README.md`](simulation/wsl2/README.md).

## 3. Optional tools

| Tool | When you need it |
|---|---|
| TensorBoard (`uv run tensorboard --logdir logs`) | watch training curves |
| [Bambu Studio](https://bambulab.com/download/studio) / any slicer | print the parts from `xgoduck_hardware` |
| [onshape-to-robot](https://onshape-to-robot.readthedocs.io/) | only if you redesign the robot in Onshape and want a new URDF/MJCF |

## Simulators considered but not used

| Simulator | Why not |
|---|---|
| Isaac Sim / Isaac Lab | No XGO Duck assets exist, and the hardware requirements are very high (Isaac Sim: RTX 4080 / 16 GB VRAM). The URDF could be imported if needed. |
| Gazebo + ROS 2 | No model exists, the Windows build is experimental only, and it is not suited for RL locomotion. |
| PyBullet | Unmaintained since 2025 and has no wheels for Windows or Python 3.12+. |
| MuJoCo Playground / MJX (JAX) | The JAX GPU build is Linux only. The XGO Duck stack uses mjlab instead. |
| Genesis, Webots | Run on Windows, but nobody has ported the XGO Duck to them yet. |

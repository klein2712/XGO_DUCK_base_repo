# Windows 11 – Sim2sim (MuJoCo + pretrained policies)

Runs natively on Windows. No GPU and no WSL needed.

## Requirements

* Windows 10/11 x64
* Python **3.12** (3.13 and 3.14 also work), from <https://www.python.org/downloads/windows/>. The `py` launcher must be installed, which is the installer's default.
* Internet access for the first setup
* Git is **not** needed

## 1. Setup (once)

Open PowerShell in the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File simulation\windows\setup.ps1
```

This does three things:

1. Creates `.venv\` in the repo root.
2. Installs `mujoco`, `onnxruntime` and `numpy` from [`../common/requirements.txt`](../common/requirements.txt).
3. Downloads the robot model and the policies into `simulation\_external\`.

## 2. Run

```powershell
# Walking policy with the 3D viewer
powershell -ExecutionPolicy Bypass -File simulation\windows\run_walk.ps1

# Start already walking forward at 0.15 m/s
powershell -ExecutionPolicy Bypass -File simulation\windows\run_walk.ps1 --vx 0.15

# Get-up policy: the duck starts lying on its belly
powershell -ExecutionPolicy Bypass -File simulation\windows\run_walk.ps1 --policy getup

# Only look at the model (no policy; joints can be moved in the right-hand "Control" panel)
powershell -ExecutionPolicy Bypass -File simulation\windows\run_walk.ps1 --view-only

# Quick check without a window: walk 10 s and print a report
powershell -ExecutionPolicy Bypass -File simulation\windows\run_walk.ps1 --vx 0.15 --headless --duration 10
```

**Steering:** click into the **MuJoCo window** and use these keys. The current command is shown in the top-left corner.

| Key | Action |
|---|---|
| ↑ / ↓ | faster forward / backward |
| ← / → | turn left / right |
| Home / End (German keyboard: Pos1 / Ende) | side step left / right |
| Space | stop |
| Enter | push the robot |
| Backspace | reset |
| close the window | quit |

Do not use letter or digit keys in the MuJoCo window: MuJoCo uses them to toggle render options. For example, digits hide geometry groups and T makes the robot transparent. If the view looks strange, press Backspace to reset the robot or restart the script. Tab shows the MuJoCo side panels.

All options: `run_walk.ps1 --help`.

## Optional: native GPU training on Windows (experimental)

The official training stack (mjlab / MuJoCo Warp) is documented for Linux only, so on Windows use [`../wsl2/`](../wsl2/).

Luwu documents a native Windows setup for its other robots in [luwu_mjlab](https://github.com/LuwuDynamics/luwu_mjlab), using conda, a CUDA 13 toolkit and PyTorch cu130. Adapting that to `xgoduck_rl` is possible but not tested here. `xgoduck_rl` pins `torch==2.9.1` and resolves the CPU build on Windows by default.

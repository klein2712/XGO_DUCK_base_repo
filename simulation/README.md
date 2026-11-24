# XGO Duck – Simulation

There are two ways to simulate the XGO Duck. Pick a folder for your OS and use case:

| Use case | Windows 11 | Linux (Ubuntu 22.04/24.04) | macOS |
|---|---|---|---|
| **A. Sim2sim:** watch the pretrained policies (walk, get-up, …) in MuJoCo, steer with the keyboard. CPU only. | ✅ [`windows/`](windows/) | ✅ [`linux/`](linux/) | ✅ same as Linux, start with `mjpython` |
| **B. RL training:** train new policies with `xgoduck_rl` (mjlab, MuJoCo Warp, NVIDIA GPU) | ✅ via [`wsl2/`](wsl2/) (recommended) · ⚠️ native is experimental | ✅ [`linux/`](linux/) | ❌ (no CUDA) |

```
simulation/
├── common/                 shared, OS-independent code
│   ├── fetch_assets.py     downloads robot model + pretrained ONNX policies -> _external/
│   ├── xgoduck_sim2sim.py  MuJoCo + ONNX Runtime player (viewer or headless)
│   └── requirements.txt    mujoco, onnxruntime, numpy (pinned)
├── windows/                PowerShell setup + run scripts (sim2sim)
├── linux/                  bash setup + run scripts (sim2sim) and GPU training scripts
├── wsl2/                   guide: GPU training on a Windows PC through WSL2
└── _external/              downloaded upstream files (git-ignored, created by fetch_assets.py)
```

## Where the model and policies come from

No new robot model was built here. Everything comes from the official Luwu Dynamics repos:

| What | Source | License |
|---|---|---|
| MuJoCo model (MJCF, STL meshes, URDF, HLS1910 servo parameters) | [LuwuDynamics/xgoduck_rl](https://github.com/LuwuDynamics/xgoduck_rl) `src/mjlab_microduck/robot/xgoduck/` | Apache-2.0 |
| Training environments (velocity, stand-up, sit-stand, ground pick, ball kick, roulade, …) | [LuwuDynamics/xgoduck_rl](https://github.com/LuwuDynamics/xgoduck_rl) | Apache-2.0 |
| Pretrained ONNX policies (the ones running on the real robot) | [LuwuDynamics/xgoduck_runtime_arduino](https://github.com/LuwuDynamics/xgoduck_runtime_arduino) `python/*.onnx` | no license file yet → downloaded locally, not redistributed |
| Printable parts, PCB | [LuwuDynamics/xgoduck_hardware](https://github.com/LuwuDynamics/xgoduck_hardware) | terms pending (see its LICENSING.md) |

The upstream lineage is Disney BDX → Open Duck Mini → Pollen Robotics [Microduck](https://github.com/pollen-robotics/microduck) / [microduck_rl](https://github.com/pollen-robotics/microduck_rl) → XGO Duck.

> The hardware repo itself contains **no** simulation model. Its STL files are print parts laid flat on the build plate and are not usable as simulation links. Use the model from `xgoduck_rl` instead.

## Policy interface (for reference)

| | |
|---|---|
| Control rate | 50 Hz (MuJoCo timestep 0.005 s, decimation 4) |
| Observation (61) | gyro (3) · projected gravity (3) · joint pos − default (14) · joint vel (14) · last action (14) · twist cmd vx, vy, wz (3) · head pose cmd (4) · body pose cmd (6) |
| Action (14) | joint target = `default_joint_pos + action` (radians) |
| Joint order | left hip_yaw, hip_roll, hip_pitch, knee, ankle · neck_pitch, head_pitch, head_yaw, head_roll · right hip_yaw … ankle |

The 15th servo, the mouth, is not part of the policy. `default_joint_pos` and the joint order are read from the ONNX metadata.

## Known limitations of the sim2sim player

* Plain MuJoCo uses the MJCF's simple position servo (kp 0.84, ±1.04 Nm). Training uses the more accurate BAM actuator model with friction, delay and backlash, so the behaviour is close to training but not identical.
* The `sitstand`, `pick`, `ballkick` and `roulade` policies need extra commands or triggers. The player only provides velocity commands, so `walk` and `getup` are the ones that work out of the box.

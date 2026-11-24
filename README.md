# XGO Duck – Simulation

Simulation setup for the **XGO Duck** by Luwu Dynamics. The XGO Duck is a 3D-printed biped with 15 Feetech HLS1910 bus servos, an Arduino UNO Q and a QMI8658 IMU; hardware files are at [LuwuDynamics/xgoduck_hardware](https://github.com/LuwuDynamics/xgoduck_hardware).

This repo collects in one place:

* **Which software you need:** [software_requirements.md](software_requirements.md)
* **A ready-to-run simulation:** [simulation/](simulation/). It plays the pretrained walk and get-up policies in MuJoCo on Windows, Linux or macOS, and covers GPU training of new policies on Linux or WSL2.

## Quick start (Windows)

```powershell
powershell -ExecutionPolicy Bypass -File simulation\windows\setup.ps1
powershell -ExecutionPolicy Bypass -File simulation\windows\run_walk.ps1
```

On Linux: `bash simulation/linux/setup.sh && bash simulation/linux/run_walk.sh`.

## Credits

* Robot model, training environments and policies: [Luwu Dynamics](https://github.com/LuwuDynamics) ([xgoduck_rl](https://github.com/LuwuDynamics/xgoduck_rl), [xgoduck_runtime_arduino](https://github.com/LuwuDynamics/xgoduck_runtime_arduino))
* Based on [Microduck](https://github.com/pollen-robotics/microduck) / [microduck_rl](https://github.com/pollen-robotics/microduck_rl) by Pollen Robotics
* [mjlab](https://github.com/mujocolab/mjlab), [MuJoCo](https://github.com/google-deepmind/mujoco), [BAM](https://github.com/Rhoban/bam)

Upstream files are downloaded at setup time and are not part of this repository. Their licenses are listed in [simulation/README.md](simulation/README.md#where-the-model-and-policies-come-from).

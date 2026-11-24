# Windows + WSL2 – GPU training

Use this to train XGO Duck policies on a Windows PC with an NVIDIA GPU. WSL2 runs a real Ubuntu, and CUDA is passed through from the Windows driver. The Linux scripts in [`../linux/`](../linux/) then work unchanged.

For just *watching* the pretrained policies you do not need WSL2. Use [`../windows/`](../windows/) instead.

## 1. Install WSL2 + Ubuntu (PowerShell as admin, once)

```powershell
wsl --install -d Ubuntu-24.04
```

Reboot if asked, then open "Ubuntu 24.04" from the Start menu and create a user.

## 2. GPU driver

* Install the normal **Windows** NVIDIA driver (Game Ready or Studio). It provides CUDA inside WSL2.
* Do **not** install a Linux NVIDIA driver inside WSL.
* Check inside Ubuntu: `nvidia-smi` must list your GPU.

## 3. Tools inside Ubuntu

```bash
sudo apt update && sudo apt install -y git python3.12 python3.12-venv build-essential
curl -LsSf https://astral.sh/uv/install.sh | sh && source ~/.bashrc
```

## 4. Clone this repo into the Linux file system

Clone it into your Linux home, **not** into `/mnt/c` or `/mnt/d`. File access across the Windows/Linux boundary is very slow, and a `.venv` created by Windows would clash with the Linux one.

```bash
cd ~ && git clone <URL of this repo> && cd <repo>
```

## 5. Train

```bash
bash simulation/linux/train_setup.sh
bash simulation/linux/train.sh Mjlab-Velocity-Flat-XgoDuck 4096
```

## 6. Watch the result

* **In WSL:** `bash simulation/linux/setup.sh && bash simulation/linux/run_walk.sh --policy <path>.onnx`. WSLg shows the MuJoCo window directly on the Windows desktop.
* **Or on Windows:** copy the `.onnx` to Windows (Explorer: `\\wsl$\Ubuntu-24.04\home\<user>\...`) and run `simulation\windows\run_walk.ps1 --policy C:\path\to\file.onnx`.

## Alternative: Docker

mjlab publishes a CUDA image (`ghcr.io/mujocolab/mjlab`). It runs with Docker Desktop and its WSL2 backend: `docker run --rm --gpus all ghcr.io/mujocolab/mjlab uv run demo`. This repo's scripts use the plain `uv` setup above.

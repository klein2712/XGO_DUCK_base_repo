#!/usr/bin/env python3
"""XGO Duck sim2sim: run a pretrained ONNX policy in plain MuJoCo (CPU only).

Works on Windows, Linux and macOS (on macOS start it with ``mjpython``).
No GPU, no mjlab, no training stack required.

The observation / action interface mirrors the training setup in
LuwuDynamics/xgoduck_rl and the robot runtime in
LuwuDynamics/xgoduck_runtime_arduino (``python/rl_core.py``):

    obs (61) = base_ang_vel(3) | projected_gravity(3) | joint_pos - default(14)
               | joint_vel(14) | last_action(14) | twist cmd(3)
               | head_pose cmd(4) | body_pose cmd(6)
    action (14) -> joint target = default_joint_pos + action_scale * action

    control: 50 Hz (sim timestep 0.005 s, decimation 4) - same as training.

Keyboard control - click into the MuJoCo window first. Only keys that the
viewer does not use itself are bound (letters and digits toggle MuJoCo
render options, so they are NOT used):

    Up / Down      forward / backward speed  (+-0.05 m/s, limit +-0.30)
    Left / Right   turn left / right         (+-0.25 rad/s, limit +-1.5)
    Home / End     side step left / right    (+-0.05 m/s, limit +-0.20)
                   (German keyboard: Pos1 / Ende)
    Space          stop (all commands to zero)
    Enter          random push on the trunk
    Backspace      reset robot
    close window   quit

The same keys also work in the terminal window; there A / D, P, R and Q
work too.

Run ``fetch_assets.py`` first to download the model and the policies.
"""
from __future__ import annotations

import argparse
import math
import os
import queue
import sys
import threading
import time
from pathlib import Path

import numpy as np

try:
    import mujoco
    import onnxruntime as ort
except ImportError as exc:  # pragma: no cover - friendly message only
    sys.exit(f"Missing dependency ({exc}). Install with: pip install -r simulation/common/requirements.txt")

SIM_DIR = Path(__file__).resolve().parents[1]
EXTERNAL_DIR = SIM_DIR / "_external"
MODEL_DIR = EXTERNAL_DIR / "xgoduck_model"
POLICY_DIR = EXTERNAL_DIR / "policies"

SIM_DT = 0.005
DECIMATION = 4
CONTROL_DT = SIM_DT * DECIMATION  # 0.02 s -> 50 Hz

OBS_DIM = 61
ACT_DIM = 14

# Command limits used by the upstream sim2sim tool for the walking robot.
VX_LIM, VY_LIM, WZ_LIM = 0.30, 0.20, 1.50
VX_STEP, VY_STEP, WZ_STEP = 0.05, 0.05, 0.25

# Action low-pass filter used on the real robot (rl_core.py). Optional here.
ACTION_ALPHA_LEG = 0.35
ACTION_ALPHA_HEAD = 0.45

# Fallback joint order / default pose (radians) if the ONNX file has no metadata.
JOINT_NAMES = [
    "left_hip_yaw", "left_hip_roll", "left_hip_pitch", "left_knee", "left_ankle",
    "neck_pitch", "head_pitch", "head_yaw", "head_roll",
    "right_hip_yaw", "right_hip_roll", "right_hip_pitch", "right_knee", "right_ankle",
]
DEFAULT_POSE = [
    0.0, -0.087266, -0.383972, -0.00494, 0.383972,
    0.349066, 0.349066, 0.0, 0.0,
    0.0, 0.087266, 0.383972, 0.00494, -0.383972,
]

SCENES = {
    "walk": "scene_walk.xml",          # robot_walk.xml: foot collisions only (used for walking)
    "full": "scene.xml",               # robot_allcollisions.xml: whole body collides (get-up, sit)
}


# --------------------------------------------------------------------------- keyboard
class TerminalKeys:
    """Non-blocking single-key reader for Windows (msvcrt) and POSIX (termios)."""

    _WIN_ARROWS = {"H": "up", "P": "down", "K": "left", "M": "right", "G": "home", "O": "end"}
    _ANSI_ARROWS = {"A": "up", "B": "down", "C": "right", "D": "left", "H": "home", "F": "end"}

    def __init__(self, q: "queue.Queue[str] | None" = None) -> None:
        self.q: queue.Queue[str] = q if q is not None else queue.Queue()
        self.enabled = sys.stdin is not None and sys.stdin.isatty()
        self._stop = threading.Event()
        self._old = None

    def __enter__(self) -> "TerminalKeys":
        if not self.enabled:
            print("stdin is not a terminal - keyboard control disabled")
            return self
        if os.name == "nt":
            threading.Thread(target=self._win_loop, daemon=True).start()
        else:
            import termios
            import tty
            fd = sys.stdin.fileno()
            self._old = termios.tcgetattr(fd)
            tty.setcbreak(fd)
            threading.Thread(target=self._posix_loop, daemon=True).start()
        return self

    def __exit__(self, *exc) -> None:
        self._stop.set()
        if self._old is not None:
            import termios
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, self._old)

    def _win_loop(self) -> None:
        import msvcrt
        while not self._stop.is_set():
            if not msvcrt.kbhit():
                time.sleep(0.01)
                continue
            ch = msvcrt.getwch()
            if ch in ("\x00", "\xe0"):  # special key prefix
                name = self._WIN_ARROWS.get(msvcrt.getwch())
                if name:
                    self.q.put(name)
            elif ch == "\r":
                self.q.put("enter")
            elif ch == "\x08":
                self.q.put("backspace")
            else:
                self.q.put(ch.lower())

    def _posix_loop(self) -> None:
        import select
        fd = sys.stdin.fileno()

        def read1(timeout: float):
            r, _, _ = select.select([fd], [], [], timeout)
            return os.read(fd, 1).decode(errors="ignore") if r else None

        while not self._stop.is_set():
            ch = read1(0.1)
            if not ch:
                continue
            if ch == "\x1b":
                if read1(0.05) == "[":
                    name = self._ANSI_ARROWS.get(read1(0.05) or "")
                    if name:
                        self.q.put(name)
                continue
            if ch in ("\r", "\n"):
                self.q.put("enter")
            elif ch in ("\x7f", "\x08"):
                self.q.put("backspace")
            else:
                self.q.put(ch.lower())

    def keys(self) -> list[str]:
        out = []
        while True:
            try:
                out.append(self.q.get_nowait())
            except queue.Empty:
                return out


# --------------------------------------------------------------------------- policy
class OnnxPolicy:
    def __init__(self, path: Path) -> None:
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 1
        self.sess = ort.InferenceSession(str(path), sess_options=opts, providers=["CPUExecutionProvider"])
        inp, out = self.sess.get_inputs()[0], self.sess.get_outputs()[0]
        if inp.shape[-1] != OBS_DIM or out.shape[-1] != ACT_DIM:
            raise ValueError(f"{path.name}: expected obs {OBS_DIM} -> act {ACT_DIM}, got {inp.shape} -> {out.shape}")
        self.in_name, self.out_name = inp.name, out.name

        meta = self.sess.get_modelmeta().custom_metadata_map
        self.joint_names = meta["joint_names"].split(",") if "joint_names" in meta else JOINT_NAMES
        if "default_joint_pos" in meta:
            self.default_pose = np.array([float(v) for v in meta["default_joint_pos"].split(",")], dtype=np.float32)
        else:
            self.default_pose = np.array(DEFAULT_POSE, dtype=np.float32)
        self.action_scale = float(meta.get("action_scale", 1.0))
        self.meta = meta

    def __call__(self, obs: np.ndarray) -> np.ndarray:
        return self.sess.run([self.out_name], {self.in_name: obs.reshape(1, -1)})[0].reshape(ACT_DIM)


# --------------------------------------------------------------------------- simulation
def quat_rotate_inverse(q: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Rotate vector v by the inverse of quaternion q = [w, x, y, z]."""
    w, xyz = q[0], q[1:4]
    t = 2.0 * np.cross(xyz, v)
    return v - w * t + np.cross(xyz, t)


class DuckSim:
    def __init__(self, scene_xml: Path, policy: OnnxPolicy, action_filter: bool, start: str) -> None:
        self.model = mujoco.MjModel.from_xml_path(str(scene_xml))
        self.model.opt.timestep = SIM_DT
        self.data = mujoco.MjData(self.model)
        self.policy = policy
        self.action_filter = action_filter
        self.start = start

        m = self.model
        jid = [mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, n) for n in policy.joint_names]
        aid = [mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, n) for n in policy.joint_names]
        missing = [n for n, j, a in zip(policy.joint_names, jid, aid) if j < 0 or a < 0]
        if missing:
            raise ValueError(f"joints/actuators not found in model: {missing}")
        self.qpos_idx = np.array([m.jnt_qposadr[j] for j in jid])
        self.qvel_idx = np.array([m.jnt_dofadr[j] for j in jid])
        self.act_idx = np.array(aid)
        self.ctrl_lo = m.actuator_ctrlrange[self.act_idx, 0]
        self.ctrl_hi = m.actuator_ctrlrange[self.act_idx, 1]

        self.trunk_id = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "trunk_base")
        free_j = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_JOINT, "trunk_base_freejoint")
        self.free_qpos = m.jnt_qposadr[free_j]
        self.free_qvel = m.jnt_dofadr[free_j]
        gyro = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_SENSOR, "imu_ang_vel")
        self.gyro_adr = m.sensor_adr[gyro]
        self.stand_key = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_KEY, "STAND")

        self.cmd = np.zeros(3, dtype=np.float32)        # vx, vy, wz
        self.head_cmd = np.zeros(4, dtype=np.float32)
        self.body_cmd = np.zeros(6, dtype=np.float32)
        self.reset()

    def reset(self) -> None:
        m, d, p = self.model, self.data, self.policy
        if self.stand_key >= 0:
            mujoco.mj_resetDataKeyframe(m, d, self.stand_key)
        else:
            mujoco.mj_resetData(m, d)
            d.qpos[self.free_qpos:self.free_qpos + 7] = [0, 0, 0.14, 1, 0, 0, 0]
        d.qpos[self.qpos_idx] = p.default_pose
        d.ctrl[self.act_idx] = p.default_pose
        if self.start in ("front", "back"):
            # Lay the duck on its belly / back, slightly above the floor.
            ang = math.pi / 2 if self.start == "front" else -math.pi / 2
            d.qpos[self.free_qpos + 2] = 0.08
            d.qpos[self.free_qpos + 3:self.free_qpos + 7] = [math.cos(ang / 2), 0, math.sin(ang / 2), 0]
        mujoco.mj_forward(m, d)
        self.last_action = np.zeros(ACT_DIM, dtype=np.float32)
        self.filtered_action = np.zeros(ACT_DIM, dtype=np.float32)

    def observation(self) -> np.ndarray:
        d = self.data
        quat = d.xquat[self.trunk_id].astype(np.float32)
        obs = np.concatenate([
            d.sensordata[self.gyro_adr:self.gyro_adr + 3],
            quat_rotate_inverse(quat, np.array([0.0, 0.0, -1.0], dtype=np.float32)),
            d.qpos[self.qpos_idx] - self.policy.default_pose,
            d.qvel[self.qvel_idx],
            self.last_action,
            self.cmd,
            self.head_cmd,
            self.body_cmd,
        ]).astype(np.float32)
        assert obs.shape == (OBS_DIM,)
        return obs

    def control_step(self) -> None:
        action = self.policy(self.observation())
        self.last_action = action.astype(np.float32)
        if self.action_filter:
            for sl, a in ((slice(0, 5), ACTION_ALPHA_LEG), (slice(5, 9), ACTION_ALPHA_HEAD), (slice(9, 14), ACTION_ALPHA_LEG)):
                self.filtered_action[sl] = a * self.filtered_action[sl] + (1 - a) * action[sl]
            action = self.filtered_action
        target = self.policy.default_pose + self.policy.action_scale * action
        self.data.ctrl[self.act_idx] = np.clip(target, self.ctrl_lo, self.ctrl_hi)
        for _ in range(DECIMATION):
            mujoco.mj_step(self.model, self.data)

    def push(self, magnitude: float = 0.6) -> None:
        ang = np.random.uniform(0, 2 * math.pi)
        self.data.qvel[self.free_qvel:self.free_qvel + 2] += magnitude * np.array([math.cos(ang), math.sin(ang)])

    # --- status helpers
    def trunk_pos(self) -> np.ndarray:
        return self.data.qpos[self.free_qpos:self.free_qpos + 3].copy()

    def upright(self) -> float:
        """-z of projected gravity: 1 = perfectly upright, 0 = lying on its side."""
        quat = self.data.xquat[self.trunk_id]
        return float(-quat_rotate_inverse(quat, np.array([0.0, 0.0, -1.0]))[2])

    def handle_key(self, k: str) -> bool:
        """Apply one key press. Returns False when the user wants to quit."""
        c = self.cmd
        if k == "up":
            c[0] = min(c[0] + VX_STEP, VX_LIM)
        elif k == "down":
            c[0] = max(c[0] - VX_STEP, -VX_LIM)
        elif k == "left":
            c[2] = min(c[2] + WZ_STEP, WZ_LIM)
        elif k == "right":
            c[2] = max(c[2] - WZ_STEP, -WZ_LIM)
        elif k in ("a", "home"):
            c[1] = min(c[1] + VY_STEP, VY_LIM)
        elif k in ("d", "end"):
            c[1] = max(c[1] - VY_STEP, -VY_LIM)
        elif k in (" ", "0", "space"):
            c[:] = 0
        elif k in ("p", "enter"):
            self.push()
            print("push!")
        elif k in ("r", "backspace"):
            self.reset()
            print("reset")
        elif k == "q":
            return False
        else:
            return True
        print(f"cmd: vx={c[0]:+.2f} m/s  vy={c[1]:+.2f} m/s  wz={c[2]:+.2f} rad/s")
        return True


# --------------------------------------------------------------------------- runners
# GLFW key codes (mjui.h) that the passive MuJoCo viewer does not use itself.
VIEWER_KEYS = {
    265: "up", 264: "down", 263: "left", 262: "right",
    268: "home", 269: "end", 32: "space", 257: "enter", 259: "backspace",
}

HELP_LEFT = "Up / Down\nLeft / Right\nHome / End\nSpace\nEnter\nBackspace\n\nCommand"


def run_viewer(sim: DuckSim) -> None:
    import mujoco.viewer

    print("Keyboard control" + __doc__.split("Keyboard control", 1)[1].split("Run ``fetch", 1)[0])
    key_q: queue.Queue[str] = queue.Queue()

    def on_key(keycode: int) -> None:  # called from the viewer thread
        name = VIEWER_KEYS.get(keycode)
        if name:
            key_q.put(name)

    with TerminalKeys(key_q) as keys, mujoco.viewer.launch_passive(
        sim.model, sim.data, key_callback=on_key, show_left_ui=False, show_right_ui=False
    ) as viewer:
        viewer.cam.distance = 0.8
        viewer.cam.elevation = -15
        running, step = True, 0
        while viewer.is_running() and running:
            t0 = time.perf_counter()
            for k in keys.keys():
                running = sim.handle_key(k) and running
            sim.control_step()
            viewer.cam.lookat[:] = sim.trunk_pos()
            if step % 10 == 0:  # refresh the on-screen help 5x per second
                c = sim.cmd
                viewer.set_texts((
                    mujoco.mjtFontScale.mjFONTSCALE_150, mujoco.mjtGridPos.mjGRID_TOPLEFT, HELP_LEFT,
                    "forward / back\nturn\nside step\nstop\npush\nreset\n\n"
                    f"vx {c[0]:+.2f}  vy {c[1]:+.2f}  wz {c[2]:+.2f}",
                ))
            step += 1
            viewer.sync()
            dt = CONTROL_DT - (time.perf_counter() - t0)
            if dt > 0:
                time.sleep(dt)


def run_headless(sim: DuckSim, duration: float) -> int:
    """Run without a window and print a short report. Exit code 0 = robot stayed upright."""
    steps = int(duration / CONTROL_DT)
    start = sim.trunk_pos()
    min_up, t_start = 1.0, time.perf_counter()
    for _ in range(steps):
        sim.control_step()
        min_up = min(min_up, sim.upright())
    wall = time.perf_counter() - t_start
    end = sim.trunk_pos()
    dist = end[:2] - start[:2]
    fell = sim.upright() < 0.5
    print(f"simulated {duration:.1f}s in {wall:.1f}s wall time ({duration / max(wall, 1e-9):.1f}x real time)")
    print(f"command        vx={sim.cmd[0]:+.2f}  vy={sim.cmd[1]:+.2f}  wz={sim.cmd[2]:+.2f}")
    print(f"displacement   dx={dist[0]:+.3f} m  dy={dist[1]:+.3f} m  (avg vx {dist[0] / duration:+.3f} m/s)")
    print(f"trunk height   {end[2]:.3f} m   uprightness end={sim.upright():.2f} min={min_up:.2f}")
    print("RESULT:", "FELL OVER" if fell else "upright")
    return 1 if fell else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Run an XGO Duck ONNX policy in MuJoCo.",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--policy", default="walk",
                    help="policy name in _external/policies (walk, getup, sitstand, ...) or path to an .onnx file")
    ap.add_argument("--scene", choices=SCENES, default=None,
                    help="walk = foot collisions only, full = whole-body collisions (default: full for getup, else walk)")
    ap.add_argument("--start", choices=["stand", "front", "back"], default=None,
                    help="initial pose (default: front for getup, else stand)")
    ap.add_argument("--vx", type=float, default=0.0, help="initial forward speed command [m/s]")
    ap.add_argument("--vy", type=float, default=0.0, help="initial sideways speed command [m/s]")
    ap.add_argument("--wz", type=float, default=0.0, help="initial yaw rate command [rad/s]")
    ap.add_argument("--action-filter", action="store_true",
                    help="apply the low-pass action filter the real robot runtime uses")
    ap.add_argument("--headless", action="store_true", help="no window; simulate --duration seconds and print a report")
    ap.add_argument("--duration", type=float, default=10.0, help="headless duration in seconds")
    ap.add_argument("--model-dir", type=Path, default=MODEL_DIR, help="folder with scene_walk.xml / scene.xml")
    ap.add_argument("--view-only", action="store_true", help="just open the model in the viewer, no policy")
    args = ap.parse_args()

    if not (args.model_dir / "scene.xml").exists():
        sys.exit(f"Model not found in {args.model_dir}. Run: python simulation/common/fetch_assets.py")

    if args.view_only:
        # No policy: start in the STAND keyframe with the servos holding that pose.
        # Nothing balances the robot, so a push (Ctrl + right-drag) will still topple it.
        import mujoco.viewer
        model = mujoco.MjModel.from_xml_path(str(args.model_dir / SCENES[args.scene or "walk"]))
        model.opt.timestep = SIM_DT
        data = mujoco.MjData(model)
        key = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "STAND")
        if key >= 0:
            mujoco.mj_resetDataKeyframe(model, data, key)
        mujoco.viewer.launch(model, data)
        return 0

    p = Path(args.policy)
    policy_path = p if p.suffix == ".onnx" else POLICY_DIR / f"xgoduck_{args.policy}.onnx"
    if not policy_path.exists():
        sys.exit(f"Policy not found: {policy_path}. Run: python simulation/common/fetch_assets.py")

    is_getup = "getup" in policy_path.name
    scene = args.scene or ("full" if is_getup else "walk")
    start = args.start or ("front" if is_getup else "stand")

    policy = OnnxPolicy(policy_path)
    sim = DuckSim(args.model_dir / SCENES[scene], policy, args.action_filter, start)
    sim.cmd[:] = [np.clip(args.vx, -VX_LIM, VX_LIM), np.clip(args.vy, -VY_LIM, VY_LIM), np.clip(args.wz, -WZ_LIM, WZ_LIM)]

    print(f"policy : {policy_path.name}  (action_scale={policy.action_scale})")
    print(f"scene  : {SCENES[scene]}   start: {start}   control: {1 / CONTROL_DT:.0f} Hz")

    if args.headless:
        return run_headless(sim, args.duration)
    run_viewer(sim)
    return 0


if __name__ == "__main__":
    sys.exit(main())

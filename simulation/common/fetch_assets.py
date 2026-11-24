#!/usr/bin/env python3
"""Download the XGO Duck simulation model and pretrained ONNX policies.

Only the Python standard library is used, so this runs before any `pip install`.

What gets downloaded (into ``simulation/_external/``):

* ``xgoduck_model/``  - MuJoCo model of the XGO Duck (MJCF + STL meshes + URDF)
  taken from LuwuDynamics/xgoduck_rl, ``src/mjlab_microduck/robot/xgoduck/``.
  License: Apache-2.0 (copied next to the files as LICENSE).
* ``policies/``       - pretrained ONNX policies shipped with the robot firmware
  (LuwuDynamics/xgoduck_runtime_arduino, ``python/*.onnx``). That repo has no
  license file yet, so the files are downloaded for local use only and are NOT
  committed to this repository (``_external/`` is git-ignored).

Both sources are pinned to the commits this repo was tested against. Pass
``--latest`` to use the default branches instead.
"""
from __future__ import annotations

import argparse
import io
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

SIM_DIR = Path(__file__).resolve().parents[1]
EXTERNAL_DIR = SIM_DIR / "_external"

RL_REPO = "LuwuDynamics/xgoduck_rl"
RL_REF = "a4c78aacd5eaa724cf246fe12d24bfe1e837fa50"  # 2026-11-09
RL_MODEL_PREFIX = "src/mjlab_microduck/robot/xgoduck/"

RUNTIME_REPO = "LuwuDynamics/xgoduck_runtime_arduino"
RUNTIME_REF = "6168aedfdba33c8fe57045f54bc46836c44a572c"  # 2026-11-20
POLICIES = [
    "xgoduck_walk.onnx",
    "xgoduck_getup.onnx",
    "xgoduck_sitstand.onnx",
    "xgoduck_pick.onnx",
    "xgoduck_ballkick_left.onnx",
    "xgoduck_ballkick_right.onnx",
    "xgoduck_roulade.onnx",
]

USER_AGENT = "xgoduck-sim-fetch/1.0"


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def fetch_model(ref: str, force: bool) -> None:
    target = EXTERNAL_DIR / "xgoduck_model"
    if target.exists() and not force:
        print(f"[skip] model already present: {target}")
        return
    if target.exists():
        shutil.rmtree(target)

    url = f"https://codeload.github.com/{RL_REPO}/tar.gz/{ref}"
    print(f"[get ] {url}")
    blob = _get(url)

    target.mkdir(parents=True)
    n = 0
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        for member in tar.getmembers():
            # Strip the "<repo>-<sha>/" top-level folder GitHub adds.
            parts = member.name.split("/", 1)
            if len(parts) != 2:
                continue
            rel = parts[1]
            if rel == "LICENSE" and member.isfile():
                dest_rel = "LICENSE"
            elif rel.startswith(RL_MODEL_PREFIX) and member.isfile():
                dest_rel = rel[len(RL_MODEL_PREFIX):]
            else:
                continue
            dest = (target / dest_rel).resolve()
            if target.resolve() not in dest.parents:  # path traversal guard
                raise RuntimeError(f"unsafe path in archive: {member.name}")
            dest.parent.mkdir(parents=True, exist_ok=True)
            src = tar.extractfile(member)
            assert src is not None
            dest.write_bytes(src.read())
            n += 1
    (target / "SOURCE.txt").write_text(
        f"https://github.com/{RL_REPO}/tree/{ref}/{RL_MODEL_PREFIX}\nLicense: Apache-2.0\n",
        encoding="utf-8",
    )
    print(f"[ ok ] {n} files -> {target}")


def fetch_policies(ref: str, force: bool) -> None:
    target = EXTERNAL_DIR / "policies"
    target.mkdir(parents=True, exist_ok=True)
    for name in POLICIES:
        dest = target / name
        if dest.exists() and not force:
            print(f"[skip] {name}")
            continue
        url = f"https://raw.githubusercontent.com/{RUNTIME_REPO}/{ref}/python/{name}"
        print(f"[get ] {url}")
        dest.write_bytes(_get(url))
    (target / "SOURCE.txt").write_text(
        f"https://github.com/{RUNTIME_REPO}/tree/{ref}/python\n"
        "No license file upstream yet - local use only, do not redistribute.\n",
        encoding="utf-8",
    )
    print(f"[ ok ] policies -> {target}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--latest", action="store_true", help="use upstream default branches instead of pinned commits")
    ap.add_argument("--force", action="store_true", help="re-download even if files exist")
    args = ap.parse_args()

    rl_ref = "main" if args.latest else RL_REF
    rt_ref = "master" if args.latest else RUNTIME_REF
    try:
        fetch_model(rl_ref, args.force)
        fetch_policies(rt_ref, args.force)
    except Exception as exc:  # network errors etc.
        print(f"[fail] {exc}", file=sys.stderr)
        return 1
    print("\nDone. Next: python simulation/common/xgoduck_sim2sim.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())

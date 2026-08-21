"""Contention: does foreground latency survive a machine that is already working?

Every interactive number in this folder is single-consumer, and the product
never runs that way: the user scrubs while the pipeline sweeps the original,
flow burns cores, and a proxy encodes in the background. v2 measured a
pipeline made 1.88x faster making playback *worse* and left it open; the
explorer's parallel sweeps measured symmetric aggregate throughput, which is
not the product question. The product question is asymmetric: the p95 of a
*drag* while something else owns the machine — and the stall, not the mean,
is the finding, which is why the harness keeps every sample.

Foregrounds are the stack's interactive activities, each on its file:
random access on the proxy, the lossy-intra cut, the Ut Video cut (the
no-NVDEC-escape cell: lossless speed measured solo may invert when decode
has to share cores), and exact fetches from the uncut original by both
routes. Backgrounds run as separate *processes* (honest about cores and
allocators): nothing, a software sweep of the original, an NVDEC sweep,
DIS flow workers, and everything at once — sweep + flow + a proxy encode —
which is the worst case the store design has to stay under. The prediction
on trial is NVDEC immunity: hardware decode should not care about CPU load,
and software decoders should collapse (the finding of that name).

Same-seed targets per foreground keep cells comparable across backgrounds.
"""

from __future__ import annotations

import random
import subprocess
import sys
import time
from fractions import Fraction
from pathlib import Path

import av
import numpy as np

from harness import FOOTAGE, Run, report, time_case

BIG = FOOTAGE / "GX010047c2_02_17_26.MP4"
DERIVED = FOOTAGE / "derived"
PROXY = DERIVED / "proxy-1328-intra.mp4"
CUT = DERIVED / "cut-crf18-intra.mp4"
UTV = DERIVED / "cut-utvideo.mkv"
CROP_W, CROP_H, CROP_X, CROP_Y = 1024, 1024, 2144, 982  # exp05's region
FETCHES = 32
FLOW_WORKERS = 4
LOAD_WARM_S = 2.0


def _pts_helpers(stream):
    tb, rate = stream.time_base, stream.average_rate
    base = stream.start_time or 0
    step = Fraction(1, 1) / (rate * tb)
    return (lambda i: base + int(step * i)), step


def _take_luma(frame, crop: bool):
    plane = frame.planes[0]
    arr = np.frombuffer(plane, dtype=np.uint8)
    arr = arr[: frame.height * plane.line_size]
    arr = arr.reshape(frame.height, plane.line_size)[:, : frame.width]
    if crop:
        arr = arr[CROP_Y : CROP_Y + CROP_H, CROP_X : CROP_X + CROP_W]
    return np.ascontiguousarray(arr)


# ── background loads (each runs in its own process until killed) ─────────────

def _load_sweep(hwaccel: str | None) -> None:
    """Decode the original sequentially, forever — the pipeline's shape."""
    opts = {}
    if hwaccel:
        from av.codec.hwaccel import HWAccel

        opts["hwaccel"] = HWAccel(device_type=hwaccel,
                                  allow_software_fallback=False)
    while True:
        with av.open(str(BIG), **opts) as container:
            stream = container.streams.video[0]
            stream.thread_type = "AUTO"
            for frame in container.decode(stream):
                frame.planes[0]  # touch the data, keep nothing


def _load_flow() -> None:
    """DIS-ultrafast over the cut, forever — the analysis chain's cost."""
    import cv2

    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_ULTRAFAST)
    prev = None
    while True:
        with av.open(str(CUT)) as container:
            stream = container.streams.video[0]
            stream.thread_type = "AUTO"
            for frame in container.decode(stream):
                arr = _take_luma(frame, crop=False)
                if prev is not None:
                    dis.calc(prev, arr, None)
                prev = arr


def _spawn(kind: str) -> subprocess.Popen:
    return subprocess.Popen(
        [sys.executable, __file__, "--load", kind],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def _spawn_encode() -> subprocess.Popen:
    """A proxy encode of the original to the null muxer — generation's load
    without touching video-tests/derived (and -copyts costs nothing here)."""
    return subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-nostdin", "-v", "error",
         "-stream_loop", "-1", "-i", str(BIG), "-vf", "scale=1328:-2",
         "-c:v", "libx264", "-crf", "23", "-preset", "veryfast", "-g", "1",
         "-an", "-f", "null", "-"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


BACKGROUNDS = {
    "none": [],
    "sw-sweep": ["sw-sweep"],
    "hw-sweep": ["hw-sweep"],
    "flow": ["flow"] * FLOW_WORKERS,
    "everything": ["sw-sweep"] + ["flow"] * FLOW_WORKERS + ["encode"],
}


# ── foregrounds (each: open, then FETCHES random exact fetches) ──────────────

def random_access(path: Path, base_idx: int, span: int, crop: bool,
                  hwaccel: str | None = None):
    rng = random.Random(7)  # same targets for every background
    targets = [base_idx + rng.randrange(span) for _ in range(FETCHES)]

    def work():
        opts = {}
        if hwaccel:
            from av.codec.hwaccel import HWAccel

            opts["hwaccel"] = HWAccel(device_type=hwaccel,
                                      allow_software_fallback=False)
        with av.open(str(path), **opts) as container:
            stream = container.streams.video[0]
            stream.thread_type = "AUTO"
            pts_of, step = _pts_helpers(stream)
            half = step / 2
            yield "open"
            for t in targets:
                target = pts_of(t)
                container.seek(target, stream=stream)
                for frame in container.decode(stream):
                    if frame.pts is not None and frame.pts + half >= target:
                        _take_luma(frame, crop)
                        break
                yield True

    return work


def main() -> None:
    run = Run(
        experiment="07-contention",
        question=(
            "What happens to the p50/p95 of interactive random access — per "
            "file, per route — while background processes sweep, compute "
            "flow, and encode?"
        ),
    )
    for p in (BIG, PROXY, CUT, UTV):
        if not p.exists():
            print(f"missing {p} — run 05-the-cut.py / recreate the proxy first")
            return
    run.add_footage(BIG, PROXY, CUT, UTV)

    with av.open(str(BIG)) as c:
        rate = c.streams.video[0].average_rate
    base_idx = int(60 * rate) + 1
    with av.open(str(PROXY)) as c:
        proxy_span = c.streams.video[0].frames - 1

    foregrounds = {
        "proxy/random": random_access(PROXY, 0, proxy_span, crop=False),
        "cut/random": random_access(CUT, 0, 300, crop=False),
        "utvideo/random": random_access(UTV, 0, 300, crop=False),
        "original/random-hw": random_access(BIG, base_idx, 2000, crop=True,
                                            hwaccel="cuda"),
        "original/random-sw": random_access(BIG, base_idx, 2000, crop=True),
    }
    run.note(
        f"each foreground: {FETCHES} exact random fetches, same seed across "
        f"backgrounds; loads get {LOAD_WARM_S}s to establish before timing; "
        f"flow load is {FLOW_WORKERS} DIS workers on the cut; encode load is "
        "a looping 1328w proxy encode of the original to the null muxer."
    )

    for bg_name, kinds in BACKGROUNDS.items():
        procs = [_spawn_encode() if k == "encode" else _spawn(k)
                 for k in kinds]
        try:
            if procs:
                time.sleep(LOAD_WARM_S)
            for fg_name, work in foregrounds.items():
                dead = sum(p.poll() is not None for p in procs)
                if dead:
                    run.note(f"{fg_name}@{bg_name}: {dead}/{len(procs)} load "
                             "processes dead BEFORE the case — load was not "
                             "what the name says")
                try:
                    time_case(
                        run, f"{fg_name}@{bg_name}", work,
                        params={"foreground": fg_name, "background": bg_name,
                                "loads": kinds},
                        unit="ms per frame fetched",
                    )
                except Exception as exc:  # noqa: BLE001 - absence is the datum
                    run.note(f"{fg_name}@{bg_name} did not run: {exc!r}")
        finally:
            for p in procs:
                p.terminate()
            for p in procs:
                try:
                    p.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    p.kill()

    for case in run.cases:
        report(case)
    print(f"\nwrote {run.write()}")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--load":
        kind = sys.argv[2]
        try:
            if kind == "sw-sweep":
                _load_sweep(None)
            elif kind == "hw-sweep":
                _load_sweep("cuda")
            elif kind == "flow":
                _load_flow()
        except KeyboardInterrupt:
            pass
        sys.exit(0)
    main()

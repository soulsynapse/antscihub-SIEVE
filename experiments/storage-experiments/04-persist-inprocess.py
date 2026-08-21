"""Persist: what encoding the grown cut costs the foreground, in-process vs out.

The contention matrix priced a *separate-process* ffmpeg encode against the
foreground and found it nearly free. But the lazily grown cut's natural
implementation encodes from the RAM tier's own arrays — same process, same
GIL — and that is unmeasured. If the in-process encoder stalls the scrub,
persistence needs process isolation (and pays shared-memory or re-decode to
get it); if it doesn't, the design stays simple.

Sessions, all against a pre-filled cache of the region (every scrub fetch a
hit, so any foreground latency is *interference*, not decode):

  baseline          scrub with nothing else running — the floor.
  encode-thread     scrub while a thread encodes the cut from cached arrays
                    via PyAV/libx264.
  encode-subprocess scrub while ffmpeg encodes the same cut from the
                    original in another process (the contention-matrix
                    shape, for direct comparison).
  encode-solo       the thread encoder with no foreground — its clean wall,
                    and the from-RAM encode rate the persist trigger design
                    needs.
"""

from __future__ import annotations

import random
import subprocess
import sys
import threading
import time
from fractions import Fraction
from pathlib import Path

import av
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decode-experiments"))
import harness
from harness import FOOTAGE, Case, Run, report

harness.RESULTS = Path(__file__).resolve().parent / "results"

BIG = FOOTAGE / "GX010047c2_02_17_26.MP4"

# ── knobs ────────────────────────────────────────────────────────────────────
SPAN = 300
START_S = 60
CROP_W, CROP_H, CROP_X, CROP_Y = 1024, 1024, 2144, 982
N_FETCHES = 100
FETCH_INTERVAL_S = 0.05
FETCH_SEED = 7
LINGER_SIGMA = 8
LINGER_JUMP_P = 0.12
ENC_OPTS = {"crf": "18", "preset": "veryfast", "g": "1"}  # exp05's winner
SCRATCH = FOOTAGE / "derived" / "_scratch-persist.mp4"


def _pts_helpers(stream):
    tb, rate = stream.time_base, stream.average_rate
    base = stream.start_time or 0
    step = Fraction(1, 1) / (rate * tb)
    return (lambda i: base + int(step * i)), step


def _crop_luma(frame):
    plane = frame.planes[0]
    arr = np.frombuffer(plane, dtype=np.uint8)
    arr = arr[: frame.height * plane.line_size]
    arr = arr.reshape(frame.height, plane.line_size)[:, : frame.width]
    return np.ascontiguousarray(arr[CROP_Y : CROP_Y + CROP_H,
                                    CROP_X : CROP_X + CROP_W])


def fill_cache(base_idx: int) -> dict[int, np.ndarray]:
    cache: dict[int, np.ndarray] = {}
    with av.open(str(BIG)) as container:
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"
        pts_of, step = _pts_helpers(stream)
        target = pts_of(base_idx)
        container.seek(target, stream=stream)
        decoded = container.decode(stream)
        for frame in decoded:
            if frame.pts is not None and frame.pts + step / 2 >= target:
                break
        cache[0] = _crop_luma(frame)
        for rel, frame in enumerate(decoded, start=1):
            if rel >= SPAN:
                break
            cache[rel] = _crop_luma(frame)
    return cache


def encode_from_cache(cache: dict, done: list) -> None:
    """The persist path: cached luma arrays -> lossy-intra file via libx264.

    Luma-only cache means flat chroma in the file; timing is what is being
    measured, and a real store would cache YUV (03's form question).
    """
    before = time.perf_counter()
    with av.open(str(SCRATCH), "w") as out:
        stream = out.add_stream("libx264", rate=24)
        stream.width, stream.height = CROP_W, CROP_H
        stream.pix_fmt = "yuv420p"
        stream.options = dict(ENC_OPTS)
        for i in range(SPAN):
            vf = av.VideoFrame.from_ndarray(cache[i], format="gray")
            vf = vf.reformat(format="yuv420p")
            for pkt in stream.encode(vf):
                out.mux(pkt)
        for pkt in stream.encode():
            out.mux(pkt)
    done.append(time.perf_counter() - before)


def lingering_targets() -> list[int]:
    rng = random.Random(FETCH_SEED)
    targets, anchor = [], rng.randrange(SPAN)
    for _ in range(N_FETCHES):
        if rng.random() < LINGER_JUMP_P:
            anchor = rng.randrange(SPAN)
        targets.append(max(0, min(SPAN - 1, round(rng.gauss(anchor, LINGER_SIGMA)))))
    return targets


def scrub(cache: dict) -> list[float]:
    samples = []
    next_tick = time.perf_counter()
    for t in lingering_targets():
        now = time.perf_counter()
        if now < next_tick:
            time.sleep(next_tick - now)
        next_tick = max(next_tick, now) + FETCH_INTERVAL_S
        before = time.perf_counter()
        cache[t]  # pre-filled: always a hit; latency here is interference
        samples.append((time.perf_counter() - before) * 1000.0)
    return samples


def main() -> None:
    run = Run(
        experiment="04-persist-inprocess",
        question=(
            "Does encoding the grown cut from the RAM tier's arrays, in "
            "process, stall a scrub that the contention matrix showed a "
            "separate-process encode does not?"
        ),
    )
    if not BIG.exists():
        print(f"missing {BIG}")
        return
    run.add_footage(BIG)
    with av.open(str(BIG)) as c:
        rate = c.streams.video[0].average_rate
    base_idx = int(START_S * rate) + 1
    before = time.perf_counter()
    cache = fill_cache(base_idx)
    run.note(f"cache pre-filled: {len(cache)} frames in "
             f"{time.perf_counter() - before:.2f}s (sequential, no foreground)")
    SCRATCH.parent.mkdir(exist_ok=True)

    def case(name: str, samples: list[float], params: dict) -> None:
        params = dict(params)
        params["warmup_discarded"] = 0
        run.cases.append(Case(name, params, samples, unit="ms per fetch (hit)",
                              note="all fetches are cache hits; latency is "
                                   "interference"))

    case("baseline", scrub(cache), {"load": "none"})

    SCRATCH.unlink(missing_ok=True)
    done: list[float] = []
    t = threading.Thread(target=encode_from_cache, args=(cache, done),
                         daemon=True)
    t.start()
    samples = scrub(cache)
    t.join(timeout=120)
    wall = done[0] if done else None
    case("encode-thread", samples,
         {"load": "in-process libx264 from cached arrays",
          "encode_wall_s": wall,
          "cut_bytes": SCRATCH.stat().st_size if SCRATCH.exists() else None})
    run.note(f"encode-thread: {SPAN} frames from RAM in "
             + (f"{wall:.2f}s" if wall else "DID NOT FINISH"))

    SCRATCH.unlink(missing_ok=True)
    proc = subprocess.Popen(
        ["ffmpeg", "-hide_banner", "-nostdin", "-v", "error", "-y",
         "-ss", str(START_S), "-i", str(BIG), "-frames:v", str(SPAN),
         "-vf", f"crop={CROP_W}:{CROP_H}:{CROP_X}:{CROP_Y}", "-an",
         "-c:v", "libx264", "-crf", ENC_OPTS["crf"], "-preset",
         ENC_OPTS["preset"], "-g", ENC_OPTS["g"], str(SCRATCH)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    before = time.perf_counter()
    samples = scrub(cache)
    proc.wait(timeout=120)
    case("encode-subprocess", samples,
         {"load": "ffmpeg from original, separate process",
          "encode_wall_s": time.perf_counter() - before})

    SCRATCH.unlink(missing_ok=True)
    done = []
    encode_from_cache(cache, done)
    case("encode-solo", [done[0] * 1000.0],
         {"load": "none (the encoder alone)", "encode_wall_s": done[0]})
    SCRATCH.unlink(missing_ok=True)

    for c_ in run.cases:
        report(c_)
    print(f"\nwrote {run.write()}")


if __name__ == "__main__":
    main()

"""The cut: does an intra-only intermediate make random access stop costing anything?

The finding on the shelf says decode cost tracks pixels, not bytes, and
ideas.md claims intra-only (FFV1) additionally retires the seek problem while
CRF does not — v1's default was CRF and therefore never had the property. This
cuts one 300-frame, 1024x1024 region out of the 5.3K source three ways (FFV1
intra, x264 CRF18 inter, x264 CRF18 intra) and measures each against decoding
the original with a crop, both sequentially and at random frames. Encode wall
time and output size go into the notes, because the cut's cost is part of the
claim.

The random-access case is the point: on an inter-coded clip a random frame
pays keyframe-plus-decode-forward; on an intra-only one it should pay an index
lookup and one decode. The lossy-intra case separates 'intra' from 'lossless',
which the FFV1-only comparison conflates.
"""

from __future__ import annotations

import random
import subprocess
import time
from fractions import Fraction
from pathlib import Path

import av
import numpy as np

from harness import FOOTAGE, Run, report, time_case

BIG = FOOTAGE / "GX010047c2_02_17_26.MP4"
DERIVED = FOOTAGE / "derived"
FRAMES = 300
CROP_W, CROP_H, CROP_X, CROP_Y = 1024, 1024, 2144, 982
SS = "60"  # seconds into the source; base index recorded per-case from the rate

CLIPS = {
    "ffv1-intra": (DERIVED / "cut-ffv1.mkv", ["-c:v", "ffv1", "-level", "3", "-g", "1", "-slices", "16", "-threads", "8"]),
    "x264-crf18-inter": (DERIVED / "cut-crf18.mp4", ["-c:v", "libx264", "-crf", "18", "-preset", "veryfast"]),
    "x264-crf18-intra": (DERIVED / "cut-crf18-intra.mp4", ["-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-g", "1"]),
}


def encode_clips(run: Run) -> None:
    DERIVED.mkdir(exist_ok=True)
    for name, (path, codec_args) in CLIPS.items():
        if path.exists():
            run.note(f"{name}: reused existing {path.name} ({path.stat().st_size} bytes)")
            continue
        cmd = [
            "ffmpeg", "-hide_banner", "-nostdin", "-v", "error", "-y",
            "-ss", SS, "-i", str(BIG), "-frames:v", str(FRAMES),
            "-vf", f"crop={CROP_W}:{CROP_H}:{CROP_X}:{CROP_Y}",
            "-an", *codec_args, str(path),
        ]
        before = time.perf_counter()
        r = subprocess.run(cmd, stderr=subprocess.PIPE)
        wall = time.perf_counter() - before
        if r.returncode != 0:
            run.note(f"{name}: encode FAILED: {r.stderr.decode(errors='replace')[:200]}")
            continue
        run.note(f"{name}: encoded in {wall:.1f}s, {path.stat().st_size} bytes")


def _pts_helpers(stream):
    tb, rate = stream.time_base, stream.average_rate
    base = stream.start_time or 0
    step = Fraction(1, 1) / (rate * tb)
    return (lambda i: base + int(step * i)), step


def _take_luma(frame, crop):
    plane = frame.planes[0]
    arr = np.frombuffer(plane, dtype=np.uint8)
    arr = arr[: frame.height * plane.line_size]
    arr = arr.reshape(frame.height, plane.line_size)[:, : frame.width]
    if crop:
        arr = arr[CROP_Y : CROP_Y + CROP_H, CROP_X : CROP_X + CROP_W]
    return np.ascontiguousarray(arr)  # both routes pay one small copy


def sequential(path: Path, base_idx: int, n: int, crop: bool):
    def work():
        with av.open(str(path)) as container:
            stream = container.streams.video[0]
            stream.thread_type = "AUTO"
            pts_of, step = _pts_helpers(stream)
            target = pts_of(base_idx)
            container.seek(target, stream=stream)
            decoded = container.decode(stream)
            for frame in decoded:  # roll to start, untimed
                if frame.pts is not None and frame.pts + step / 2 >= target:
                    break
            yield "open"
            _take_luma(frame, crop)
            yield True
            for index, frame in enumerate(decoded):
                if index >= n - 1:
                    break
                _take_luma(frame, crop)
                yield True

    return work


def random_access(path: Path, base_idx: int, span: int, n: int, crop: bool):
    rng = random.Random(7)
    targets = [base_idx + rng.randrange(span) for _ in range(n)]

    def work():
        with av.open(str(path)) as container:
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
        experiment="05-the-cut",
        question=(
            "Does an intra-only cut retire random-access cost, and what do "
            "the three routes to the same 1024x1024 region cost sequentially "
            "and at random frames?"
        ),
    )
    encode_clips(run)
    present = [(n, p) for n, (p, _) in CLIPS.items() if p.exists()]
    run.add_footage(BIG, *(p for _, p in present))
    run.note(
        "original-source cases decode the 5.3K frame and slice the same "
        "region out of the luma plane; clip cases decode their own file. "
        "Both pay one contiguous copy of the 1024x1024 result."
    )

    with av.open(str(BIG)) as c:
        rate = c.streams.video[0].average_rate
    base_idx = int(int(SS) * rate) + 1
    run.note(
        f"original-source cases start at frame {base_idx} (~{SS}s); clip "
        "frame 0 corresponds to it within a frame."
    )

    time_case(
        run, "original/sequential+crop", sequential(BIG, base_idx, FRAMES, True),
        params={"file": BIG.name, "mode": "sequential", "crop": True},
    )
    time_case(
        run, "original/random", random_access(BIG, base_idx, FRAMES, 32, True),
        params={"file": BIG.name, "mode": "random", "crop": True},
        unit="ms per frame fetched",
    )
    for name, path in present:
        time_case(
            run, f"{name}/sequential", sequential(path, 0, FRAMES, False),
            params={"file": path.name, "mode": "sequential", "crop": False},
        )
        time_case(
            run, f"{name}/random", random_access(path, 0, FRAMES, 32, False),
            params={"file": path.name, "mode": "random", "crop": False},
            unit="ms per frame fetched",
        )

    for case in run.cases:
        report(case)
    print(f"\nwrote {run.write()}")


if __name__ == "__main__":
    main()

"""The flow wall: how big a span can re-pay DIS before it stops feeling live.

The analysis cache invalidates from flow upward: change a flow parameter and
the whole span's reduced series re-pays decode+DIS. Whether flow knobs can
be *sliders* or must be commit-style parameters is a product-shape decision
hanging off one number — the wall-clock of that re-pay as a function of span
length. exp06 priced DIS per frame on the cut; this measures the end-to-end
sweep (decode + flow + reduce) at the spans a tuning session actually holds,
on the two files it would run against.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import av
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decode-experiments"))
import harness
from harness import FOOTAGE, Run, report, time_case

harness.RESULTS = Path(__file__).resolve().parent / "results"

CUT = FOOTAGE / "derived" / "cut-crf18-intra.mp4"
PROXY = FOOTAGE / "derived" / "proxy-1328-intra.mp4"

# ── knobs ────────────────────────────────────────────────────────────────────
SPANS = (300, 1000, 3000)     #: frames per sweep (cut caps at its length)
PRESET = cv2.DISOPTICAL_FLOW_PRESET_ULTRAFAST


def _luma(frame):
    plane = frame.planes[0]
    arr = np.frombuffer(plane, dtype=np.uint8)
    arr = arr[: frame.height * plane.line_size]
    arr = arr.reshape(frame.height, plane.line_size)[:, : frame.width]
    return np.ascontiguousarray(arr)


def sweep(path: Path, n: int):
    def work():
        dis = cv2.DISOpticalFlow_create(PRESET)
        with av.open(str(path)) as container:
            stream = container.streams.video[0]
            stream.thread_type = "AUTO"
            decoded = container.decode(stream)
            prev = _luma(next(decoded))
            yield "open"
            for count, frame in enumerate(decoded):
                if count >= n - 1:
                    break
                cur = _luma(frame)
                flow = dis.calc(prev, cur, None)
                float(np.mean(np.abs(flow)))  # the reduction, kept honest
                prev = cur
                yield True

    return work


def main() -> None:
    run = Run(
        experiment="05-flow-wall",
        question=(
            "End-to-end decode+DIS+reduce wall time per span length, on the "
            "cut and the proxy — the number that decides whether flow "
            "parameters can be sliders."
        ),
    )
    for path in (CUT, PROXY):
        if not path.exists():
            print(f"missing {path} — regenerate per the synthesis recreate "
                  "section")
            return
    run.add_footage(CUT, PROXY)

    for path in (CUT, PROXY):
        with av.open(str(path)) as c:
            nframes = c.streams.video[0].frames or 10**9
        for span in SPANS:
            if span > nframes:
                run.note(f"{path.name}: span {span} skipped ({nframes} frames)")
                continue
            case = time_case(
                run, f"{path.name}/span={span}", sweep(path, span),
                params={"file": path.name, "span": span,
                        "preset": "DIS_ULTRAFAST"},
                unit="ms per frame (decode+DIS+reduce)",
            )
            wall = sum(case.samples_ms) / 1000.0
            case.params["wall_s"] = round(wall, 2)
            print(f"      wall for {span} frames: {wall:.2f}s")

    for case in run.cases:
        report(case)
    print(f"\nwrote {run.write()}")


if __name__ == "__main__":
    main()

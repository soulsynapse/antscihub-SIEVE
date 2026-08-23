"""What riding along on a fetch that was happening anyway actually costs.

A step's arithmetic is cheap or dear only relative to what produced its
input, so this prices each step's field and reduction on inputs that are
already decoded and resident. That is the marginal cost of computing one
while the input is hot, and it is the number the cheapest cost class is
defined against.

`tools.classify` reads it against two things:

**Free** means the work is in the noise beside the fetch that produced the
input. So the test is a ratio, and the regime is what decides it: the same
arithmetic is free beside one fetch and not beside another, at the same size,
because the fetches differ by orders of magnitude between a large original
and a small derived file. The ratio is recorded per case so the cut can be
moved without anything being re-run.

**Budgeted** means it fits a frame period at the analysis form. The budget is
not the whole period — the fetch and the drawing are in it too, and the paint
figure comes from `01-paint-cost` rather than being re-measured here. What is
reported is the residual after both, because a step that fits the period
alone and not beside the drawing of it does not fit.

Cost class used to be a field each step declared. This experiment falsified
the declaring rather than any one declaration, which is ADR-0007; it computes
the class per pairing and reports which steps land in different classes
against different fetches.

Two signals that need no decode at all are priced beside them, because the
cheapest thing in the ladder is what the encoder already paid for: per-frame
packet size, which is demux-only, and motion vectors, where a build will
export them.

Real inputs throughout. Frame differencing on random noise is maximally
different everywhere and dense flow on it has nothing to track; both are the
wrong shape and would misprice the arithmetic in opposite directions.
"""

from __future__ import annotations

import sys
from pathlib import Path

import av
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decode-experiments"))
import harness  # noqa: E402
from harness import FOOTAGE, Run, quantiles, report, time_case  # noqa: E402

import tools as toolkit  # noqa: E402

harness.RESULTS = Path(__file__).resolve().parent / "results"

BIG = FOOTAGE / "GX010047c2_02_17_26.MP4"
CUT = FOOTAGE / "derived" / "cut-crf18-intra.mp4"

CROP = (2144, 982, 1024, 1024)
FPS = 24000 / 1001
PAINT_MS = 2.1     #: read from 01-paint-cost rather than re-measured here
HELD = 40          #: real inputs held resident for the arithmetic cases
REPS = 40
MV_FRAMES = 21     #: frames to check for exported motion vectors


def _luma_crop(frame, rect):
    plane = frame.planes[0]
    arr = np.frombuffer(plane, dtype=np.uint8)
    arr = arr[: frame.height * plane.line_size]
    arr = arr.reshape(frame.height, plane.line_size)[:, : frame.width]
    x, y, w, h = rect
    return np.ascontiguousarray(arr[y:y + h, x:x + w])


def _resident(path: Path, count: int):
    out = []
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"
        for frame in container.decode(stream):
            out.append(_luma_crop(frame, (0, 0, frame.width, frame.height)))
            if len(out) >= count:
                break
    return out


def repeat(fn, n=REPS):
    def work():
        yield "start"
        for i in range(n):
            fn(i)
            yield True
    return work


def main() -> None:
    run = Run(
        experiment="03-free-while-hot",
        question="What does a step's field cost on an already-resident "
                 "input, and which class does that put it in, against "
                 "which fetch?",
    )
    run.add_footage(BIG, CUT)
    period_ms = 1000.0 / FPS
    run.note(f"frame period {period_ms:.1f} ms at {FPS:.3f} fps; the paint "
             f"figure is read from 01-paint-cost rather than re-measured, "
             f"and the budgeted test uses the residual after fetch and paint")
    run.note(f"free is taken as at most {toolkit.FREE_RATIO}x the fetch that "
             f"produced the input (tools.FREE_RATIO); every case records the "
             f"ratio it was judged on, so the cut can be moved without "
             f"re-running anything")

    # ── fetch baselines, per regime ──────────────────────────────────────
    print("fetch, per regime (plane 0, no scaler):")
    fetches: dict[str, float] = {}
    streams: dict[Path, object] = {}
    for path, label, rect in ((BIG, "uncut source crop", CROP),
                              (CUT, "intra cut", None)):
        if not path.exists():
            run.note(f"{label}: {path.name} absent, not run")
            continue

        def go(_i, path=path, rect=rect):
            state = streams.get(path)
            if state is None:
                container = av.open(str(path))
                stream = container.streams.video[0]
                stream.thread_type = "AUTO"
                state = streams[path] = container.decode(stream)
            frame = next(state)
            return _luma_crop(frame, rect or (0, 0, frame.width, frame.height))
        case = time_case(run, f"fetch {label}", repeat(go),
                         params={"file": path.name}, unit="ms per frame")
        report(case)
        fetches[label] = quantiles(case.samples_ms)["p50"]

    # ── the steps, on inputs already resident ────────────────────────────
    frames = _resident(CUT, HELD)
    height, width = frames[0].shape
    print(f"\nfield + reduce on resident {width}x{height} real inputs:")
    verdicts = []
    for make in (toolkit.absdiff, toolkit.dis_flow, toolkit.lag_mhi):
        tool = make()
        base = tool.reach
        if base >= len(frames):
            run.note(f"{tool.key()}: reach {base} exceeds {len(frames)} held "
                     "inputs, not run")
            continue

        def go(i, tool=tool, base=base):
            row = base + (i % (len(frames) - base))
            window = {r: frames[r] for r in tool.needs(row)}
            return tool.reduce(tool.field(window, row))
        case = time_case(run, f"{tool.key()} field+reduce", repeat(go),
                         params={"offsets": list(tool.offsets),
                                 "size": [width, height]},
                         unit="ms per frame")
        report(case)
        field_ms = quantiles(case.samples_ms)["p50"]
        for label, fetch_ms in fetches.items():
            verdicts.append({
                "tool": tool.key(), "against": label,
                "field_ms": round(field_ms, 3),
                "fetch_ms": round(fetch_ms, 3),
                "ratio": round(field_ms / fetch_ms, 2) if fetch_ms else None,
                "residual_ms": round(period_ms - fetch_ms - PAINT_MS, 1),
                "verdict": toolkit.classify(field_ms, fetch_ms, period_ms,
                                            PAINT_MS)})

    print("\nclass, per pairing:")
    for v in verdicts:
        print(f"  {v['tool']:<26} vs {v['against']:<19} field "
              f"{v['field_ms']:>7.3f} ms = {v['ratio']:>7.2f}x fetch "
              f"-> {v['verdict']}")
    seen = {v["tool"]: {w["verdict"] for w in verdicts if w["tool"] == v["tool"]}
            for v in verdicts}
    split = [name for name, classes in seen.items() if len(classes) > 1]
    run.note("class per pairing: " + "; ".join(
        f"{v['tool']} is {v['verdict']} against {v['against']} "
        f"({v['ratio']}x fetch)" for v in verdicts))
    run.note(f"{len(split)} of {len(seen)} steps land in a different class "
             f"against the two fetches: {', '.join(split) or 'none'}. A class "
             f"is a property of the step-and-fetch pairing rather than of the "
             f"step, which is ADR-0007 and why nothing declares one.")
    print(f"\n{len(split)}/{len(seen)} steps change class between regimes: "
          f"{', '.join(split) or 'none'}")

    # ── the signals that need no decode ──────────────────────────────────
    print("\nsignals the encoder already paid for:")
    packets = {}

    def packet_size(_i):
        state = packets.get("demux")
        if state is None:
            container = av.open(str(BIG))
            state = packets["demux"] = container.demux(
                container.streams.video[0])
        return next(state).size
    case = time_case(run, "packet size (demux only, no decode)",
                     repeat(packet_size), params={"file": BIG.name},
                     unit="ms per frame")
    report(case)

    try:
        container = av.open(str(BIG))
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"
        stream.codec_context.options = {"flags2": "+export_mvs"}
        found = 0
        for count, frame in enumerate(container.decode(stream)):
            if any(sd.type.name == "MOTION_VECTORS"
                   for sd in getattr(frame, "side_data", []) or []):
                found += 1
            if count >= MV_FRAMES - 1:
                break
        container.close()
        run.note(f"motion vectors: {found} of {MV_FRAMES} decoded frames "
                 f"carried a MOTION_VECTORS side-data block with +export_mvs "
                 f"on this build and codec; "
                 f"{'available' if found else 'NOT available'} as a free "
                 f"signal here")
        print(f"  motion vectors present on {found}/{MV_FRAMES} frames")
    except Exception as exc:  # noqa: BLE001
        run.note(f"motion vectors: could not be exported on this build ({exc!r})")
        print(f"  motion vectors unavailable: {exc!r}")

    path = run.write()
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()

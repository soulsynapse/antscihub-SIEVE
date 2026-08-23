"""What riding along on a decode that was happening anyway actually costs.

`tools.py` used to let a tool declare a cost class — `free`, `budgeted`,
`commit` — on the grounds that a declaration nothing can falsify is not
worth writing down. This is the falsifier, and what it falsified was the
declaring rather than any one declaration. It prices each tool's field and
reduction on frames already decoded and resident, which is the marginal cost
of computing one while the frame is hot, and reads it against the two things
the class names are about:

- **`free`** means the work is in the noise beside the decode that produced
  the frame. So the test is a ratio against decode at the same regime, and
  the regime is what decides it: the same op is free beside a 5.3K decode
  and not free beside an intra chunk, at the same size, because the decodes
  differ by a factor of forty. The result reports the ratio rather than a
  verdict alone, so the cut can be moved without re-running anything.

- **`budgeted`** means it fits a frame period at the analysis form. The
  budget is not the whole period: serve and paint are in it too, and paint
  is measured next door (`01-paint-cost`). What is reported is the residual
  after both, because a tool that fits the period alone and not beside the
  drawing of it does not fit.

Two signals that need no decode at all are priced beside them, since the
cheapest thing in the ladder is the thing the encoder already paid for:
per-frame packet size, which is demux-only, and motion vectors, which come
out of the stream when the decoder is asked to export them.

Real frames throughout, not synthetic. Frame differencing on random noise is
maximally different everywhere and dense flow on it has nothing to track;
both are the wrong shape and would misprice the ops in opposite directions.
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

import forms  # noqa: E402
import tools as toolkit  # noqa: E402

harness.RESULTS = Path(__file__).resolve().parent / "results"

BIG = FOOTAGE / "GX010047c2_02_17_26.MP4"
CUT = FOOTAGE / "derived" / "cut-crf18-intra.mp4"

CROP = (2144, 982, 1024, 1024)
FPS = 24000 / 1001          #: the source's rate; the frame period is its inverse
PAINT_MS = 2.1              #: measured next door; read from 01-paint-cost
HELD = 40                   #: real frames held for the compute cases
REPS = 40


def _luma_crop(frame, rect):
    plane = frame.planes[0]
    arr = np.frombuffer(plane, dtype=np.uint8)
    arr = arr[: frame.height * plane.line_size]
    arr = arr.reshape(frame.height, plane.line_size)[:, : frame.width]
    x, y, w, h = rect
    return np.ascontiguousarray(arr[y:y + h, x:x + w])


def _real_frames(path: Path, count: int, rect):
    out = []
    with av.open(str(path)) as container:
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"
        for frame in container.decode(stream):
            out.append(_luma_crop(frame, rect or (0, 0, frame.width, frame.height)))
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
        question="What does a tool's field cost on an already-decoded frame, "
                "and which class does that put it in, against which decode?",
    )
    run.add_footage(BIG, CUT)
    period_ms = 1000.0 / FPS
    run.note(f"frame period {period_ms:.1f} ms at {FPS:.3f} fps; "
             f"paint {PAINT_MS} ms is read from 01-paint-cost rather than "
             f"re-measured, and the budgeted test uses the residual after "
             f"decode and paint")
    run.note(f"free is taken as at most {toolkit.FREE_RATIO}x the decode that "
             f"produced the frame (tools.FREE_RATIO); the ratio is recorded "
             f"per case so the cut can be moved without re-running anything")

    # ── decode baselines, per regime ─────────────────────────────────────
    print("decode, per regime (plane 0, no scaler):")
    decodes: dict[str, float] = {}
    for path, label, rect in ((BIG, "uncut 5.3K crop", CROP),
                              (CUT, "intra cut", None)):
        if not path.exists():
            run.note(f"{label}: {path.name} absent, not run")
            continue

        def go(_i, path=path, rect=rect):
            state = go.state.get(path)
            if state is None:
                container = av.open(str(path))
                stream = container.streams.video[0]
                stream.thread_type = "AUTO"
                state = go.state[path] = container.decode(stream)
            frame = next(state)
            use = rect or (0, 0, frame.width, frame.height)
            return _luma_crop(frame, use)
        go.state = {}
        case = time_case(run, f"decode {label}", repeat(go),
                         params={"file": path.name}, unit="ms per frame")
        report(case)
        decodes[label] = quantiles(case.samples_ms)["p50"]

    # ── the tools, on frames already resident ────────────────────────────
    frames = _real_frames(CUT, HELD, None)
    height, width = frames[0].shape
    print(f"\nfield + reduce on resident {width}x{height} real frames:")
    rect = (0, 0, width, height)
    verdicts = []
    for make in (toolkit.absdiff, toolkit.dis_flow, toolkit.lag_mhi):
        tool = make()
        base = -min(tool.offsets)
        if base >= len(frames):
            run.note(f"{tool.key()}: reach {base} exceeds {len(frames)} held "
                     "frames, not run")
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
        got = quantiles(case.samples_ms)["p50"]
        for label, decode_ms in decodes.items():
            ratio = got / decode_ms if decode_ms else float("inf")
            residual = period_ms - decode_ms - PAINT_MS
            verdicts.append({
                "tool": tool.key(), "against": label,
                "field_ms": round(got, 3), "decode_ms": round(decode_ms, 3),
                "ratio": round(ratio, 2), "residual_ms": round(residual, 1),
                "verdict": toolkit.classify(got, decode_ms, period_ms,
                                            PAINT_MS)})

    print("\nclass, per pairing:")
    for v in verdicts:
        print(f"  {v['tool']:<26} vs {v['against']:<16} field "
              f"{v['field_ms']:>7.3f} ms = {v['ratio']:>7.2f}x decode "
              f"-> {v['verdict']}")
    seen = {v["tool"]: {w["verdict"] for w in verdicts if w["tool"] == v["tool"]}
            for v in verdicts}
    split = [name for name, classes in seen.items() if len(classes) > 1]
    run.note("class per pairing: " + "; ".join(
        f"{v['tool']} is {v['verdict']} against {v['against']} "
        f"({v['ratio']}x decode)" for v in verdicts))
    run.note(f"{len(split)} of {len(seen)} tools land in a different class "
             f"against the two decodes: {', '.join(split) or 'none'}. A class "
             f"is a property of the tool-and-decode pairing, not of the tool, "
             f"which is why tools.py no longer lets one be declared.")
    print(f"\n{len(split)}/{len(seen)} tools change class between regimes: "
          f"{', '.join(split) or 'none'}")

    # ── the signals that need no decode ──────────────────────────────────
    print("\nsignals the encoder already paid for:")

    def packet_size(_i):
        state = getattr(packet_size, "state", None)
        if state is None:
            container = av.open(str(BIG))
            state = packet_size.state = container.demux(
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
            if count >= 20:
                break
        container.close()
        run.note(f"motion vectors: {found} of 21 decoded frames carried a "
                 f"MOTION_VECTORS side-data block with +export_mvs on this "
                 f"build; {'available' if found else 'NOT available'} as a "
                 f"free signal here")
        print(f"  motion vectors present on {found}/21 frames")
    except Exception as exc:  # noqa: BLE001
        run.note(f"motion vectors: could not be exported on this build ({exc!r})")
        print(f"  motion vectors unavailable: {exc!r}")

    path = run.write()
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()

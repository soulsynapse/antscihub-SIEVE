"""What a step's arithmetic costs while the machine does the loop's own work.

Every field cost in this folder is otherwise uncontended, and a driven
session of the tool explorer showed that is not the number that gets felt.
Bucketing its log by whether a fill or an encode was running made one step
look specially fragile, which was an accident of a hand-driven session. This
measures it on purpose.

The background work is the loop's actual background work rather than a
synthetic spinner: a thread decoding the original sequentially, which is what
a window fill is, and a thread encoding intra chunks, which is what the
write-behind is. Contention for the interpreter lock and for memory bandwidth
against *that* is the subject, and a busy loop would take neither in the same
proportion.

Two things it settles.

**How much each step inflates**, which need not be a constant. Arithmetic
that makes a few passes over an image contends differently from arithmetic
that spends its time inside a solver, so whether the inflation is uniform is
a question rather than an assumption.

**Whether the median or the tail decides the class.** A step that fits a
frame period at the median and misses it at the tail is felt as lag rather
than as a step that fits, so `tools.classify` may need to read a tail. What
tail, and how much worse than the median, is what this run is for — and if
the two agree everywhere, then the change is not supported and should not be
made.

No GUI here and no paint: this prices the arithmetic under contention, and
the explorer prices what that feels like.
"""

from __future__ import annotations

import sys
import threading
import time
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
SCRATCH = FOOTAGE / "derived" / "_under-load-scratch.mp4"

CROP = (2144, 982, 1024, 1024)
FPS = 24000 / 1001
PAINT_MS = 2.1          #: read from 01-paint-cost
FETCH_MS = 0.13         #: the chunk-regime fetch, from 02-form-derivation
HELD = 40
REPS = 120              #: more than the quiet runs: the tail is the point
SETTLE_S = 1.5          #: let the background reach steady state first


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


class Load:
    """The loop's own background work, started and stopped around a case.

    A fill is a sequential decode of the original with the crop sliced out;
    an encode is intra frames into a container. Neither is synthetic,
    because what is being measured is contention against this work in
    particular.
    """

    def __init__(self, fill: bool, encode: bool, frames):
        self.fill, self.encode = fill, encode
        self.frames = frames
        self.stop = threading.Event()
        self.threads: list[threading.Thread] = []
        self.fills = 0
        self.encodes = 0

    def _fill_loop(self):
        while not self.stop.is_set():
            try:
                with av.open(str(BIG)) as container:
                    stream = container.streams.video[0]
                    stream.thread_type = "AUTO"
                    for frame in container.decode(stream):
                        _luma_crop(frame, CROP)
                        self.fills += 1
                        if self.stop.is_set():
                            return
            except Exception:  # noqa: BLE001
                return

    def _encode_loop(self):
        while not self.stop.is_set():
            try:
                with av.open(str(SCRATCH), "w") as out:
                    stream = out.add_stream("libx264", rate=24)
                    stream.height, stream.width = self.frames[0].shape
                    stream.pix_fmt = "yuv420p"
                    stream.options = {"crf": "18", "preset": "veryfast",
                                      "g": "1"}
                    for arr in self.frames:
                        vf = av.VideoFrame.from_ndarray(arr, format="gray")
                        for pkt in stream.encode(vf.reformat(format="yuv420p")):
                            out.mux(pkt)
                        self.encodes += 1
                        if self.stop.is_set():
                            break
                    for pkt in stream.encode():
                        out.mux(pkt)
            except Exception:  # noqa: BLE001
                return
        SCRATCH.unlink(missing_ok=True)

    def __enter__(self):
        if self.fill:
            self.threads.append(threading.Thread(target=self._fill_loop,
                                                 daemon=True))
        if self.encode:
            self.threads.append(threading.Thread(target=self._encode_loop,
                                                 daemon=True))
        for t in self.threads:
            t.start()
        if self.threads:
            time.sleep(SETTLE_S)
        return self

    def __exit__(self, *exc):
        self.stop.set()
        for t in self.threads:
            t.join(timeout=5)
        return False


def repeat(fn, n=REPS):
    def work():
        yield "start"
        for i in range(n):
            fn(i)
            yield True
    return work


def main() -> None:
    run = Run(
        experiment="04-under-load",
        question="What does a step's arithmetic cost while a fill and a "
                 "write-behind encode run, and does the tail or the median "
                 "decide whether it fits?",
    )
    run.add_footage(BIG, CUT)
    period_ms = 1000.0 / FPS
    run.note("the background work is a sequential decode of the original "
             "with the crop sliced out (a window fill) and libx264 intra "
             "encoding (the write-behind), not a synthetic spinner — "
             "contention for the interpreter lock and for memory bandwidth "
             "is the subject, and a busy loop would take neither in the same "
             "proportion")
    run.note("the interpreter's switch interval is left at its default; the "
             "explorer shortens it, so these are the untuned ratios and the "
             "explorer's are the tuned ones")
    run.note("the fetch and paint figures used for classification come from "
             "02-form-derivation and 01-paint-cost rather than being "
             "re-measured here")

    frames = _resident(CUT, HELD)
    height, width = frames[0].shape
    print(f"resident {width}x{height} real inputs; period {period_ms:.1f} ms\n")

    conditions = (("idle", False, False),
                  ("fill", True, False),
                  ("fill+encode", True, True))
    table: dict[tuple[str, str], dict] = {}
    for label, fill, encode in conditions:
        print(f"{label}:")
        for make in (toolkit.absdiff, toolkit.dis_flow, toolkit.lag_mhi):
            tool = make()
            base = tool.reach
            with Load(fill, encode, frames) as load:
                def go(i, tool=tool, base=base):
                    row = base + (i % (len(frames) - base))
                    window = {r: frames[r] for r in tool.needs(row)}
                    return tool.reduce(tool.field(window, row))
                case = time_case(run, f"{tool.key()} under {label}",
                                 repeat(go),
                                 params={"load": label, "fill": fill,
                                         "encode": encode,
                                         "size": [width, height]},
                                 unit="ms per frame")
            report(case)
            table[(tool.key(), label)] = quantiles(case.samples_ms)
            if fill or encode:
                run.note(f"{tool.key()} under {label}: the background did "
                         f"{load.fills} fill frames and {load.encodes} "
                         f"encodes during the case")
        print()

    print(f"{'step':<26} {'condition':<12} {'p50':>7} {'p95':>7} {'max':>8}"
          f"  {'x idle p50':>10}")
    for (key, label), q in table.items():
        idle = table[(key, "idle")]["p50"]
        print(f"{key:<26} {label:<12} {q['p50']:>7.2f} {q['p95']:>7.2f} "
              f"{q['max']:>8.2f}  {q['p50'] / idle:>10.2f}")

    print("\nclass by median against class by tail:")
    verdicts = []
    for (key, label), q in table.items():
        by_p50 = toolkit.classify(q["p50"], FETCH_MS, period_ms, PAINT_MS)
        by_p95 = toolkit.classify(q["p95"], FETCH_MS, period_ms, PAINT_MS)
        verdicts.append({"tool": key, "load": label,
                         "p50": round(q["p50"], 2), "p95": round(q["p95"], 2),
                         "by_median": by_p50, "by_tail": by_p95,
                         "disagrees": by_p50 != by_p95})
        flag = "  <- disagrees" if by_p50 != by_p95 else ""
        print(f"  {key:<26} {label:<12} median->{by_p50:<9} "
              f"tail->{by_p95:<9}{flag}")
    split = [v for v in verdicts if v["disagrees"]]
    run.note("median/tail disagreement: " + (
        "; ".join(f"{v['tool']} under {v['load']} is {v['by_median']} by p50 "
                  f"and {v['by_tail']} by p95" for v in split)
        or "none — the two agree everywhere here, so classifying on a tail "
           "is not supported by this run"))
    print(f"\n{len(split)} of {len(verdicts)} pairings classify differently "
          f"by median than by tail")
    path = run.write()
    print(f"wrote {path}")


if __name__ == "__main__":
    main()

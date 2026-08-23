"""What a tool's field costs while the machine is doing the loop's own work.

Every field number this folder has is uncontended, and a driven session of
the tool explorer found that is not the number that gets felt: bucketing its
log by whether a fill or an encode was running showed dense flow going from
6 ms to 8.8 ms at the median, 15.9 at p95, and once to 131 — while frame
differencing barely moved. The felt report was "lags a bit at some points",
and those points were all one tool under one condition.

That was an accident of a hand-driven session, so this measures it on
purpose, with the background work being the loop's actual background work
rather than a synthetic spinner: a thread decoding the original
sequentially, which is what a window fill is, and a thread encoding intra
chunks, which is what the write-behind is.

Two things it settles.

**How much each tool inflates**, which is not a constant. A tool whose field
is a few numpy passes over a megabyte contends for memory bandwidth and the
GIL differently from one that spends its time inside a solver, and the
ratios in the explorer's log differ by tool by more than a factor of two.

**Whether the tail or the median is the thing to classify on.** A tool that
fits a frame period at p50 and misses it at p99 is felt as lag, not as a
tool that fits — so `tools.classify` should be reading a tail. What tail,
and how much worse it is than the median, is what this run is for.

The GUI is not here and neither is paint, deliberately: this prices the
compute under contention, and the explorer prices what that feels like.
"""

from __future__ import annotations

import queue
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

CROP = (2144, 982, 1024, 1024)
FPS = 24000 / 1001
HELD = 40
REPS = 120          #: more than the quiet experiments: the tail is the point


def _luma_crop(frame, rect):
    plane = frame.planes[0]
    arr = np.frombuffer(plane, dtype=np.uint8)
    arr = arr[: frame.height * plane.line_size]
    arr = arr.reshape(frame.height, plane.line_size)[:, : frame.width]
    x, y, w, h = rect
    return np.ascontiguousarray(arr[y:y + h, x:x + w])


def _real_frames(path: Path, count: int):
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

    A fill is a sequential decode of the original with the crop sliced out,
    which is exactly what `WindowFill` does; an encode is intra frames into
    a container, which is exactly the write-behind. Neither is a synthetic
    spinner, because what is being measured is contention for the GIL and
    for memory bandwidth against *this* work, and a busy loop would contend
    for neither in the same proportion.
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
        out_path = FOOTAGE / "derived" / "_under-load-scratch.mp4"
        while not self.stop.is_set():
            try:
                with av.open(str(out_path), "w") as out:
                    stream = out.add_stream("libx264", rate=24)
                    stream.height, stream.width = self.frames[0].shape
                    stream.pix_fmt = "yuv420p"
                    stream.options = {"crf": "18", "preset": "veryfast", "g": "1"}
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
        out_path.unlink(missing_ok=True)

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
            time.sleep(1.5)   # let the load reach steady state first
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
        question="What does a tool's field cost while a fill and a "
                 "write-behind encode are running, and does the tail or the "
                 "median decide whether it fits?",
    )
    run.add_footage(BIG, CUT)
    period_ms = 1000.0 / FPS
    run.note(f"frame period {period_ms:.1f} ms; the background work is a "
             f"sequential decode of the original with the crop sliced out (a "
             f"window fill) and libx264 intra encoding (the write-behind), "
             f"not a synthetic spinner — contention for the GIL and for "
             f"memory bandwidth is the subject and a busy loop would take "
             f"neither in the same proportion")
    run.note("sys.setswitchinterval is left at its default here; the "
             "explorer sets it to 0.002, so these ratios are the untuned "
             "case and the explorer's are the tuned one")

    frames = _real_frames(CUT, HELD)
    height, width = frames[0].shape
    print(f"resident {width}x{height} real frames; period {period_ms:.1f} ms\n")

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
                run.note(f"{tool.key()} under {label}: background did "
                         f"{load.fills} fill frames, {load.encodes} encodes "
                         f"during the case")
        print()

    print(f"{'tool':<26} {'condition':<12} {'p50':>7} {'p95':>7} {'p99':>7} "
          f"{'max':>8}  {'x idle p50':>10}")
    for (key, label), q in table.items():
        idle = table[(key, "idle")]["p50"]
        print(f"{key:<26} {label:<12} {q['p50']:>7.2f} {q['p95']:>7.2f} "
              f"{q.get('p99', q['p95']):>7.2f} {q['max']:>8.2f}  "
              f"{q['p50'] / idle:>10.2f}")

    # what the classifier would say, median against tail
    print("\nclass by median against class by tail (decode 0.13 ms, "
          "paint 2.8 ms, chunk regime):")
    verdicts = []
    for (key, label), q in table.items():
        by_p50 = toolkit.classify(q["p50"], 0.13, period_ms, 2.8)
        by_p95 = toolkit.classify(q["p95"], 0.13, period_ms, 2.8)
        verdicts.append({"tool": key, "load": label,
                         "p50": round(q["p50"], 2), "p95": round(q["p95"], 2),
                         "by_median": by_p50, "by_tail": by_p95,
                         "disagrees": by_p50 != by_p95})
        flag = "  <- disagrees" if by_p50 != by_p95 else ""
        print(f"  {key:<26} {label:<12} median->{by_p50:<9} "
              f"tail->{by_p95:<9}{flag}")
    split = [v for v in verdicts if v["disagrees"]]
    run.note("median/tail class disagreement: " + (
        "; ".join(f"{v['tool']} under {v['load']} is {v['by_median']} by p50 "
                  f"({v['p50']} ms) and {v['by_tail']} by p95 ({v['p95']} ms)"
                  for v in split) or "none — the two agree everywhere here"))
    print(f"\n{len(split)} of {len(verdicts)} pairings classify differently "
          f"by median than by tail")
    path = run.write()
    print(f"wrote {path}")


if __name__ == "__main__":
    main()

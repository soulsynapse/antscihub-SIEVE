"""What a filled window's wall is made of, term by term.

`2026.08.30-a-second-cursor-makes-preemption-free` took the live walls down
to the parked walls and stopped there, which leaves the obvious question
unanswered: what is the ~6.7 s that remains, and how much of it could go?

The explorer cannot answer it. Its clocks are around *dispatch* — one
envelope per decode, route attached — so everything inside a decode is one
number, and everything outside one is the unattributed remainder. This
prices the two terms the explorer folds together, in isolation, on the
machine that ran it:

    decode floor      sequential luma off the source, nothing held. The
                      ceiling `2026.08.21-sequential-luma-ceiling-is-shared`
                      measured on different hardware; a floor quoted from
                      another machine is not a floor.
    the copy          `_luma` allocates and copies a full plane per frame.
                      Priced three ways -- decode alone, decode plus the
                      plane view, decode plus the copy -- because the view
                      is what the copy is avoiding (it pins the whole
                      AVFrame) and the difference between the two is the
                      real price of not pinning it.
    the copy, cold    the same copy off a frame already held, which is what
                      a microbenchmark of `.copy()` would report. It is
                      several times the in-situ cost because the decoder's
                      buffer is hot, and it is here so that the difference
                      is on the record rather than rediscovered.
    graph bookkeeping what the dispatcher pays per decode before it decodes:
                      `pressure_queue`, `unserved` over a 480-position
                      declaration, `still_wants`, and the GUI's `declare`.
                      Measured because it was the author's first hypothesis
                      for the gap and the measurement refuted it.

The last one is the reason this file exists rather than a paragraph of
arithmetic. `pressure_queue` sorts every need and builds a set of every
declared position twice per call, and it is called after every single
decode; reading the code, that is obviously the hot spot. It is not, by two
orders of magnitude. An unmeasured "obviously" is what this folder's rule
about a number taken in the loop is for.

**Nothing here is a number about the loop.** Every case runs with one
decoder, one thread, no Qt, no tool and no pool. They are the terms a wall
is *composed of*, and the composition is measured in the explorer and
nowhere else -- the folder's rule, applied to itself. The budget arithmetic
this prints against a chosen log is subtraction, not a measurement.
"""

from __future__ import annotations

import json
import statistics as st
import sys
import time
from pathlib import Path

import av
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decode-experiments"))

import harness
from graph import Graph, Need, Urgency

harness.RESULTS = Path(__file__).resolve().parent / "results"

BIG = harness.FOOTAGE / "GX010047c2_02_17_26.MP4"
LOGS = Path(__file__).resolve().parent / "explorer-logs"
N = 400          #: frames per decode case, after the warm-up
WARMUP = 40      #: discarded; the open, the index, and a cold page cache


def _open():
    container = av.open(str(BIG))
    stream = container.streams.video[0]
    stream.thread_type = "AUTO"
    return container, stream


def _view(frame) -> np.ndarray:
    """The luma plane as a view. Keeps the whole AVFrame alive."""
    plane = frame.planes[0]
    arr = np.frombuffer(plane, dtype=np.uint8)
    arr = arr[: frame.height * plane.line_size]
    return arr.reshape(frame.height, plane.line_size)[:, : frame.width]


def _copy(frame) -> np.ndarray:
    return _view(frame).copy()


def _decode_case(run: harness.Run, name: str, hold) -> None:
    """`hold` is what the caller does with each frame, or None."""
    def work():
        container, stream = _open()
        try:
            for index, frame in enumerate(container.decode(stream)):
                if index >= N + WARMUP + 1:
                    return
                if hold is not None:
                    _ = hold(frame)
                yield index
        finally:
            container.close()

    case = harness.time_case(run, name, work, warmup=WARMUP,
                             params={"frames": N, "threads": "AUTO"})
    harness.report(case)


def _graph_case(run: harness.Run) -> None:
    """The dispatcher's per-decode bookkeeping, at the explorer's shape.

    One sweep declaring a 480-frame window, a GUI at one position, a tool
    admitting four offsets -- what `explorer.py --walk` puts in the graph.
    The pool is a set, so `has` costs what a dict probe costs and no more;
    a pool under its lock is the explorer's number, not this one.
    """
    form_key = "src|5312x2988|u8"
    graph = Graph()
    graph.declare(Need("fill", 3768, tuple(range(480)), form_key,
                       Urgency.DEFERRED))
    graph.declare(Need("gui", 3900, (0,), form_key, Urgency.INTERACTIVE))
    graph.declare(Need("tool", 3900, (-30, -20, -10, 0), form_key,
                       Urgency.DEFERRED))
    have = set(range(3768, 3768 + 300))

    def has(position: int, _fk: str) -> bool:
        return position in have

    sweep = next(n for n in graph.pressure_queue() if n.node_id == "fill")

    def one_dispatch() -> None:
        """What `_pick` and the post-decode check cost, once."""
        graph.pressure_queue()
        sweep.unserved(has)
        graph.still_wants("fill", 3900, form_key)
        graph.declare(Need("gui", 3900, (0,), form_key, Urgency.INTERACTIVE))

    def work():
        for index in range(N + WARMUP + 1):
            one_dispatch()
            yield index

    case = harness.time_case(run, "graph bookkeeping per decode", work,
                             warmup=WARMUP, unit="ms per dispatch",
                             params={"declared_positions": 480, "nodes": 3})
    harness.report(case)


def _cold_copy_case(run: harness.Run) -> None:
    container, stream = _open()
    try:
        frame = next(container.decode(stream))
        plane = _view(frame)
        nbytes = plane.nbytes

        def work():
            for index in range(200 + WARMUP + 1):
                _ = plane.copy()
                yield index

        case = harness.time_case(
            run, "the copy alone, off a held frame", work, warmup=WARMUP,
            unit="ms per copy", params={"bytes": int(nbytes)},
            note="what a microbenchmark of .copy() reports; the in-situ "
                 "cost is the decode+copy minus decode+view difference, "
                 "and is several times smaller because the decoder's "
                 "buffer is still hot")
        harness.report(case)
    finally:
        container.close()


def _budget(run: harness.Run, log_name: str | None) -> None:
    """Subtract the terms above out of one leg of one explorer log.

    Arithmetic over a log this file did not produce, printed rather than
    stored: it is a reading of a measurement, and storing it would make a
    later log's numbers look like they had been superseded when nothing had
    been re-measured.
    """
    if log_name is None:
        candidates = sorted(LOGS.glob("orchestrator-*.json"))
        chosen = None
        for path in reversed(candidates):
            data = json.loads(path.read_text(encoding="utf-8"))
            pre = data.get("topology", {}).get("preemption")
            if pre and pre.get("gui_cursor") \
                    and data["topology"]["playhead"] == "live":
                chosen = path
                break
        if chosen is None:
            run.note("no live --gui-cursor log found; budget not computed")
            print("\nno live --gui-cursor log to read a budget out of")
            return
    else:
        chosen = LOGS / log_name

    data = json.loads(chosen.read_text(encoding="utf-8"))
    trace = data["dispatch_trace"]
    print(f"\nbudget, read out of {chosen.name}")
    for entry in data["runs"]:
        walls = [w for w in entry["walls"] if w["what"] == "window covered"]
        if not walls or not entry["events"]:
            continue
        t0, t1 = entry["events"][0]["t"], walls[0]["t"]
        wall = walls[0]["wall_s"]
        seg = [e for e in trace if t0 <= e[0] <= t1]
        if not seg:
            continue
        fill = [e for e in seg if e[1] == "fill"]
        gui = [e for e in seg if e[1] == "gui"]
        fill_s, gui_s = sum(e[4] for e in fill) / 1000, sum(e[4] for e in gui) / 1000
        print(f"  {entry['label']:<20} wall={wall:5.2f}  "
              f"fill={fill_s:5.2f}s/{len(fill):>3}f  "
              f"gui={gui_s:5.2f}s/{len(gui):>3}f  "
              f"rest={wall - fill_s - gui_s:5.2f}s  "
              f"fill_ms/f={1000 * fill_s / max(1, len(fill)):5.2f}")
    run.note(f"budget read out of {chosen.name}")


def main() -> None:
    if not BIG.exists():
        print(f"missing {BIG}")
        return

    run = harness.Run(
        experiment="08-decode-budget",
        question="What is a filled window's wall made of, and how much of "
                 "it is not decode?")
    run.add_footage(BIG)

    print("decode terms (one reader, one thread, nothing held):")
    _decode_case(run, "decode only", None)
    _decode_case(run, "decode + luma view", _view)
    _decode_case(run, "decode + luma copy", _copy)
    _cold_copy_case(run)

    print("\ndispatcher terms (no decoder):")
    _graph_case(run)

    log = None
    if "--log" in sys.argv:
        log = sys.argv[sys.argv.index("--log") + 1]
    _budget(run, log)

    path = run.write()
    print(f"\nwrote {path.name}")


if __name__ == "__main__":
    main()

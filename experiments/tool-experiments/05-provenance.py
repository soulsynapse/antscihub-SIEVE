"""Is every stored value the one its own key says it is?

The other experiments here ask how expensive something is. None of them can
ask where a number came from, which is how a real defect survived four of
them: the drawing was writing the series, and a cost measurement cannot see
a provenance error because a value filed by the wrong producer costs exactly
what the right one costs.

The invariant fits in a sentence and it is the only one this file checks: **a
stored value must be reproducible from its own key.** A series is filed under
a step and a form. Take any covered row, recompute it with the step that key
names, and the answer must be the stored one. A producer that reads its
step twice — once to choose which inputs to gather and again to decide where
to file the answer — breaks it, and nothing else here would notice, because
the number is plausible and the key is real.

Three cases, in increasing nastiness. **Quiet**: one writer, nothing changing
underneath, which establishes that the invariant is checkable and that the
check itself is not the broken thing. **Switching underneath**: a writer that
reads its step, gathers, evaluates and files, while another thread swaps the
active step as fast as it can — the shape of the defect that was here.
**Reading while written**: a reader snapshotting a series a writer is
filling, because a numpy slice is a view and a reader that slices rather than
copies can see values and coverage from two different instants, which reads
as a real measurement of zero.

A pass is not a proof of thread safety. It is a regression test for specific
defects that were in this tree, run long enough to make their windows likely
rather than certain — and it is run against a deliberately broken writer
(`--broken`) as well, because a test that has never failed has no
demonstrated power.
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
from harness import FOOTAGE, Run  # noqa: E402

import series as series_mod  # noqa: E402
import tools as toolkit  # noqa: E402

harness.RESULTS = Path(__file__).resolve().parent / "results"

CUT = FOOTAGE / "derived" / "cut-crf18-intra.mp4"
CROP = (2144, 982, 1024, 1024)
HELD = 60
ROUNDS = 400
QUIET_ROUNDS = 120
SWITCH_PAUSE_S = 0.0004
TOLERANCE = 1e-4


def _resident(count: int):
    out = []
    with av.open(str(CUT)) as container:
        stream = container.streams.video[0]
        stream.thread_type = "AUTO"
        for frame in container.decode(stream):
            plane = frame.planes[0]
            arr = np.frombuffer(plane, dtype=np.uint8)
            arr = arr[: frame.height * plane.line_size]
            arr = arr.reshape(frame.height, plane.line_size)[:, : frame.width]
            out.append(np.ascontiguousarray(arr))
            if len(out) >= count:
                break
    return out


class Rig:
    """The smallest thing that can hold the defect, and the fix.

    Mirrors the explorer's rig in the one respect that matters: a mutable
    active step that one thread swaps while another produces. The correct
    writer reads it once and threads it through; `--broken` reads it again
    after gathering, which is how it used to be.
    """

    def __init__(self, pts, makers):
        self.makers = makers
        self.names = list(makers)
        self.name = self.names[0]
        self.tool = makers[self.name]()
        self.tools = {self.tool.key(): self.tool}
        self.series: dict[str, series_mod.Series] = {}
        self.pts = pts
        self.lock = threading.RLock()

    def use(self, name: str) -> None:
        self.name = name
        tool = self.makers[name]()
        with self.lock:
            self.tools.setdefault(tool.key(), tool)
        self.tool = tool

    def series_for(self, tool) -> series_mod.Series:
        form = tool.form_for(CROP)
        key = f"{tool.key()}|{form.key()}"
        with self.lock:
            got = self.series.get(key)
            if got is None:
                got = self.series[key] = series_mod.Series(
                    source=CUT.name, tool_key=tool.key(),
                    form_key=form.key(), pts=self.pts, timebase="1/24000")
        return got


def verify(rig: Rig, frames) -> tuple[int, list[str]]:
    """Recompute every covered row with the step its key names."""
    checked, bad = 0, []
    for key, series in rig.series.items():
        tool = rig.tools.get(key.split("|")[0])
        if tool is None:
            bad.append(f"{key}: no step answers to this key")
            continue
        values, covered = series.snapshot(0, len(frames))
        for row in np.nonzero(covered)[0]:
            row = int(row)
            want = tool.needs(row)
            if min(want) < 0 or max(want) >= len(frames):
                continue
            expect = float(tool.reduce(
                tool.field({r: frames[r] for r in want}, row)))
            got = float(values[row])
            checked += 1
            if abs(expect - got) > TOLERANCE * max(1.0, abs(expect)):
                bad.append(f"{key} row {row}: stored {got:.6f}, its own step "
                           f"gives {expect:.6f}")
    return checked, bad


def writer(rig: Rig, frames, rounds: int, broken: bool,
           stop: threading.Event) -> None:
    for i in range(rounds):
        if stop.is_set():
            return
        tool = rig.tool                        # the one read
        row = 31 + (i % (len(frames) - 31))
        window = {r: frames[r] for r in tool.needs(row)}
        # the defect is *three independent reads* of one mutable field:
        # gather with what it was, compute with what it is now, file under
        # what it is by then. Collapsing them into a single re-read makes
        # the writer self-consistent and the test toothless, which is worth
        # a comment because that is exactly how this file was once wrong.
        field = (rig.tool if broken else tool).field(window, row)
        value = float((rig.tool if broken else tool).reduce(field))
        rig.series_for(rig.tool if broken else tool).put(row, value)


def switcher(rig: Rig, stop: threading.Event) -> None:
    i = 0
    while not stop.is_set():
        rig.use(rig.names[i % len(rig.names)])
        i += 1
        time.sleep(SWITCH_PAUSE_S)


def main() -> None:
    broken = "--broken" in sys.argv
    run = Run(
        experiment="05-provenance",
        question="Is every stored value reproducible from the key it is "
                 "filed under, including while the active step changes "
                 "underneath its producer?",
    )
    run.add_footage(CUT)
    run.note("the invariant: a value stored under a step and a form must "
             "equal what that step computes for that row. A cost experiment "
             "cannot see a violation, because a value filed by the wrong "
             "producer costs exactly what the right one costs.")
    if broken:
        run.note("RUN WITH --broken: the writer re-reads the active step "
                 "after gathering, which is the defect this test exists for. "
                 "A pass here would mean the test tests nothing.")

    frames = _resident(HELD)
    pts = np.arange(len(frames), dtype=np.int64) * 1000
    makers = {"absdiff": toolkit.absdiff, "dis": toolkit.dis_flow,
              "mhi-lag": toolkit.lag_mhi}
    results = []

    rig = Rig(pts, makers)
    writer(rig, frames, QUIET_ROUNDS, broken, threading.Event())
    results.append(("quiet, one writer", *verify(rig, frames)))

    rig = Rig(pts, makers)
    stop = threading.Event()
    swap = threading.Thread(target=switcher, args=(rig, stop), daemon=True)
    swap.start()
    writer(rig, frames, ROUNDS, broken, stop)
    stop.set()
    swap.join(timeout=2)
    results.append(("step switching underneath", *verify(rig, frames)))

    rig = Rig(pts, makers)
    stop = threading.Event()
    torn: list[str] = []

    def reader():
        target = rig.series_for(rig.tool)
        while not stop.is_set():
            values, covered = target.snapshot(0, len(frames))
            if len(values) != len(covered):
                torn.append("snapshot returned mismatched lengths")
            elif covered.any() and not np.isfinite(values[covered]).all():
                torn.append("a covered row holds a non-finite value")
    rd = threading.Thread(target=reader, daemon=True)
    rd.start()
    writer(rig, frames, ROUNDS, broken, stop)
    stop.set()
    rd.join(timeout=2)
    checked, bad = verify(rig, frames)
    results.append(("reading while written", checked, bad + torn))

    ok = True
    print(f"{'case':<30} {'rows checked':>13}  verdict")
    for label, checked, bad in results:
        ok = ok and not bad
        print(f"{label:<30} {checked:>13}  "
              f"{'ok' if not bad else f'FAIL ({len(bad)})'}")
        for line in bad[:4]:
            print(f"    {line}")
        run.note(f"{label}: {checked} rows recomputed from their key, "
                 f"{len(bad)} disagreed"
                 + ("; first: " + bad[0] if bad else ""))
    print("\nPASS" if ok else "\nFAIL")
    if broken and ok:
        print("the --broken writer did not trip the check: the window was "
              "missed rather than absent. Raise ROUNDS and run again.")
    path = run.write()
    print(f"wrote {path}")


if __name__ == "__main__":
    main()

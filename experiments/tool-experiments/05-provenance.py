"""Is every stored value the one its own key says it is?

Every experiment in this folder so far asks how expensive something is. None
asks where a number came from, which is how a real defect survived four of
them: the display was writing the series, and a cost measurement cannot see
a provenance error because the wrong number costs exactly what the right one
does.

The invariant is small enough to state in a sentence and it is the only one
that matters here: **a stored value must be reproducible from its own key.**
A series is filed under (tool, form). Take any covered row, recompute it
with the tool that key names, and the answer must be the stored one. If a
producer ever read the rig's tool twice — once to choose which frames to
gather and again to decide where to file the answer — this fails, and
nothing else in the folder would notice, because the number is plausible and
the key is real.

Three cases, in increasing nastiness:

1. **Quiet.** One writer, nothing changing underneath. Establishes that the
   invariant is checkable at all and that the check itself is not the thing
   that is broken.

2. **Switching underneath.** A writer loop that reads the tool, gathers,
   evaluates and files — while another thread swaps the active tool as fast
   as it can. This is the shape of the bug that was here: on the fill thread
   with the user changing tools. It should be impossible to produce a value
   filed under a tool that did not compute it, and before the fix it was
   routine.

3. **Reading while written.** A reader taking snapshots of a series a writer
   is filling. A numpy slice is a view, so a reader that slices rather than
   copies can see a values array and a coverage array from two different
   instants — a row marked covered whose value has not landed yet. That
   reads as a real measurement of zero.

A pass here is not a proof of thread safety; it is a regression test for
three specific defects that were in this tree, run for long enough to make
their windows likely rather than certain.
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

import forms  # noqa: E402
import series as series_mod  # noqa: E402
import tools as toolkit  # noqa: E402

harness.RESULTS = Path(__file__).resolve().parent / "results"

CUT = FOOTAGE / "derived" / "cut-crf18-intra.mp4"
HELD = 60
ROUNDS = 400
CROP = (2144, 982, 1024, 1024)


def _frames(count: int):
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

    Mirrors the explorer's ToolRig in the one respect that matters: a
    mutable `tool` that a GUI thread swaps while a worker produces. The
    worker is written the correct way — one read, threaded through — and
    `--broken` runs it the way it used to be, so the test can be shown to
    fail against the defect rather than merely passing against the fix.
    """

    def __init__(self, pts, makers):
        self.makers = makers
        self.names = list(makers)
        self.name = self.names[0]
        self.tool = makers[self.name]()
        self.tools: dict[str, object] = {self.tool.key(): self.tool}
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
                    source=CUT.name, tool_key=tool.key(), form_key=form.key(),
                    pts=self.pts, timebase="1/24000")
        return got


def verify(rig: Rig, frames) -> tuple[int, list[str]]:
    """Recompute every covered row from the tool its key names."""
    checked, bad = 0, []
    for key, series in rig.series.items():
        tool_key = key.split("|")[0]
        tool = rig.tools.get(tool_key)
        if tool is None:
            bad.append(f"{key}: no tool answers to this key")
            continue
        values, covered = series.snapshot(0, len(frames))
        for row in np.nonzero(covered)[0]:
            row = int(row)
            want = tool.needs(row)
            if min(want) < 0 or max(want) >= len(frames):
                continue
            field = tool.field({r: frames[r] for r in want}, row)
            expect = float(tool.reduce(field))
            got = float(values[row])
            checked += 1
            if abs(expect - got) > 1e-4 * max(1.0, abs(expect)):
                bad.append(f"{key} row {row}: stored {got:.6f}, "
                           f"its own tool gives {expect:.6f}")
    return checked, bad


def writer(rig: Rig, frames, rounds: int, broken: bool, stop: threading.Event):
    for i in range(rounds):
        if stop.is_set():
            return
        tool = rig.tool                      # the one read
        row = 31 + (i % (len(frames) - 31))
        want = tool.needs(row)
        got = {r: frames[r] for r in want}
        field = (rig.tool if broken else tool).field(got, row)
        value = float((rig.tool if broken else tool).reduce(field))
        series = rig.series_for(rig.tool if broken else tool)
        series.put(row, value)


def switcher(rig: Rig, stop: threading.Event):
    i = 0
    while not stop.is_set():
        rig.use(rig.names[i % len(rig.names)])
        i += 1
        time.sleep(0.0004)


def main() -> None:
    broken = "--broken" in sys.argv
    run = Run(
        experiment="05-provenance",
        question="Is every stored value reproducible from the key it is "
                 "filed under, including while the tool changes underneath?",
    )
    run.add_footage(CUT)
    run.note("the invariant: a value stored under (tool, form) must equal "
             "what that tool computes for that row. A cost experiment cannot "
             "see a violation, because a value filed under the wrong tool "
             "costs exactly what the right one costs.")
    if broken:
        run.note("RUN WITH --broken: the writer re-reads the rig's tool after "
                 "gathering, which is the defect this test exists for. A pass "
                 "here would mean the test is not testing anything.")

    frames = _frames(HELD)
    pts = np.arange(len(frames), dtype=np.int64) * 1000
    makers = {"absdiff": toolkit.absdiff, "dis": toolkit.dis_flow,
              "mhi-lag": toolkit.lag_mhi}
    results = []

    # 1 ── quiet
    rig = Rig(pts, makers)
    stop = threading.Event()
    writer(rig, frames, 120, broken, stop)
    checked, bad = verify(rig, frames)
    results.append(("quiet, one writer", checked, bad))

    # 2 ── the tool changing underneath the writer
    rig = Rig(pts, makers)
    stop = threading.Event()
    swap = threading.Thread(target=switcher, args=(rig, stop), daemon=True)
    swap.start()
    writer(rig, frames, ROUNDS, broken, stop)
    stop.set()
    swap.join(timeout=2)
    checked, bad = verify(rig, frames)
    results.append(("tool switching underneath", checked, bad))

    # 3 ── a reader taking snapshots while a writer fills
    rig = Rig(pts, makers)
    stop = threading.Event()
    torn: list[str] = []

    def reader():
        target = rig.series_for(rig.tool)
        while not stop.is_set():
            values, covered = target.snapshot(0, len(frames))
            if len(values) != len(covered):
                torn.append("snapshot returned mismatched lengths")
            # a row marked covered whose value never landed reads as a
            # real measurement of zero, which is the failure mode coverage
            # exists to prevent
            if covered.any() and not np.isfinite(values[covered]).all():
                torn.append("covered row holds a non-finite value")
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
        verdict = "ok" if not bad else f"FAIL ({len(bad)})"
        ok = ok and not bad
        print(f"{label:<30} {checked:>13}  {verdict}")
        for line in bad[:4]:
            print(f"    {line}")
        run.note(f"{label}: {checked} rows recomputed from their key, "
                 f"{len(bad)} disagreed"
                 + ("; first: " + bad[0] if bad else ""))
    print("\nPASS" if ok else "\nFAIL")
    if broken and ok:
        print("the --broken writer did not trip the check: the race window "
              "was missed, not absent. Raise ROUNDS and run again.")
    path = run.write()
    print(f"wrote {path}")


if __name__ == "__main__":
    main()

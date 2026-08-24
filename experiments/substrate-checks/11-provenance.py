"""Is every stored value the one its own key says it is?

The invariant `experiments/tool-experiments/05-provenance.py` established, run
against `src/sieve` now that something in it records a value. Until
`sieve.analysis.record` landed there was nothing to check: ADR-0005 was the one
settled Substrate decision with no code, so the port had stores and declarations
and a session and nothing that wrote a number down.

**The invariant fits in a sentence and it is the only one here: a stored value
must be reproducible from its own key.** A series is filed under a step and a
form. Take any covered row, recompute it with the step that key names, and the
answer must be the stored one.

Why it needs its own file, when four cost experiments ran over the defect it
catches without seeing it: **a value filed by the wrong producer costs exactly
what the right one costs.** No timing instrument can see a provenance error. The
number is plausible, the key is real, and the only thing wrong is the
relationship between them. What found it in the tool folder was a question about
shape rather than about speed, and what keeps it found is this.

The defect is specific and it is easy to write. A producer that reads the active
step *twice* — once to decide which inputs to gather, once to decide where to
file the answer — writes a value computed with one step under the key of another
whenever the two reads straddle a change. `sieve.session.Session.active()` exists
to make that read once and hand it over; `--broken` reaches for the live set
instead, which is how it used to be.

Five cases, in increasing nastiness.

**quiet** — one fill, nothing changing underneath. Establishes that the
invariant is checkable at all and that the checker is not itself the broken
thing.

**warm-up** — a step whose oldest input sits outside the window has no honest
value at the window's first rows, and there must be no value there rather than
one computed from what happened to be resident.

**switching** — a fill running while another thread swaps the session's active
step as fast as it can. The shape of the defect that was in this tree. This is
the case `--broken` fails.

**reading** — a reader snapshotting a series while a fill writes it. A numpy
slice is a view, and a reader that slices rather than copies sees values and
coverage from two different instants, which reads as a real measurement.

**persisted** — a series written, read back, and re-verified against the step
its sidecar names. A key that survives a round trip through a filename and then
cannot be checked is a key that has stopped meaning anything.

A pass is not a proof of thread safety. It is a regression test for a specific
defect that was in this tree, run long enough to make its window likely rather
than certain, and run against a deliberately broken producer as well — because a
test that has never failed has no demonstrated power.

Run:
    uv run --group experiments python experiments/substrate-checks/11-provenance.py
    uv run --group experiments python experiments/substrate-checks/11-provenance.py --broken
"""

from __future__ import annotations

import sys
import tempfile
import threading
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "decode-experiments"))
import harness  # noqa: E402
from harness import Run  # noqa: E402

from sieve.analysis import record as record_mod  # noqa: E402
from sieve.analysis.record import Recorder  # noqa: E402
from sieve.analysis.series import Series  # noqa: E402
from sieve.analysis.tool import Tool, analysis_form  # noqa: E402
from sieve.decode import fake as fake_mod  # noqa: E402
from sieve.decode.fake import FakeRoute  # noqa: E402
from sieve.session.session import Session  # noqa: E402

harness.RESULTS = Path(__file__).resolve().parent / "results"

ROWS = 960
CHUNK = 96
WINDOW = 288
CROP = (0, 0, 32, 24)
TOLERANCE = 1e-4

#: A holder the broken producer reaches for, standing in for the session's own
#: mutable set of active steps. The correct producer never looks at it.
LIVE: dict = {"active": []}


def mean_tool() -> Tool:
    return Tool(name="absdiff", form_for=analysis_form("gray"), offsets=(-1, 0),
                field=lambda frames, row: cv2.absdiff(frames[row],
                                                      frames[row - 1]),
                reduce=lambda field: float(np.mean(field)),
                params={"reduce": "mean"})


def peak_tool() -> Tool:
    return Tool(name="absdiff", form_for=analysis_form("gray"), offsets=(-1, 0),
                field=lambda frames, row: cv2.absdiff(frames[row],
                                                      frames[row - 1]),
                reduce=lambda field: float(np.max(field)),
                params={"reduce": "peak"})


def reading_live(self, active, row, resident) -> int:
    """`admitted` as it used to be: gather by one read, file by another.

    Kept here as the thing being argued against, and it is genuinely the
    tidier-looking version — one fewer argument to thread through, and the
    producer always files under "the current step", which sounds like exactly
    what it should do. What it does when the step changes between the gather
    and the file is write a number computed with one step under the key of
    another, and cost exactly what the right answer costs.
    """
    written = 0
    for tool, form in active:
        for position in Recorder._positions_ready(
                tool, form, row, resident, len(self.table.pts)):
            frames = {need: resident.get(form.key(), need)
                      for need in tool.needs(position)}
            if any(frame is None for frame in frames.values()):
                continue
            value = tool.reduce(tool.field(frames, position))
            # the second read: whatever is active *now* decides the key
            current = LIVE["active"] or [(tool, form)]
            filing_tool, filing_form = current[0]
            series = self.series_for(filing_tool, filing_form)
            if series.get(position) is None:
                series.put(position, float(value))
                written += 1
    self.written += written
    return written


def build(root: Path, tool: Tool) -> tuple[Session, FakeRoute]:
    table = fake_mod.table(ROWS)
    route = FakeRoute(table)
    session = Session(root / "src.mp4", root / "derived", route=route,
                      budget_bytes=800 * 64 * 48, window_rows=WINDOW,
                      rows_per_chunk=CHUNK)
    session.crop = CROP
    session.tools = [tool]
    LIVE["active"] = session.active()
    return session, route


def verify(session: Session, resident) -> tuple[int, list[str]]:
    """Recompute every covered row with the step its own key names."""
    checked, bad = 0, []
    answers = session.recorder.tools_by_key(session.active())
    for key, series in session.recorder.series().items():
        tool = answers.get(key)
        if tool is None:
            bad.append(f"{key}: no active step answers to this key")
            continue
        form = tool.form_for(session.crop)
        for row in range(len(series.values)):
            stored = series.get(row)
            if stored is None:
                continue
            frames = {need: resident.get(form.key(), need)
                      for need in tool.needs(row)}
            if any(frame is None for frame in frames.values()):
                continue      # evicted since; nothing to recompute against
            again = float(tool.reduce(tool.field(frames, row)))
            checked += 1
            if abs(again - stored) > TOLERANCE:
                bad.append(f"{key} row {row}: stored {stored:.6f}, "
                           f"recomputes to {again:.6f}")
                if len(bad) >= 6:
                    return checked, bad
    return checked, bad


def case_quiet(run: Run, root: Path) -> tuple[str, int, list[str]]:
    session, _ = build(root / "quiet", mean_tool())
    low, high = session.land(200)
    session.frontier.wait(timeout=60)
    checked, bad = verify(session, session.resident)
    if not checked:
        bad.append("nothing was recorded, so nothing was checked")
    run.note(f"quiet: {checked} rows recomputed from their key over "
             f"{low}..{high}, {session.recorder.written} written")
    session.close()
    return "quiet (one writer, nothing moving)", checked, bad


def case_warmup(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    session, _ = build(root / "warmup", mean_tool())
    low, high = session.land(200)
    session.frontier.wait(timeout=60)
    series = next(iter(session.recorder.series().values()))

    # the step admits (-1, 0), so the window's first row has an input that was
    # never in the window. There must be no value there rather than one
    # computed from whatever happened to be resident.
    if series.get(low) is not None:
        bad.append(f"row {low} has a value, though its input at {low - 1} is "
                   "outside the window that was filled")
    if series.get(low + 1) is None:
        bad.append(f"row {low + 1} has no value, though both its inputs "
                   "landed")
    boundary = series.first_honest(low, mean_tool().reach)
    if boundary != low + 1:
        bad.append(f"first_honest({low}, 1) said {boundary}")
    covered = series.runs(low, high)
    if covered != [(low + 1, high)]:
        bad.append(f"the covered run is {covered}, not one stretch from the "
                   "first honest row to the end")
    run.note(f"warm-up: {covered} covered of {low}..{high} — the first row's "
             "input was never admitted, so it has no value rather than a "
             "wrong one")
    session.close()
    return "warm-up (no value beats a guess)", high - low, bad


def case_switching(run: Run, root: Path) -> tuple[str, int, list[str]]:
    """A fill running while the active step is swapped underneath it."""
    session, _ = build(root / "switching", mean_tool())
    other = peak_tool()
    stop = threading.Event()

    def churn():
        pair = [session.active(), [(other, other.form_for(session.crop))]]
        index = 0
        while not stop.is_set():
            LIVE["active"] = pair[index % 2]
            index += 1
            time.sleep(0.0004)

    swapper = threading.Thread(target=churn, daemon=True)
    swapper.start()
    low, high = session.land(200)
    session.frontier.wait(timeout=60)
    stop.set()
    swapper.join(timeout=2)
    LIVE["active"] = session.active()

    checked, bad = verify(session, session.resident)
    keys = sorted(session.recorder.series())
    if len(keys) > 1:
        bad.append(f"one fill produced {len(keys)} series: {keys}")
    run.note(f"switching: {checked} rows recomputed while the active step was "
             f"swapped throughout; series written: {keys}")
    session.close()
    return "switching (the step moved underneath)", checked, bad


def case_reading(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    session, _ = build(root / "reading", mean_tool())
    stop = threading.Event()
    torn: list[str] = []

    def reader():
        while not stop.is_set():
            for series in session.recorder.series().values():
                values, covered = series.snapshot(0, ROWS)
                if len(values) != len(covered):
                    torn.append("snapshot lengths disagree")
                elif covered.any() and not np.isfinite(values[covered]).all():
                    torn.append("a covered row holds a non-finite value")

    watcher = threading.Thread(target=reader, daemon=True)
    watcher.start()
    session.land(200)
    session.frontier.wait(timeout=60)
    stop.set()
    watcher.join(timeout=2)

    checked, found = verify(session, session.resident)
    bad += found + torn
    run.note(f"reading: {checked} rows verified with a reader snapshotting "
             "throughout")
    session.close()
    return "reading (snapshot while written)", checked, bad


def case_persisted(run: Run, root: Path) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    session, _ = build(root / "persisted", mean_tool())
    session.land(200)
    session.frontier.wait(timeout=60)
    written = session.recorder.save()
    if not written:
        bad.append("nothing was written to disk")
        session.close()
        return "persisted (survives the round trip)", 0, bad

    tool = mean_tool()
    form = tool.form_for(session.crop)
    checked = 0
    for path in written:
        back = Series.load(path)
        if back.tool_key != tool.key() or back.form_key != form.key():
            bad.append(f"{path.name} came back as {back.key!r}")
            continue
        for row in range(len(back.values)):
            stored = back.get(row)
            if stored is None:
                continue
            frames = {need: session.resident.get(form.key(), need)
                      for need in tool.needs(row)}
            if any(frame is None for frame in frames.values()):
                continue
            again = float(tool.reduce(tool.field(frames, row)))
            checked += 1
            if abs(again - stored) > TOLERANCE:
                bad.append(f"{path.name} row {row}: {stored} vs {again}")
                break
    run.note(f"persisted: {checked} rows verified after a round trip through "
             f"{written[0].name}")
    session.close()
    return "persisted (survives the round trip)", checked, bad


def main() -> None:
    broken = "--broken" in sys.argv
    if broken:
        record_mod.Recorder.admitted = reading_live

    run = Run(
        experiment="provenance" + ("-broken" if broken else ""),
        question="Is every value src/sieve stores reproducible from the key "
                 "it is filed under?",
    )
    run.note("no footage: provenance is about which step a number came from, "
             "and the fake route's frames are as good a workload as any")
    if broken:
        run.note("RUN WITH --broken: the producer reads the active step again "
                 "after gathering, which is how it used to be. `switching` is "
                 "expected to FAIL.")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        results = [
            case_quiet(run, root),
            case_warmup(run, root),
            case_switching(run, root),
            case_reading(run, root),
            case_persisted(run, root),
        ]

    ok = True
    print(f"{'case':<40} {'checked':>9}  verdict")
    for label, checked, bad in results:
        ok = ok and not bad
        print(f"{label:<40} {checked:>9}  "
              f"{'ok' if not bad else f'FAIL ({len(bad)})'}")
        for line in bad[:4]:
            print(f"    {line}")
        run.note(f"{label}: {checked} checked, {len(bad)} disagreed"
                 + ("; first: " + bad[0] if bad else ""))

    print()
    for line in run.notes:
        print(f"  · {line}")

    print("\nPASS" if ok else "\nFAIL")
    if broken and ok:
        print("the --broken producer did not trip the check: the window was "
              "missed rather than absent. Raise the churn and run again.")
    path = run.write()
    print(f"wrote {path}")


if __name__ == "__main__":
    main()

"""The port, put through what the explorer was put through, on the real file.

The gate `docs/archive/2026.08-substrate-port.md` owed for P7, and the only one that can
catch a regression the fake route structurally cannot see. Everything else in
this folder checks a property against synthetic frames; this drives
`src/sieve/` over the 5.3K source and sets the numbers beside the ones the
explorer produced on the same footage.

**It is a different program and says so.** The storage experiments measured
strategies against each other inside one file; this measures the ported
substrate as it actually runs, through `Session`. A comparison that pretended
the two were the same run would be worse than one that admits they are not, so
the explorer's figures are *read out of its committed result files* rather than
written down here — a later measurement supersedes them by being committed
beside them, and nothing in this docstring can go stale.

**What is expected, from the plan:** parity at the window tier and a difference
at the miss. The window keeps the wipe `02-form-derivation.py` gave it, so a
fill that decodes the same rows in the same order should cost what it cost. The
miss is where the port deliberately diverges: the explorer blocks on a scrub
into unfilled ground and the ladder does not, so what was a stall is a hold.
That is a change in *behaviour* and not an improvement in speed, and reporting
it as a faster number would be a lie about which thing got better.

Four measurements.

**region** — a cold 300-frame region, a fill running, and a same-seed scripted
scrub over it, which is `01-time-to-tunable.py`'s shape. Set beside that file's
`lazy-near-playhead`, which is the strategy this substrate implements.

**fill** — how long the frontier takes to cover the region, against the same
file's recorded completion.

**miss** — what a scrub into unfilled ground costs. Against `cold`, which is
what paying the original's random-access price per fetch looks like.

**build** — the proxy builder over a region with the real launcher, timed
between segment arrivals, against `06-build-order.py`'s `batch=4`.

Nothing here asserts and nothing passes or fails: these are costs, and ADR-0008
is explicit that a cost is reported and never held under a target. What would
be a defect is a *window* number that moved without a reason, and the reason
would be in the notes, so the reading is left to whoever reads it.

Run:
    uv run --group experiments python experiments/substrate-checks/10-parity.py
"""

from __future__ import annotations

import glob
import json
import random
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "decode-experiments"))
import harness  # noqa: E402
from harness import FOOTAGE, Run, quantiles  # noqa: E402

from sieve.analysis.tool import Tool, analysis_form  # noqa: E402
from sieve.frame import FrameTable, Shape  # noqa: E402
from sieve.session.session import Session  # noqa: E402
from sieve.store.build import BATCH, ProxyBuilder  # noqa: E402
from sieve.store.build import FFmpegLauncher  # noqa: E402
from sieve.store.spans import SpanStore  # noqa: E402

harness.RESULTS = Path(__file__).resolve().parent / "results"
EXPLORER = Path(__file__).resolve().parents[1] / "storage-experiments" / "results"

BIG = FOOTAGE / "GX010047c2_02_17_26.MP4"
#: the region `01-time-to-tunable.py` used, so the two are over the same ground
BASE_ROW = 1439
REGION = 300
CROP = (2144, 982, 1024, 1024)
FETCHES = 100
SEED = 20260821          #: the explorer's scripted scrub is same-seed; so is this
SEGMENTS = 20            #: the region `06-build-order.py` built
SEG_ROWS = 96


def committed(prefix: str) -> dict:
    """The newest committed result for one storage experiment, or `{}`.

    Read rather than restated. A figure written into this file would be one
    that could not be superseded by re-running the experiment, which is the
    whole arrangement `experiments/` is built on.
    """
    found = sorted(glob.glob(str(EXPLORER / f"{prefix}-*.json")))
    if not found:
        return {}
    return json.loads(Path(found[-1]).read_text(encoding="utf-8"))


def case_of(document: dict, name: str) -> dict | None:
    for case in document.get("cases", []):
        if case["name"] == name:
            return case
    return None


def p50_of(case: dict | None) -> float | None:
    if not case or not case.get("samples_ms"):
        return None
    return quantiles(case["samples_ms"])["p50"]


def beside(run: Run, label: str, ours: float | None, theirs: float | None,
           unit: str, reading: str) -> None:
    """One line of the comparison, printed and kept."""
    def show(value):
        return "—" if value is None else f"{value:9.2f}"
    line = (f"{label:<28} {show(ours)}  {show(theirs)}   {unit}")
    print(f"  {line}")
    run.note(f"{label}: src/sieve {show(ours).strip()} vs explorer "
             f"{show(theirs).strip()} {unit} — {reading}")


def session_over(root: Path, table: FrameTable, shape: Shape) -> Session:
    session = Session(BIG, root, budget_bytes=1_200_000_000,
                      window_rows=REGION, rows_per_chunk=SEG_ROWS)
    session.crop = CROP
    session.tools = [Tool(name="absdiff", form_for=analysis_form("gray"),
                          offsets=(-1, 0), field=lambda f, r: None)]
    return session


def measure_region(run: Run, table: FrameTable, shape: Shape) -> None:
    """A cold region, a fill, and a scripted scrub over it."""
    exp01 = committed("01-time-to-tunable")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        session = session_over(root, table, shape)
        started = time.perf_counter()
        low, high = session.land(BASE_ROW + REGION // 2)
        covered_at = None

        rng = random.Random(SEED)
        latencies: list[float] = []
        tiers: dict[str, int] = {}
        for _ in range(FETCHES):
            row = rng.randrange(low, high)
            begin = time.perf_counter()
            served = session.serve(row, task="drag")
            latencies.append((time.perf_counter() - begin) * 1000)
            tiers[served.tier] = tiers.get(served.tier, 0) + 1
            # Noticed *during* the scrub and not waited for after it. A first
            # version waited on the frontier once the hundred fetches were
            # done, which cannot report less than the sleeps add up to — five
            # seconds, whatever the fill actually did. The number it printed
            # was a floor wearing a measurement's label, and it was the one
            # number in this file the plan cares most about.
            if covered_at is None and session.frontier is not None \
                    and not session.frontier.running():
                covered_at = time.perf_counter() - started
            time.sleep(0.05)      # a hand, not a loop
        if session.frontier is not None:
            session.frontier.wait(timeout=180)
            if covered_at is None:
                covered_at = time.perf_counter() - started
        decoded = session.frontier.from_route if session.frontier else 0
        # which decoder actually did the filling. Without this the fill
        # number is a claim with no mechanism behind it, and the gap
        # against the explorer is large enough that "we are faster" is
        # not a reading anybody should accept on its own.
        verdict = getattr(session.route, "verdict", "sw")
        probed = dict(getattr(session.route, "measured_ms", {}))
        session.close()

    ours = quantiles(latencies)
    beside(run, "scrub, p50", ours["p50"],
           p50_of(case_of(exp01, "lazy-near-playhead")), "ms per fetch",
           "the strategy this substrate implements; both serve from memory")
    beside(run, "scrub, p95", ours["p95"], None, "ms per fetch",
           "kept because a p50 of nothing hides where the stalls were")
    beside(run, "fill over the region", covered_at * 1000 if covered_at else None,
           _fill_seconds(exp01) * 1000 if _fill_seconds(exp01) else None,
           "ms to cover 300",
           "the window tier, where the plan expects parity; both under a "
           "scripted scrub competing for the decoder")
    run.note(f"region: window {low}..{high}, {decoded} rows decoded, tiers "
             f"{tiers}")
    run.note(f"region: the fill ran on the {verdict!r} side of the probed "
             f"hybrid (seek race {probed}). The explorer filled with plain "
             "software PyAV, so a gap here is the routing decision P1 made "
             "showing up, and not the same work done faster.")
    print(f"  tiers served: {tiers}")


def _fill_seconds(document: dict) -> float | None:
    """The fill completion the explorer recorded, out of its own notes."""
    for note in document.get("notes", []):
        if "fill covered" in note and "complete at" in note:
            try:
                return float(note.split("complete at")[1].strip().rstrip("s"))
            except (IndexError, ValueError):
                return None
    return None


def measure_miss(run: Run, table: FrameTable, shape: Shape) -> None:
    """What a scrub into ground the fill has not reached costs."""
    exp01 = committed("01-time-to-tunable")
    with tempfile.TemporaryDirectory() as tmp:
        session = session_over(Path(tmp), table, shape)
        session.window = (BASE_ROW, BASE_ROW + REGION)   # a window, no fill
        rng = random.Random(SEED)
        latencies = []
        tiers: dict[str, int] = {}
        for _ in range(FETCHES):
            row = rng.randrange(BASE_ROW, BASE_ROW + REGION)
            begin = time.perf_counter()
            served = session.serve(row, task="drag")
            latencies.append((time.perf_counter() - begin) * 1000)
            tiers[served.tier] = tiers.get(served.tier, 0) + 1
        session.close()

    ours = quantiles(latencies)
    beside(run, "miss, p50", ours["p50"], p50_of(case_of(exp01, "cold")),
           "ms per fetch",
           "NOT a speedup: the explorer decodes and this holds, so the two "
           "are different acts and only one of them shows a frame")
    run.note(f"miss: with no fill running the ladder served {tiers} — a hold "
             "shows the picture already up and lets the fill overtake it, "
             "which is a behaviour change and not a faster decode")
    print(f"  tiers served: {tiers}")


def measure_build(run: Run, table: FrameTable, shape: Shape) -> None:
    """The proxy builder over a region, with the real launcher."""
    exp06 = committed("06-build-order")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        store = SpanStore(root / "proxy", table)
        (root / "proxy").mkdir(parents=True, exist_ok=True)
        launcher = FFmpegLauncher(BIG, shape, len(table), SEG_ROWS)
        builder = ProxyBuilder(store, table, launcher.form().key(), launcher,
                               segments=SEGMENTS, rows_per_segment=SEG_ROWS,
                               batch=BATCH)
        arrivals: list[float] = []
        seen = 0
        started = time.perf_counter()
        while not builder.done() and time.perf_counter() - started < 300:
            builder.tick(fill_running=False)
            now = len(store.coverage)
            if now > seen:
                arrivals.extend([(time.perf_counter() - started) * 1000]
                                * (now - seen))
                seen = now
            time.sleep(0.05)
        builder.stop()
        store.close()

    gaps = [b - a for a, b in zip(arrivals, arrivals[1:])] or [0.0]
    ours = quantiles(gaps)
    beside(run, "proxy, between segments", ours["p50"],
           p50_of(case_of(exp06, "batch=4")), "ms per segment",
           "the same batch size; the explorer's run was at normal process "
           "priority and this one is below-normal, so the ratio transfers "
           "and the absolute does not")
    run.note(f"build: {seen} of {SEGMENTS} segments in "
             f"{(arrivals[-1] if arrivals else 0):.0f} ms")


def main() -> None:
    run = Run(
        experiment="parity",
        question="Put through what the explorer was put through, does the "
                 "ported substrate cost what the explorer cost?",
    )
    if not BIG.exists():
        print(f"{BIG.name} absent; nothing to compare")
        run.note("skipped: the source is not here")
        run.write()
        return
    run.add_footage(BIG)
    run.note("a different program from the storage experiments and compared "
             "anyway: they measured strategies against each other inside one "
             "file, this measures the substrate as it runs. The explorer's "
             "figures are read from its committed results, never restated.")

    table = FrameTable.cached(BIG)
    shape = Shape.read(BIG)

    print(f"{'measurement':<30} {'src/sieve':>9}  {'explorer':>9}   unit")
    measure_region(run, table, shape)
    measure_miss(run, table, shape)
    measure_build(run, table, shape)

    print()
    for line in run.notes:
        print(f"  · {line}")
    path = run.write()
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()

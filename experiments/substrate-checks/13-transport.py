"""Does the playhead follow the clock, or the machine?

The transport's look is provisional and will be replaced by a designed strip.
This checks the part that must survive that, which is one sentence: **the
playhead follows a clock and the drawing follows the machine.**

It is the explorer's hardest-won lesson and it is easy to get wrong in the
tidiest possible way. A loop that advances one row per timer tick is shorter,
reads better, and plays the footage at whatever rate the machine can draw — so
the behaviour on screen runs slow whenever anything else is happening, and
nobody can tell whether they are watching slow ants or a busy computer. The
whole subject of this application is how fast things move, so a transport that
quietly restates the machine's load as the recording's rate is not a
performance problem, it is a measurement error with a picture on it.

Four cases, offscreen and without footage: a clock is not about pixels.

**rate** — over a wall-clock second the playhead advances by about the frame
rate, whatever the tick interval is.

**stall** — this is the one that matters. Nothing is served for a while, as
though the machine were busy elsewhere; when it comes back the playhead is
where the *recording* should be, not one row on from where it stopped. The
frames in between are reported as skipped rather than queued.

**wrap** — the loop returns to the window's first row and keeps its phase,
rather than restarting the clock and drifting.

**layout** — no size hints and `Ignored` policies, like everything else that
updates: the bottom pane's height is fixed and the strip that eventually lives
here must not argue with it.

`--broken` advances one row per tick, which is the version somebody writes
first.

Run:
    uv run --group experiments python experiments/substrate-checks/13-transport.py
    uv run --group experiments python experiments/substrate-checks/13-transport.py --broken
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QSizePolicy  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "decode-experiments"))
import harness  # noqa: E402
from harness import Run  # noqa: E402

from sieve.gui.view.transport import Transport  # noqa: E402
from sieve.gui.view.transport import view as transport_mod  # noqa: E402

harness.RESULTS = Path(__file__).resolve().parent / "results"

FIRST, LAST, FPS = 1000, 1300, 24.0


def one_per_tick(self) -> None:
    """The playhead as a counter rather than a clock.

    Kept here as the thing being argued against. It is shorter and it reads
    better, and what it does is play the recording at the rate the machine
    happens to manage — so a busy moment becomes slow behaviour on screen, and
    the one question this application exists to answer is quietly answered
    wrong.
    """
    span = self._last - self._first
    if span <= 0:
        return
    row = self._first + (self._row - self._first + 1) % span
    self._row = row
    self._draw_readout()
    self.update()
    self.wants.emit(row)


def spin(app, seconds: float) -> None:
    end = time.perf_counter() + seconds
    while time.perf_counter() < end:
        app.processEvents()
        time.sleep(0.002)


def case_rate(run: Run, app) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    transport = Transport()
    asked: list[int] = []
    transport.wants.connect(asked.append)
    transport.follow(FIRST, LAST, FPS)
    transport.play()
    spin(app, 1.0)
    transport.pause()

    if not 0.7 * FPS <= len(asked) <= 1.2 * FPS:
        bad.append(f"{len(asked)} rows asked for in a second at {FPS} fps")
    if any(not FIRST <= row < LAST for row in asked):
        bad.append("a row outside the window was asked for")
    run.note(f"rate: {len(asked)} rows in a wall-clock second at {FPS} fps")
    return "rate (the recording's, not the machine's)", len(asked), bad


def case_stall(run: Run, app) -> tuple[str, int, list[str]]:
    """The case the whole file is for."""
    bad: list[str] = []
    transport = Transport()
    asked: list[int] = []
    skipped: list[int] = []
    transport.wants.connect(asked.append)
    transport.skipped.connect(skipped.append)
    transport.follow(FIRST, LAST, FPS)
    transport.play()
    spin(app, 0.2)

    before = transport.at()
    # the machine is elsewhere: no events are processed at all for a while,
    # which is what a stall on the drawing thread actually looks like
    time.sleep(0.5)
    app.processEvents()
    after = transport.at()
    transport.pause()

    moved = (after - before) % (LAST - FIRST)
    expected = 0.5 * FPS
    if moved < expected * 0.6:
        bad.append(f"the playhead moved {moved} rows across a {expected:.0f}-row "
                   "stall; it is counting ticks rather than reading a clock")
    if not skipped:
        bad.append("frames were passed and none were reported skipped")
    run.note(f"stall: half a second with nothing served moved the playhead "
             f"{moved} rows (about {expected:.0f} at {FPS} fps), "
             f"{sum(skipped)} reported skipped")
    return "stall (the clock kept going)", moved, bad


def case_wrap(run: Run, app) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    transport = Transport()
    asked: list[int] = []
    transport.wants.connect(asked.append)
    # a short window, so a second of wall clock goes round it more than once
    transport.follow(FIRST, FIRST + 12, FPS)
    transport.play()
    spin(app, 1.0)
    transport.pause()

    if not asked:
        bad.append("nothing was asked for")
        return "wrap (round, and keeps its phase)", 0, bad
    if any(not FIRST <= row < FIRST + 12 for row in asked):
        outside = [r for r in asked if not FIRST <= r < FIRST + 12]
        bad.append(f"rows outside the window: {outside[:4]}")
    if len(set(asked)) < 8:
        bad.append(f"only {len(set(asked))} distinct rows over a window of 12")
    wrapped = sum(1 for a, b in zip(asked, asked[1:]) if b < a)
    if wrapped < 1:
        bad.append("the loop never came round")
    run.note(f"wrap: {len(asked)} requests over a 12-row window, "
             f"{wrapped} times round")
    return "wrap (round, and keeps its phase)", len(asked), bad


def case_layout(run: Run, app) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    transport = Transport()
    transport.follow(FIRST, LAST, FPS)
    policy = transport.sizePolicy()
    if policy.horizontalPolicy() != QSizePolicy.Policy.Ignored:
        bad.append(f"horizontal policy is {policy.horizontalPolicy()}")
    for label, hint in (("sizeHint", transport.sizeHint()),
                        ("minimumSizeHint", transport.minimumSizeHint())):
        if hint.isValid() and (hint.width() > 0 or hint.height() > 0):
            bad.append(f"{label} is {hint.width()}x{hint.height()}")
    run.note("layout: no hints, and the horizontal policy is Ignored — the "
             "pane's width is the user's, not the readout's")
    return "layout (no vote)", 3, bad


def main() -> None:
    broken = "--broken" in sys.argv
    if broken:
        transport_mod.Transport._advance = one_per_tick

    app = QApplication.instance() or QApplication([])
    run = Run(
        experiment="P8-transport" + ("-broken" if broken else ""),
        question="Does the playhead follow a clock, so the recording plays at "
                 "its own rate rather than the machine's?",
    )
    run.note("offscreen and without footage: a clock is not about pixels")
    if broken:
        run.note("RUN WITH --broken: the playhead advances one row per tick, "
                 "which is the version somebody writes first. `stall` is "
                 "expected to FAIL.")

    results = [
        case_rate(run, app),
        case_stall(run, app),
        case_wrap(run, app),
        case_layout(run, app),
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
        print("the --broken run tripped nothing: the substitution is not "
              "being reached and `stall` is not demonstrating what it claims.")
    path = run.write()
    print(f"wrote {path}")


if __name__ == "__main__":
    main()

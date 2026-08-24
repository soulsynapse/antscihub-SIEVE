"""Does the picture stay out of the layout, and cost one scale per frame?

P8 of `docs/substrate/port-plan.md`. The canvas is the first thing in the port
somebody can look at, and it is also the piece the freeze finding is most
specific about — because the thing that made the video visibly resize every few
seconds was not the decoder. It was the picture having an opinion about how big
the pane should be.

**Nothing that updates may participate in layout negotiation.** A pixmap's size
hint and a line of HUD text nudged the splitter between them, and the canvas
oscillated between two widths for a whole session while every store serve stayed
fast. Twelve reflows, and none of them anything to do with what SIEVE was
computing. The rule is the finding's; what is new is that it is checkable — a
widget either has hints or it does not, and that is a thing to assert rather
than a thing to remember.

**A frame is scaled once per frame, not once per paint.** A repaint is asked for
by anything: a window passing over this one, a sibling resizing, the compositor.
Rescaling a full-resolution crop on each is paint cost that grows with how busy
the *desktop* is rather than with what the application is doing, which is the
worst shape a cost can have because nothing in the application explains it.

Six cases, offscreen and without footage: what a widget tells a layout, and how
many times it scales, are not about pixels.

**layout** — no size hints, `Ignored` on both axes, and none of it moves when a
frame four times the widget's size is shown. This is the case `--broken` fails.

**scale-once** — one scale per frame, none per repaint, exactly one per resize.

**copy** — the widget owns what it draws. A `QImage` over a numpy buffer is a
view, and the buffer belongs to a store a fill thread is writing and an eviction
may take; the failure is a torn picture rather than a crash, and only sometimes.

**hold** — holding leaves the picture and the row alone, which is what the
ladder's last rung means.

**stand-in** — a frame shown for a row it is not is remembered as such, so
whether the picture is the answer is something the interface can say without
working it out again from the pixels.

**surface** — the reductions moved into `sieve.analysis.surface` still take a
series down to display width, because a strip is one column per pixel and
drawing every point of a covered timeline is the scatter the freeze hunt found.

`--broken` gives the widget the size hints it used to have.

Run:
    uv run --group experiments python experiments/substrate-checks/12-canvas.py
    uv run --group experiments python experiments/substrate-checks/12-canvas.py --broken
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np  # noqa: E402
from PySide6.QtCore import QSize  # noqa: E402
from PySide6.QtGui import QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication, QSizePolicy  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "decode-experiments"))
import harness  # noqa: E402
from harness import Run  # noqa: E402

from sieve.analysis.surface import to_columns  # noqa: E402
from sieve.gui.view.canvas import Canvas  # noqa: E402
from sieve.gui.view.canvas.video_canvas import VideoCanvas  # noqa: E402
from sieve.gui.view.canvas.video_canvas import view as canvas_mod  # noqa: E402

harness.RESULTS = Path(__file__).resolve().parent / "results"

WIDE, TALL = 400, 300


def opinionated_hint(self) -> QSize:
    """The hint the widget used to have: as big as the picture it holds.

    Kept here as the thing being argued against. It is the obvious one — a
    widget that knows how large its content is telling the layout so — and it
    is how the video came to be deciding the width of the pane it stood in.
    """
    if self._scaled is not None:
        return self._scaled.size()
    return QSize(1920, 1080)


def frame(width: int, height: int, value: int = 128) -> np.ndarray:
    array = np.full((height, width), value, dtype=np.uint8)
    array[:8, :8] = 255      # a corner to tell one frame from another
    return array


def case_layout(run: Run, app) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    video = VideoCanvas()
    video.resize(WIDE, TALL)

    policy = video.sizePolicy()
    if policy.horizontalPolicy() != QSizePolicy.Policy.Ignored:
        bad.append(f"horizontal policy is {policy.horizontalPolicy()}")
    if policy.verticalPolicy() != QSizePolicy.Policy.Ignored:
        bad.append(f"vertical policy is {policy.verticalPolicy()}")

    before = (video.sizeHint(), video.minimumSizeHint())
    # a frame four times the widget, which is the ordinary case: a 1024 crop
    # in a pane somebody dragged narrow
    video.show_frame(frame(WIDE * 4, TALL * 4))
    after = (video.sizeHint(), video.minimumSizeHint())

    for label, hint in (("sizeHint", after[0]),
                        ("minimumSizeHint", after[1])):
        if hint.isValid() and (hint.width() > 0 or hint.height() > 0):
            bad.append(f"{label} is {hint.width()}x{hint.height()}; a widget "
                       "that updates may not vote on the layout")
    if before != after:
        bad.append("showing a frame moved the hints")
    if video.minimumSize().width() or video.minimumSize().height():
        bad.append(f"a minimum size of {video.minimumSize()} is a floor the "
                   "pane cannot go below")
    run.note(f"layout: hints {after[0].width()}x{after[0].height()} with a "
             f"{WIDE * 4}x{TALL * 4} frame up, policies "
             f"{policy.horizontalPolicy().name}/"
             f"{policy.verticalPolicy().name}")
    return "layout (no vote, no hints)", 4, bad


def case_scale_once(run: Run, app) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    video = VideoCanvas()
    video.resize(WIDE, TALL)
    # shown, even offscreen: a widget that has never been shown is not handed
    # resize events on an explicit resize, so a check that only ever renders
    # into a pixmap measures a widget in a state the application never has it
    # in — and reports the geometry rule holding for the wrong reason.
    video.show()
    app.processEvents()
    video.show_frame(frame(1024, 1024))
    if video.scales != 1:
        bad.append(f"showing one frame scaled {video.scales} times")

    # settle first. An offscreen widget is handed its first resize event when
    # something first paints it, so a count taken before that attributes a
    # geometry change to the repaints — which is the check mismeasuring, not
    # the widget rescaling.
    target = QPixmap(video.size())
    video.render(target)
    app.processEvents()
    after_frame = video.scales

    for _ in range(20):
        video.render(target)
    if video.scales != after_frame:
        bad.append(f"20 repaints cost {video.scales - after_frame} scales; "
                   "a repaint is asked for by anything and must be a blit")

    video.resize(WIDE + 120, TALL + 90)
    app.processEvents()
    if video.scales != after_frame + 1:
        bad.append(f"a resize cost {video.scales - after_frame} scales, not "
                   "one")

    before = video.scales
    for index in range(10):
        video.show_frame(frame(1024, 1024, value=index * 20))
    if video.scales != before + 10:
        bad.append(f"ten frames cost {video.scales - before} scales")
    run.note(f"scale-once: {video.scales} scales for 11 frames, one resize "
             "and twenty repaints")
    return "scale-once (per frame, not per paint)", video.scales, bad


def case_copy(run: Run, app) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    video = VideoCanvas()
    video.resize(64, 64)
    source = frame(64, 64, value=10)
    video.show_frame(source)

    drawn = QPixmap(video.size())
    video.render(drawn)
    first = drawn.toImage().pixelColor(32, 32).value()

    # what a fill thread or an eviction does to a buffer a widget was handed
    source[:] = 240
    again = QPixmap(video.size())
    video.render(again)
    second = again.toImage().pixelColor(32, 32).value()

    if first != second:
        bad.append(f"the picture changed from {first} to {second} when the "
                   "array behind it was overwritten; the widget is drawing a "
                   "view of somebody else's buffer")
    run.note(f"copy: the drawn value stayed {first} after the source array was "
             "overwritten")
    return "copy (owns what it draws)", 2, bad


def case_hold(run: Run, app) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    video = VideoCanvas()
    video.resize(WIDE, TALL)
    video.show_frame(frame(128, 128, value=77), row=412)

    drawn = QPixmap(video.size())
    video.render(drawn)
    before = drawn.toImage().pixelColor(WIDE // 2, TALL // 2).value()
    scales = video.scales

    video.hold()
    after_pixmap = QPixmap(video.size())
    video.render(after_pixmap)
    after = after_pixmap.toImage().pixelColor(WIDE // 2, TALL // 2).value()

    if before != after:
        bad.append(f"holding changed the picture from {before} to {after}")
    if video.row() != 412:
        bad.append(f"holding moved the row to {video.row()}")
    if video.scales != scales:
        bad.append("holding cost a scale")
    if not video.has_frame():
        bad.append("holding lost the frame")
    run.note("hold: the picture, the row and the scale count all unchanged — "
             "which is what the ladder's last rung means")
    return "hold (nothing happens, on purpose)", 3, bad


def case_stand_in(run: Run, app) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    video = VideoCanvas()
    video.resize(WIDE, TALL)
    video.show_frame(frame(64, 64), row=100)
    if video.standing_in():
        bad.append("an exact frame reported standing in")
    video.show_frame(frame(64, 64), row=100, standing_in=True)
    if not video.standing_in():
        bad.append("a stand-in did not report itself")
    video.show_frame(frame(64, 64), row=101)
    if video.standing_in():
        bad.append("the stand-in flag survived the next exact frame")
    run.note("stand-in: whether the picture is the answer is remembered rather "
             "than re-derived from the pixels")
    return "stand-in (remembered, not re-derived)", 3, bad


def case_surface(run: Run, app) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    rows = 4000
    values = np.linspace(0, 1, rows, dtype=np.float32)
    covered = np.zeros(rows, dtype=bool)
    covered[500:3500] = True

    columns = to_columns(values, covered, 320)
    for name, array in columns.items():
        if len(array) != 320:
            bad.append(f"{name} came back {len(array)} long, not 320")
    if "covered" in columns and columns["covered"][0]:
        bad.append("a column with no covered rows under it reads as covered")
    if "covered" in columns and not columns["covered"][160]:
        bad.append("a column in the middle of the covered stretch reads as "
                   "uncovered")
    run.note(f"surface: {rows} rows reduced to 320 columns "
             f"({sorted(columns)}) — one per pixel, which is what a strip is")
    return "surface (reduced to display width)", len(columns), bad


def main() -> None:
    broken = "--broken" in sys.argv
    if broken:
        canvas_mod.VideoCanvas.sizeHint = opinionated_hint
        canvas_mod.VideoCanvas.minimumSizeHint = opinionated_hint

    app = QApplication.instance() or QApplication([])
    run = Run(
        experiment="P8-canvas" + ("-broken" if broken else ""),
        question="Does the picture stay out of the layout, and cost one scale "
                 "per frame rather than one per paint?",
    )
    run.note("offscreen and without footage: what a widget tells a layout, "
             "and how many times it scales, are not about pixels")
    if broken:
        run.note("RUN WITH --broken: the widget reports the size of the "
                 "picture it holds, which is the hint that had the video "
                 "deciding the width of its own pane. `layout` is expected "
                 "to FAIL.")

    results = [
        case_layout(run, app),
        case_scale_once(run, app),
        case_copy(run, app),
        case_hold(run, app),
        case_stand_in(run, app),
        case_surface(run, app),
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
              "being reached and `layout` is not demonstrating what it claims.")
    path = run.write()
    print(f"wrote {path}")


if __name__ == "__main__":
    main()

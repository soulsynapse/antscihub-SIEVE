"""Does a crop drawn on the stage come back as the crop that was kept?

T1's other half. `15-numberbox` checks one control alone and `14-crop` checks
the arithmetic alone; this checks the thing neither can, which is that the three
landed pieces close a loop. A hand drags a rectangle over a picture, something
clamps it into a legal crop, and the box and the four numbers both end up
showing *that* crop rather than the one that was drawn.

The failure this is really about has been paid for twice already in this tree: a
rule that lives in a comment has as many implementations as it has readers. The
overlay draws the set crop by mapping source pixels back to widget coordinates,
and the owner maps the other way; the moment those are two pieces of arithmetic
rather than one module read twice, the box sits a little off the crop it claims
to be — and nothing goes red, because both halves are individually plausible.

Five cases, offscreen. The mapping is restated here in plain arithmetic rather
than imported, which is the point: a check that called `crop.to_source` would
agree with the overlay by construction and prove only that one function equals
itself.

**stage** — the overlay follows `Canvas.staged` and matches its parent, because
an overlay sized to the pane before a resize draws the box where the picture is
no longer.

**maps** — a synthesised drag over a known stage arrives as widget coordinates
that map to the source rect worked out by hand.

**roundtrip** — the crop the owner settled on, drawn back by the overlay, is the
rectangle that was dragged, to within the rounding the clamp did. This is the
case `--broken` fails.

**gesture** — a click is not a drag, a drag off the picture stops at its edge,
and a refused drag says so rather than doing nothing.

**closes** — an overlay, four number boxes and a clamp wired as a pane will wire
them: a drag the clamp moves shows up in the boxes as the moved value, typing a
refused number leaves the accepted one on screen, and neither push provokes
another. The owner here is a dozen lines and lives in this file, because the
pane that will own both arrives with the tuning pane and this is what says the
pieces will compose when it does.

`--broken` gives `CropOverlay._box` its own scale arithmetic against its own
rect instead of `crop.to_placed` against the stage — which is the same drawing
worked out a second way, and is wrong by exactly the canvas margin and the
letterbox.

Run:
    uv run --group experiments python experiments/substrate-checks/16-overlay.py
    uv run --group experiments python experiments/substrate-checks/16-overlay.py --broken
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, QRect, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "decode-experiments"))
import harness  # noqa: E402
from harness import Run  # noqa: E402

from sieve.gui.primitives.number import NumberBox  # noqa: E402
from sieve.gui.view.canvas import overlay as overlay_mod  # noqa: E402
from sieve.gui.view.canvas.overlay import DRAG_MIN, CropOverlay, over  # noqa: E402
from sieve.gui.view.canvas.view import Canvas  # noqa: E402

harness.RESULTS = Path(__file__).resolve().parent / "results"

#: The source the cases pretend to be cropping, and the pane it is seen in.
#: Both arbitrary and both awkward on purpose — the pane's aspect is not the
#: source's, so a mapping that quietly used the widget rect is off by a
#: letterbox rather than off by nothing.
SOURCE_W, SOURCE_H = 1920, 1080
PANE_W, PANE_H = 900, 560

#: How far a redrawn box may sit from the rectangle that was dragged, in widget
#: pixels. Not zero, and the reason is not slack: the clamp snaps every edge
#: down to even *source* pixels, and one source pixel is more than one widget
#: pixel whenever the picture is shown smaller than it was recorded. Two
#: source pixels at this scale, rounded up.
SLACK = 3

#: The floor the restated clamp uses. Restated rather than imported for the
#: same reason the mapping is: a check that imported `crop.MINIMUM` would still
#: pass if the clamp stopped applying it.
MINIMUM = 64


def own_box(overlay: CropOverlay):
    """`_box` worked out a second time, from the wrong rectangle.

    The bug this file exists to catch, written the way it actually gets
    written: not as a mistake in the arithmetic, but as arithmetic that is
    correct about the widget when the picture is somewhere else in it.
    """
    crop = overlay.crop()
    frame = overlay._frame
    if crop is None or frame is None:
        return None
    scale_x = overlay.width() / frame[0]
    scale_y = overlay.height() / frame[1]
    x, y, w, h = crop
    return QRect(round(x * scale_x), round(y * scale_y),
                 max(1, round(w * scale_x)), max(1, round(h * scale_y)))


# -- the mapping and the clamp, restated -------------------------------------
def clamp(rect) -> tuple[int, int, int, int]:
    """A source rect made legal: on the frame, big enough, even. By hand."""
    x, y, w, h = (int(round(v)) for v in rect)
    x = max(0, min(x, SOURCE_W - MINIMUM))
    y = max(0, min(y, SOURCE_H - MINIMUM))
    w = max(MINIMUM, min(w, SOURCE_W - x))
    h = max(MINIMUM, min(h, SOURCE_H - y))
    return tuple(v - v % 2 for v in (x, y, w, h))


def to_source(drawn: QRect, stage: QRect) -> tuple[int, int, int, int]:
    """A widget rect over a placed picture, as a legal source crop. By hand."""
    scale_x = SOURCE_W / stage.width()
    scale_y = SOURCE_H / stage.height()
    return clamp((
        (drawn.x() - stage.x()) * scale_x, (drawn.y() - stage.y()) * scale_y,
        drawn.width() * scale_x, drawn.height() * scale_y))


def to_widget(rect, stage: QRect) -> QRect:
    """The other direction, by hand."""
    scale_x = stage.width() / SOURCE_W
    scale_y = stage.height() / SOURCE_H
    x, y, w, h = rect
    return QRect(round(stage.x() + x * scale_x), round(stage.y() + y * scale_y),
                 max(1, round(w * scale_x)), max(1, round(h * scale_y)))


# -- driving a hand ----------------------------------------------------------
def _send(app, widget, kind, point: QPoint, button=Qt.MouseButton.LeftButton):
    held = (Qt.MouseButton.LeftButton if kind is QMouseEvent.Type.MouseMove
            else button)
    app.sendEvent(widget, QMouseEvent(
        kind, QPointF(point), QPointF(point), button, held,
        Qt.KeyboardModifier.NoModifier))


def drag(app, widget, start: QPoint, end: QPoint) -> None:
    """Press, move once through the middle, move to the end, release.

    Two moves rather than one because a band that only ever saw its final
    position would pass a check that a band which never updates would also
    pass.
    """
    _send(app, widget, QMouseEvent.Type.MouseButtonPress, start)
    _send(app, widget, QMouseEvent.Type.MouseMove,
          QPoint((start.x() + end.x()) // 2, (start.y() + end.y()) // 2))
    _send(app, widget, QMouseEvent.Type.MouseMove, end)
    _send(app, widget, QMouseEvent.Type.MouseButtonRelease, end)


def relaid(canvas, app, width: int, height: int) -> None:
    """Resize and let the event through.

    Qt does not deliver a resize event to a widget that has never been shown,
    so a check that built a canvas, resized it and looked would read the stage
    from before the layout — which is indistinguishable from an overlay that
    does not follow. The first version of this file made exactly that mistake
    and blamed the overlay. Hence `show()` in `staged_canvas` and the pump
    here, neither of which the running application needs.
    """
    canvas.resize(width, height)
    app.processEvents()


def staged_canvas(app):
    """A canvas of the source's shape, laid out, with an overlay over it."""
    canvas = Canvas(SOURCE_W / SOURCE_H)
    canvas.resize(PANE_W, PANE_H)
    canvas.show()          # offscreen; see `relaid` for why it must be shown
    app.processEvents()
    skin = over(canvas)
    skin.set_frame_size(SOURCE_W, SOURCE_H)
    return canvas, skin


# -- cases -------------------------------------------------------------------
def case_stage(run: Run, app) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    canvas, skin = staged_canvas(app)
    if skin.stage() != canvas.stage():
        bad.append(f"the overlay is drawn against {skin.stage()} and the "
                   f"content was placed at {canvas.stage()}")
    if skin.geometry() != canvas.rect():
        bad.append(f"the overlay is {skin.geometry()} over a canvas of "
                   f"{canvas.rect()}")

    relaid(canvas, app, PANE_W // 2, PANE_H)   # a splitter dragged
    if skin.stage() != canvas.stage() or skin.geometry() != canvas.rect():
        bad.append("the overlay did not follow a resize, so the box is drawn "
                   "where the picture was")

    canvas.set_aspect(4 / 3)                # a clip of another shape
    if skin.stage() != canvas.stage():
        bad.append("the overlay did not follow a change of aspect")
    run.note(f"stage: overlay tracks the stage through a resize and a change "
             f"of aspect; last stage {skin.stage()}")
    return "stage (one answer to where the picture is)", 4, bad


def case_maps(run: Run, app) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    canvas, skin = staged_canvas(app)
    stage = canvas.stage()
    heard: list[QRect] = []
    skin.drawn.connect(heard.append)

    start = QPoint(stage.x() + 40, stage.y() + 30)
    end = QPoint(stage.x() + 300, stage.y() + 200)
    drag(app, skin, start, end)
    if len(heard) != 1:
        bad.append(f"a drag over the picture emitted {len(heard)} rects")
        return "maps (widget coordinates out)", 2, bad
    got = heard[0]
    want = QRect(start, end).normalized()
    if got != want:
        bad.append(f"the drag left as {got}, not the {want} that was drawn")
    if to_source(got, stage) != to_source(want, stage):
        bad.append("the emitted rect does not map to the source crop the "
                   "drawn one does")
    run.note(f"maps: {want} out of the overlay maps to "
             f"{to_source(want, stage)} in source pixels")
    return "maps (widget coordinates out)", 2, bad


def case_roundtrip(run: Run, app) -> tuple[str, int, list[str]]:
    """The set crop, drawn back, lands where it was dragged."""
    bad: list[str] = []
    canvas, skin = staged_canvas(app)
    stage = canvas.stage()
    heard: list[QRect] = []
    skin.drawn.connect(heard.append)

    start = QPoint(stage.x() + 60, stage.y() + 50)
    end = QPoint(stage.x() + 420, stage.y() + 260)
    drag(app, skin, start, end)
    if not heard:
        bad.append("nothing was drawn")
        return "roundtrip (the box is the crop)", 3, bad

    settled = to_source(heard[0], stage)
    skin.show_crop(settled)
    box = skin._box()
    want = to_widget(settled, stage)
    if box is None:
        bad.append("a crop was set and nothing is drawn for it")
    else:
        off = max(abs(box.x() - want.x()), abs(box.y() - want.y()),
                  abs(box.width() - want.width()),
                  abs(box.height() - want.height()))
        if off > SLACK:
            bad.append(f"the box is drawn at {box} and the crop it claims to "
                       f"be is at {want} — {off}px out, which is the two "
                       "mappings having become two implementations")
        drawn = QRect(start, end).normalized()
        wander = max(abs(box.x() - drawn.x()), abs(box.y() - drawn.y()))
        if wander > MINIMUM:
            bad.append(f"the box is {wander}px from where the hand dragged it")

    # And through a resize, which is where a mapping against the wrong
    # rectangle stops agreeing even by accident.
    was = skin._box()
    relaid(canvas, app, PANE_W, PANE_H // 2)
    after = skin._box()
    want_after = to_widget(settled, canvas.stage())
    if after is None:
        bad.append("the box vanished on a resize")
    elif max(abs(after.x() - want_after.x()),
             abs(after.y() - want_after.y())) > SLACK:
        bad.append(f"after a resize the box is at {after}, not {want_after}")
    run.note(f"roundtrip: crop {settled} drawn at {was}, and at {after} once "
             "the pane was halved — a box that did not move is one being "
             "mapped against something that did not either")
    return "roundtrip (the box is the crop)", 3, bad


def case_gesture(run: Run, app) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    canvas, skin = staged_canvas(app)
    stage = canvas.stage()
    heard: list[QRect] = []
    refusals: list[str] = []
    skin.drawn.connect(heard.append)
    skin.refused.connect(refusals.append)

    # a click, and a twitch under the floor
    at = QPoint(stage.center())
    drag(app, skin, at, at)
    drag(app, skin, at, QPoint(at.x() + DRAG_MIN - 1, at.y() + DRAG_MIN - 1))
    if heard:
        bad.append(f"a click set a crop: {heard}")

    # a drag that runs off the picture stops at its edge
    drag(app, skin, QPoint(stage.x() + 20, stage.y() + 20),
         QPoint(stage.right() + 400, stage.bottom() + 400))
    if not heard:
        bad.append("a drag off the picture emitted nothing at all")
    elif not stage.contains(heard[-1]):
        bad.append(f"the band left the picture: {heard[-1]} is not inside "
                   f"{stage}")

    # and one that is refused says why
    heard.clear()
    skin.allow(False)
    drag(app, skin, QPoint(stage.x() + 30, stage.y() + 30),
         QPoint(stage.x() + 300, stage.y() + 200))
    if heard:
        bad.append("a refused drag set a crop anyway")
    if len(refusals) != 1:
        bad.append(f"a refused drag said {refusals}; a gesture that does "
                   "nothing and says nothing reads as a broken canvas")
    run.note(f"gesture: a click sets nothing, a drag off the picture stops at "
             f"its edge, a refused one says {refusals!r}")
    return "gesture (click, overrun, refusal)", 4, bad


class Pane:
    """The dozen lines a tuning pane will own, standing in for one.

    Not in `src/` because where it goes is the tuning pane's decision and the
    tuning pane does not exist. Here so that T1 is demonstrated as a loop
    rather than as two pieces that each work alone.
    """

    def __init__(self, canvas, skin) -> None:
        self.canvas, self.skin = canvas, skin
        self.boxes = [NumberBox(0, low=0, high=max(SOURCE_W, SOURCE_H))
                      for _ in range(4)]
        self.pushes = 0
        skin.drawn.connect(self._drawn)
        for box in self.boxes:
            box.chosen.connect(self._typed)

    def settle(self, rect) -> None:
        self.pushes += 1
        legal = clamp(rect)
        self.skin.show_crop(legal)
        for box, value in zip(self.boxes, legal):
            box.show_value(value)

    def _drawn(self, band: QRect) -> None:
        self.settle(to_source(band, self.canvas.stage()))

    def _typed(self, _value: int) -> None:
        self.settle(tuple(box.value() for box in self.boxes))

    def shown(self) -> tuple[int, ...]:
        return tuple(box.value() for box in self.boxes)


def case_closes(run: Run, app) -> tuple[str, int, list[str]]:
    bad: list[str] = []
    canvas, skin = staged_canvas(app)
    pane = Pane(canvas, skin)
    stage = canvas.stage()

    drag(app, skin, QPoint(stage.x() + 15, stage.y() + 12),
         QPoint(stage.x() + 380, stage.y() + 240))
    if skin.crop() is None:
        bad.append("a drag reached the overlay and no crop was set")
        return "closes (drag, numbers, clamp)", 4, bad
    if pane.shown() != skin.crop():
        bad.append(f"the numbers say {pane.shown()} and the box is drawn for "
                   f"{skin.crop()}")
    if any(v % 2 for v in pane.shown()):
        bad.append(f"an odd edge reached the numbers: {pane.shown()}")

    # Typing something the clamp refuses: a crop wider than the frame.
    before = pane.pushes
    pane.boxes[2].setValue(SOURCE_W * 2)
    if pane.pushes - before != 1:
        bad.append(f"one typed number cost {pane.pushes - before} decisions; "
                   "a correction is being announced as an edit")
    width = pane.shown()[2]
    if width > SOURCE_W - pane.shown()[0]:
        bad.append(f"the numbers show a width of {width}, which does not fit "
                   f"on a {SOURCE_W}px frame")
    if pane.shown() != skin.crop():
        bad.append("after a refused number the numbers and the box disagree")
    run.note(f"closes: a drag set {skin.crop()}; typing a width of "
             f"{SOURCE_W * 2} came back as {pane.shown()[2]} in one push")
    return "closes (drag, numbers, clamp)", 4, bad


def main() -> None:
    broken = "--broken" in sys.argv
    if broken:
        overlay_mod.CropOverlay._box = own_box

    app = QApplication.instance() or QApplication([])
    run = Run(
        experiment="T1-overlay" + ("-broken" if broken else ""),
        question="Does a crop drawn on the stage come back as the crop that "
                 "was kept?",
    )
    run.note(f"offscreen; a {SOURCE_W}x{SOURCE_H} source in a "
             f"{PANE_W}x{PANE_H} pane, so the stage is letterboxed and a "
             "mapping against the widget rect is wrong by a measurable amount")
    if broken:
        run.note("RUN WITH --broken: `_box` works the mapping out a second "
                 "time against its own rect. `roundtrip` is expected to FAIL.")

    results = [
        case_stage(run, app),
        case_maps(run, app),
        case_roundtrip(run, app),
        case_gesture(run, app),
        case_closes(run, app),
    ]

    ok = True
    print(f"{'case':<44} {'checked':>9}  verdict")
    for label, checked, bad in results:
        ok = ok and not bad
        print(f"{label:<44} {checked:>9}  "
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
              "being reached and these cases are not demonstrating what they "
              "claim.")
    path = run.write()
    print(f"wrote {path}")


if __name__ == "__main__":
    main()

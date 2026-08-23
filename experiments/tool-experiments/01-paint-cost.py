"""What drawing a tool's output costs, before anything is concluded about the store.

This runs first, ahead of the contention experiment, because it is a
prerequisite for it rather than merely a priority. Every freeze in the
session explorer's tuning loop traced to the presentation layer and none to
the tier stack, and a paint cost that is not separately instrumented reads
as a slow store — which is the day the freeze hunt cost. Worse for the
contention experiment: a live surface expensive enough to occupy a core is
itself a third consumer,
so a contention number taken with an unmeasured renderer alongside is a
number about the renderer.

Three questions, each a fork in code that is already written:

1. **Overlay order.** The field must be *computed* at analysis size to stay
   truthful, but it is *drawn* at display size. Colour-mapping before the
   resize maps every analysis pixel and then throws most of them away;
   after, it maps only what is shown. The two are not the same picture —
   averaging a quantity then colouring it is what a colour bar claims is
   happening, averaging colours is not — so the difference is reported here
   as well as the times, per the standing rule not to assume two routes are
   bit-identical.

2. **Live graph.** A rasteriser against a decimation. The existing fix for
   matplotlib was to move it off the GUI thread, which stops the hiccup and
   leaves the work running; this prices what the work is, at the two sizes
   a session actually draws — a tuning window and the whole timeline.

3. **The reduction itself**, at the sizes it would run at, so the claim that
   it is free beside a blit is a measured one.

The sizes come from the session explorer's own geometry: a 1024² crop drawn
into a canvas that measured 822-900 px wide, and an 11,304-frame timeline
into a strip about as wide. They are stated as parameters in the result
rather than as constants believed here.
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decode-experiments"))
import harness  # noqa: E402
from harness import Run, report, time_case  # noqa: E402

import surfaces  # noqa: E402

harness.RESULTS = Path(__file__).resolve().parent / "results"

# ── knobs ────────────────────────────────────────────────────────────────
ANALYSIS = (1024, 1024)   #: the crop the tools run on
CANVAS = (850, 850)       #: what the explorer's canvas measured
STRIP_COLUMNS = 850       #: a timeline strip about a canvas wide
WINDOW_FRAMES = 300       #: the 10 s tuning window
TIMELINE_FRAMES = 11304   #: the 5.3K source's decodable length
ALPHA = 0.55
CEILING = 30.0
REPS = 60


def _frames():
    rng = np.random.default_rng(0)
    field = (rng.random(ANALYSIS[::-1]).astype(np.float32) * CEILING)
    display = (rng.random((CANVAS[1], CANVAS[0], 3)) * 255).astype(np.uint8)
    return field, display


def _colormap_then_resize(field, display):
    scaled = np.clip(field / CEILING, 0, 1)
    heat = cv2.applyColorMap((scaled * 255).astype(np.uint8), cv2.COLORMAP_INFERNO)
    heat = cv2.resize(heat, CANVAS, interpolation=cv2.INTER_LINEAR)
    return cv2.addWeighted(display, 1 - ALPHA, heat, ALPHA, 0)


def _resize_then_colormap(field, display):
    return surfaces.overlay(display, field, CEILING, ALPHA)


def repeat(fn, n=REPS):
    """One `yield` per call, plus the leading one `time_case` uses as t0."""
    def work():
        yield "start"
        for _ in range(n):
            fn()
            yield True
    return work


def main() -> None:
    run = Run(
        experiment="01-paint-cost",
        question="What does drawing a tool's output cost, per surface and per order?",
    )
    run.note(f"analysis={ANALYSIS} canvas={CANVAS} alpha={ALPHA} ceiling={CEILING}")
    field, display = _frames()

    print("overlay, one frame:")
    for name, fn in (("colormap-then-resize", _colormap_then_resize),
                     ("resize-then-colormap", _resize_then_colormap)):
        case = time_case(run, f"overlay {name}", repeat(lambda f=fn: f(field, display)),
                         params={"analysis": list(ANALYSIS), "canvas": list(CANVAS)},
                         unit="ms per drawn frame")
        report(case)

    a = _colormap_then_resize(field, display)
    b = _resize_then_colormap(field, display)
    diff = int(np.abs(a.astype(int) - b.astype(int)).max())
    run.note(f"the two overlay orders differ by up to {diff}/255 per channel — "
             "they are different pictures, and resize-then-colormap is the one "
             "whose colour bar is honest (it averages the quantity, not colours)")

    print("live graph, one refresh:")
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    rng = np.random.default_rng(1)
    values = rng.random(TIMELINE_FRAMES).astype(np.float32)
    covered = np.ones(TIMELINE_FRAMES, dtype=bool)

    def mpl(n):
        def go():
            figure = Figure(figsize=(CANVAS[0] / 100, 1.4), dpi=100)
            canvas = FigureCanvasAgg(figure)
            figure.add_subplot(111).plot(values[:n])
            canvas.draw()
            return np.asarray(canvas.buffer_rgba())
        return go

    for n, label in ((WINDOW_FRAMES, "window"), (TIMELINE_FRAMES, "timeline")):
        case = time_case(run, f"matplotlib Agg {label} n={n}", repeat(mpl(n), 20),
                         params={"points": n, "columns": STRIP_COLUMNS},
                         unit="ms per refresh")
        report(case)
        case = time_case(
            run, f"to_columns {label} n={n}",
            repeat(lambda n=n: surfaces.to_columns(
                values[:n], covered[:n], STRIP_COLUMNS)),
            params={"points": n, "columns": STRIP_COLUMNS},
            unit="ms per refresh")
        report(case)

    run.note("to_columns is the reduction only; what a live surface adds on top "
             "is a painter polyline over at most `columns` segments, which is "
             "the explorer's to measure with a widget in hand")
    path = run.write()
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()

"""What drawing a step's output costs, before anything is concluded about the store.

This runs before the rest because it is a prerequisite rather than merely a
priority. Every freeze in the session explorer's tuning loop traced to the
presentation layer and none to the tier stack, and a paint cost that is not
separately instrumented reads as a slow store — the mistake that cost this
tree a day. Worse for anything measuring contention: a live surface expensive
enough to hold a core is a consumer in its own right, so a number taken
beside an uninstrumented renderer is partly about the renderer.

Three forks, each already present in code that ships:

**Overlay order.** A field must be *computed* at analysis size to stay
truthful, and is *drawn* at display size. Colour-mapping before the resize
maps every analysis pixel and discards most of them; after, it maps only what
is shown. The two are not the same picture — averaging a quantity and then
colouring it is what a colour bar claims, averaging colours is not — so the
difference is reported here alongside the times, per the standing rule
against assuming two routes are bit-identical.

**The live graph.** A rasteriser against a decimation. The known fix for
matplotlib was to move it off the GUI thread, which stops the hiccup and
leaves the work running; this prices what that work is, at the two sizes a
session actually draws.

**The reduction itself**, at the sizes it would run at, so that calling it
free beside a blit is measured rather than asserted.

Sizes come from the session explorer's own geometry and are stated as
parameters in the result rather than as constants believed here.
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
ANALYSIS = (1024, 1024)   #: the crop the steps run on
CANVAS = (850, 850)       #: what the explorer's canvas measured
STRIP_COLUMNS = 850       #: a timeline strip about a canvas wide
WINDOW_ROWS = 300         #: the tuning window
TIMELINE_ROWS = 11304     #: the source's decodable length
ALPHA = 0.55
CEILING = 30.0
REPS = 60
FIGURE_REPS = 20          #: a rasteriser is slow enough to need fewer


def _inputs():
    rng = np.random.default_rng(0)
    field = rng.random(ANALYSIS[::-1]).astype(np.float32) * CEILING
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
    """One yield per call, plus the leading one `time_case` uses as t0."""
    def work():
        yield "start"
        for _ in range(n):
            fn()
            yield True
    return work


def main() -> None:
    run = Run(
        experiment="01-paint-cost",
        question="What does drawing a step's output cost, per surface and "
                 "per order?",
    )
    run.note(f"analysis={ANALYSIS} canvas={CANVAS} alpha={ALPHA} "
             f"ceiling={CEILING}")
    run.note("inputs are synthetic. Random noise is the worst case for an "
             "area resize and nothing like a real difference image or flow "
             "magnitude, which are smooth and mostly zero — the ordering "
             "here should transfer and the absolute values may not, so a "
             "felt cost is the explorer's to report and not this file's.")
    field, display = _inputs()

    print("overlay, one drawn frame:")
    for label, fn in (("colormap-then-resize", _colormap_then_resize),
                      ("resize-then-colormap", _resize_then_colormap)):
        case = time_case(run, f"overlay {label}",
                         repeat(lambda f=fn: f(field, display)),
                         params={"analysis": list(ANALYSIS),
                                 "canvas": list(CANVAS)},
                         unit="ms per drawn frame")
        report(case)

    a = _colormap_then_resize(field, display)
    b = _resize_then_colormap(field, display)
    diff = int(np.abs(a.astype(int) - b.astype(int)).max())
    run.note(f"the two overlay orders differ by up to {diff}/255 per "
             f"channel: different pictures, and resize-then-colormap is the "
             f"one whose colour bar is honest, because it averages the "
             f"quantity rather than the colours")

    print("\nlive graph, one refresh:")
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    rng = np.random.default_rng(1)
    values = rng.random(TIMELINE_ROWS).astype(np.float32)
    covered = np.ones(TIMELINE_ROWS, dtype=bool)

    def rasterise(n):
        def go():
            figure = Figure(figsize=(CANVAS[0] / 100, 1.4), dpi=100)
            canvas = FigureCanvasAgg(figure)
            figure.add_subplot(111).plot(values[:n])
            canvas.draw()
            return np.asarray(canvas.buffer_rgba())
        return go

    for n, label in ((WINDOW_ROWS, "window"), (TIMELINE_ROWS, "timeline")):
        case = time_case(run, f"matplotlib Agg {label} n={n}",
                         repeat(rasterise(n), FIGURE_REPS),
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

    run.note("to_columns is the reduction alone; what a live surface adds on "
             "top is a painter polyline over at most `columns` segments, "
             "which needs a widget in hand and is the explorer's to measure")
    path = run.write()
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()

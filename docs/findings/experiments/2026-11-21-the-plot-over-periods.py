"""The one-off of docs/spec/a-cut-in-time.md's plot box, offscreen, with no walk under it. A Plot is
handed a node's line over three periods, two of them overlapping, as the window hands it beside the
walk of the nodes no cut in time feeds. Each piece's first drawn column is set against its own
first row, the columns between the periods are read for the line's colour, and the hover over the
overlap is read for its readouts. Then purb's document with a `period` on the video, everything of
it below the `period`, is planned over the crossings clip, and the frame view is handed the row
before a period and a row inside one.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-21-the-plot-over-periods.py 2>NUL

Qt runs offscreen, so no window opens.
"""
import json
import os
import sys
import tempfile

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player import theme  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.graph import Graph  # noqa: E402
from sieve_player.plot import Plot  # noqa: E402
from sieve_player.registry import defaults, discover  # noqa: E402
from sieve_player.window import Display, outside_cuts  # noqa: E402

DOC = os.path.join(ROOT, "video-tests", "purb-168-178.json")
WINDOW = (100, 200)
PIECES = [(80, 160), (140, 200), (240, 290)]    # a cut short before the window, b overlapping it, c after a gap


def coloured(img, x, inner):
    """Whether column `x` of the plot's field holds the selection's line colour."""
    want = theme.SERIES
    for y in range(int(inner.top()) + 1, int(inner.bottom())):
        c = img.pixelColor(x, y)
        if abs(c.red() - want.red()) + abs(c.green() - want.green()) + abs(c.blue() - want.blue()) < 40:
            return True
    return False


if __name__ == "__main__":
    decmod.QUIET = True
    QApplication.instance() or QApplication([])
    s, n = WINDOW
    plot = Plot()
    plot.resize(1200, 154)
    plot.set_window(s, n, 30.0)
    pieces = [(10.0 + 5 * k + np.sin(np.arange(b - a) / 7.0), None, a) for k, (a, b) in enumerate(PIECES)]
    plot.set_lines({"track": pieces})
    plot.set_selection("track")
    img, inner = plot.grab().toImage(), plot._inner()
    print(f"window {s}-{s + n}, periods {PIECES}")
    for line in plot.lines["track"].pieces:
        xs, _, _, rows = plot._columns(line)
        first = line.start + rows.start
        print(f"  piece from row {line.start}: first drawn row {first}, at x {xs[0]:.1f}, where row {max(line.start, s)} lies at {plot._x(max(line.start, s)):.1f}")
    gap = [r for r in range(200, 240)]
    lit = [r for r in gap if coloured(img, round(plot._x(r)), inner)]
    inside = [r for r in range(150, 155) if coloured(img, round(plot._x(r)), inner)]
    print(f"  rows 200-239, between the periods: {len(lit)} of {len(gap)} columns in the line's colour; rows 150-154, inside one: {len(inside)} of 5")
    plot.set_hover(150)
    print(f"  hover at row 150, where two periods overlap: {[text for _, text, _, _ in plot.readouts()]}")
    plot.set_hover(-1)
    plot.set_playhead(150)
    print(f"  the corner at the playhead there: {plot.lines['track'].at(150)}")

    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    with tempfile.TemporaryDirectory() as tmp:
        doc = D.load(DOC, tools)
        path = os.path.join(tmp, "periods.json")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"rows": 590, "periods": [{"name": "a", "first": 40, "end": 200}]}, f)
        period = doc.add_node("period", (0.0, 0.0), {**defaults(tools["period"]), **tools["period"].load_periods(path)}).id
        selector = doc.add_node("file", (0.0, 0.0), {**defaults(tools["file"]), "folder": tmp, "pattern": "periods.json"}).id
        doc.connect(selector, period, "periods")
        doc.disconnect("threshold", "in")
        doc.connect("video", period)
        doc.connect(period, "threshold")
        g = Graph(doc, Decoder(doc.video), tools)
        e = g.snapshot().entries["threshold"]
        for row in (39, 40):
            display = Display()
            if said := outside_cuts(e, "threshold", row):
                display.clear(said)
            print(f"  the frame of threshold at row {row}: {display.reason or 'a frame, nothing said'!r}")
        g.close()

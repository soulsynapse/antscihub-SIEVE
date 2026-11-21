"""The one-off of docs/spec/a-cut-in-time.md's box of each `period`'s periods drawn on the strip: a
document of two `period`s, one fed `count`'s gate over the crossings clip banded at its median and
one fed a file with an overlap, the strip handed their cuts as the window hands them, and its
lanes and its pixels against each one's periods, with each node in turn the selection.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-20-periods-on-the-strip.py 2>NUL

Qt runs offscreen, so no window opens. The document and band are those of
2026-11-20-a-period-fed-a-gate.py.
"""
import os
import sys
import tempfile

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402
from PySide6.QtGui import QColor  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player import theme  # noqa: E402
from sieve_player.cut import cut_in_time  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.graph import Graph, Series, gated  # noqa: E402
from sieve_player.plan import plan  # noqa: E402
from sieve_player.registry import computed, cuts, defaults, discover  # noqa: E402
from sieve_player.timeline import Strip  # noqa: E402

DOC = os.path.join(ROOT, "video-tests", "purb-168-178.json")
FILED = [(0, 200), (150, 300), (290, 400), (500, 590)]


def drawn(image, rect):
    return QColor(image.pixel(int(rect.center().x() * image.devicePixelRatio()), int(rect.center().y() * image.devicePixelRatio())))


if __name__ == "__main__":
    decmod.QUIET = True
    app = QApplication([])
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    doc = D.load(DOC, tools)
    g = Graph(doc, Decoder(doc.video), tools)
    n, fps = g.count, g.fps
    blobs = np.empty(n, object)
    blobs[:] = [g.compute("blobs", r) for r in range(n)]
    g.close()
    g.decoder.close()
    count = tools["count"]
    result = count.run(Series(blobs, "k", 0, fps), computed(count, defaults(count)))
    band = (float(np.median(result["signal"])), float(np.max(result["signal"])))
    doc.node("count").band = band
    period = tools["period"]
    by_gate = doc.add_node("period", (0.0, 0.0), defaults(period))
    doc.connect("video", by_gate.id)
    doc.connect("count", by_gate.id, "gate")
    by_file = doc.add_node("period", (0.0, 0.0), defaults(period))
    doc.connect("video", by_file.id)
    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "filed.json")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(period.periods_text(n, FILED))
        selector = doc.add_node("file", (0.0, 0.0), {**defaults(tools["file"]), "folder": folder, "pattern": "filed.json"})
        doc.connect(selector.id, by_file.id, "periods")
        doc.node(by_file.id).params.update(period.PATHS["periods"](D.pick_path(doc, tools, by_file.id, "periods")[0]))
    entries = plan(doc, tools, "video key", cut_result=lambda nid, key: gated({**result, "key": key}, band, "signal")[0] if nid == by_gate.id else None).entries
    spans = {n.id: [s for r in e.cuts if (s := cut_in_time(r))] for n in doc.nodes if (e := entries.get(n.id)) and cuts(e.tool)}
    print({nid: len(ss) for nid, ss in spans.items()}, "periods a node; the file's", FILED)

    strip = Strip()
    strip.resize(1600, Strip.H)
    strip.set_count(n, fps)
    strip.set_series({"count": (result["signal"], 0, None)})
    strip.set_periods(spans)
    print("lanes:", [(nid, len(ss)) for nid, ss in strip.lanes])
    for selection in ("count", by_gate.id, by_file.id):
        strip.set_series({"count": (result["signal"], 0, None)}, selection)
        image = strip.grab().toImage()
        bad = []
        for k, (nid, ss) in enumerate(strip.lanes):
            want = QColor.fromHsv(theme.hashed_hue(nid), *theme.TYPE_SV)
            for first, end in ss:
                if strip.lane_rect(k, first, end).width() >= 2 and drawn(image, strip.lane_rect(k, first, end)).rgb() != want.rgb():
                    bad.append((nid, first, end))
            gaps = [(a, b) for (_, a), (b, _) in zip(ss, ss[1:]) if strip.lane_rect(k, a, b).width() >= 3]
            bad += [(nid, "gap", a, b) for a, b in gaps if drawn(image, strip.lane_rect(k, a, b)).rgb() == want.rgb()]
        print(f"selection {selection}: every span in its node's colour and no gap: {not bad}", bad[:5])
    print("the two nodes' colours differ:", theme.hashed_hue(by_gate.id) != theme.hashed_hue(by_file.id))
    lowest = strip.height() - 1 - len(strip.lanes) * (Strip.LANE + 1)
    print(f"the series' floor at y {lowest}, above the top lane's {strip.lane_rect(len(strip.lanes) - 1, 0, 1).top()}")

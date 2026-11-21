"""The one-off of docs/spec/a-cut-in-time.md's box of a gate's periods written to a file: `count`
over the crossings clip, banded at its median and wired into a `period`'s gate; the periods the
plan gives it written by the `period`'s card's Write, the save dialog answered with a scratch path;
a second `period` fed the file by a `file` selector, its loader reading it as the window's
would, and its periods against the first's.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-20-a-gates-periods-written.py 2>NUL

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
from PySide6.QtWidgets import QApplication, QFileDialog  # noqa: E402

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.graph import Graph, Series, gated  # noqa: E402
from sieve_player.plan import plan  # noqa: E402
from sieve_player.registry import computed, defaults, discover  # noqa: E402

DOC = os.path.join(ROOT, "video-tests", "purb-168-178.json")


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
    entries = plan(doc, tools, "video key", cut_result=lambda nid, key, within: gated({**result, "key": key}, band, "signal")[0]).entries
    gave = [r.extent.rows for r in entries[by_gate.id].cuts]

    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "chosen.json")
        asked = []
        QFileDialog.getSaveFileName = staticmethod(lambda parent, title, default, filt: (asked.append(default), (path, filt))[1])
        card = period.settings()
        card.set_params(by_gate.params)
        card.set_source(doc.video, fps)
        card.show_cuts(entries[by_gate.id].cuts, n, "count")
        print(f"button: {card.button.text()!r}, enabled {card.button.isEnabled()}")
        card.button.click()
        print(f"dialog filled in {os.path.basename(asked[0])!r} in the footage's folder: {os.path.dirname(asked[0]) == os.path.dirname(doc.video)}")
        print(f"card says: {card.status.text()!r}")
        by_file = doc.add_node("period", (0.0, 0.0), defaults(period))
        doc.connect("video", by_file.id)
        selector = doc.add_node("file", (0.0, 0.0), {**defaults(tools["file"]), "folder": folder, "pattern": "chosen.json"})
        doc.connect(selector.id, by_file.id, "periods")
        picked, why = D.pick_path(doc, tools, by_file.id, "periods")
        print(f"the selector picks the written file: {picked is not None and os.path.samefile(picked, path)} {why}")
        params = period.PATHS["periods"](picked)
    doc.node(by_file.id).params.update(params)
    read = [r.extent.rows for r in plan(doc, tools, "video key", cut_result=lambda nid, key, within: None).entries[by_file.id].cuts]
    print(f"{n} rows; file rows {params['rows']}; names of the first three {[p['name'] for p in params['periods'][:3]]}")
    print(f"the gate gave {len(gave)} periods, the file {len(read)}: {'the same' if read == gave else 'DIFFER'}")
    unfed = period.settings()
    unfed.set_source(doc.video, fps)
    unfed.show_cuts(entries[by_gate.id].cuts, n, None)
    print(f"a period fed no gate: button enabled {unfed.button.isEnabled()}")

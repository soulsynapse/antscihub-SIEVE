"""Experiment behind docs/findings/2026-11-12-a-cold-window-and-the-clip.md, the observation the two forks
of The old monitor goes in docs/spec/monitor.md ask for: cold windows taken at places along a clip, each
projected to the clip by catalogue.cold, beside a clip walk's measured cost on a fresh graph.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-12-a-cold-window-and-the-clip.py [sim | live | saved] 2>NUL

`sim` is the simulations' graph, whose clip is 64 rows and whose chain ends in a node run whole; `live` is
video-tests/purb-settings.json with every bake live and `saved` the document as it is saved. A window's
figure is its record's, its nodes' ms and its unprobed over its rows; the projection is given by each
node's mean and, for a node run whole, by its growth fitted along the window. Last, what the catalogue
finds in the clip walk.
"""
import os
import sys
import tempfile
import time

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player import store  # noqa: E402
from sieve_player.catalogue import Log, cold, cost, line, reach  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.dev import simulations  # noqa: E402
from sieve_player.graph import Graph  # noqa: E402
from sieve_player.ledger import Ledger  # noqa: E402
from sieve_player.registry import discover  # noqa: E402
from sieve_player.worker import Worker  # noqa: E402

DOC = os.path.join(ROOT, "video-tests", "purb-settings.json")
PLACES = (0.0, 0.2, 0.4, 0.6, 0.8)


class Session:
    """A graph, its worker and a ledger on it; `walk` waits for the window and `clip` for the clip."""

    def __init__(self, graph, every):
        self.graph, self.ledger = graph, Ledger()
        graph.on_event = self.ledger.event
        graph.sync()
        self.worker = Worker(graph, every=every)
        self.win, self.clipped, self.series, self.clips = [], [], [], []
        self.worker.walked.connect(lambda d, n, *_: self.win.append((d, n)))
        self.worker.clipWalked.connect(lambda d, n, *_: self.clipped.append((d, n)))
        self.worker.seriesReady.connect(lambda *a: self.series.append(a))
        self.worker.clipReady.connect(lambda *a: self.clips.append(a))
        self.worker.clipRefused.connect(lambda why: sys.exit(f"the clip walk was refused: {why}"))

    def wait(self, done, what, timeout=1800):
        t = time.perf_counter()
        while not done():
            QApplication.processEvents()
            time.sleep(0.002)
            if time.perf_counter() - t > timeout:
                sys.exit(f"{what} did not finish in {timeout} s")
        return time.perf_counter() - t

    def walk(self, start, length):
        self.win.clear()
        self.series.clear()
        self.worker.set_window(start, length)
        if not self.worker.isRunning():
            self.worker.start()
        self.wait(lambda: self.win and self.win[-1] == (length, length) and (self.series or not self.graph.chain), "the window")
        return self.ledger.view()

    def clip(self):
        self.worker.walk_clip()
        if not self.worker.isRunning():
            self.worker.start()
        n = self.graph.count
        s = self.wait(lambda: self.clipped and self.clipped[-1][0] == self.clipped[-1][1] >= n - 1
                      and (self.clips or not self.graph.chain), "the clip walk")
        return self.ledger.view(), s

    def close(self):
        self.worker.stop()
        self.graph.close()
        self.graph.decoder.close()


def per_node(w, only):
    return {n: sum(r[1] for (k, d, _), r in x.runs.items() if d == "walk" and k != "seek") / w.done
            for n, x in w.nodes.items() if n in only}


def run(make, every, length, label):
    s = make()
    n = s.graph.count
    print(f"\n== {label}: {n} rows at {s.graph.fps:.2f} fps, windows of {length}, the chain's cadence {every}")
    shown, firsts = None, []
    for place in PLACES:
        start = min(int(place * n), n - length)
        view = s.walk(start, length)
        w = view.walks[-1]
        p = cold(view)
        if shown is None:
            shown = sorted(reach(w.plan))
            print(f"   the plan reaches {', '.join(shown)}; static {', '.join(c.node for c in p.nodes.values() if c.walk is None) or 'none'}; "
                  f"run whole {', '.join(c.node for c in p.nodes.values() if c.grows) or 'none'}; no figure for {p.missing or 'none'}")
            print(f"   {'window at':>10} {'its own':>8} {'folds':>7} {'seeks':>7} {'projected':>10} {'by growth':>10} {'clip, s':>8} {'by growth':>10}"
                  f"  stale")
        folds = sum(r[1] for x in w.nodes.values() for (k, d, _), r in x.runs.items() if k == "fold" or d == "fold") / w.done
        sought = sum(r[1] for x in w.nodes.values() for (k, d, _), r in x.runs.items() if k == "seek" and d == "walk") / w.done
        a, b = p.ms_row(), p.ms_row(n)
        firsts.append((a, b, p))
        print(f"   {start:>10} {(cost(w) + w.unprobed) / w.done:>8.3f} {folds:>7.3f} {sought:>7.3f} {a:>10.3f} {b:>10.3f} "
              f"{a * n / 1000:>8.1f} {b * n / 1000:>10.1f}  {[c.node for c in p.nodes.values() if c.stale] or ''}")
    s.close()

    s = make()
    view, wall = s.clip()
    w = next(x for x in reversed(view.walks) if x.lane == "clip")
    measured = (cost(w) + w.unprobed) / w.done
    print(f"   the clip walk, cold, on a fresh graph: {w.done} rows in {wall:.1f} s, {wall / w.done * 1000:.3f} ms a row by the wall, "
          f"{measured:.3f} by its record, of which {w.unprobed / w.done:.3f} unprobed; recomputed {dict(w.recomputed) or 'nothing'}")
    means, grown = [f[0] for f in firsts], [f[1] for f in firsts]
    print(f"   projected by the mean {min(means):.3f} to {max(means):.3f}, {min(means) / measured:.2f} to {max(means) / measured:.2f} of the clip walk; "
          f"by growth {min(grown):.3f} to {max(grown):.3f}, {min(grown) / measured:.2f} to {max(grown) / measured:.2f}")
    clip = per_node(w, shown)
    print(f"   {'node':16} {'clip walk':>10}" + "".join(f"{'w' + str(i):>9}" for i in range(len(firsts))) + "   by growth, each window")
    for nid in shown:
        cs = [f[2].nodes.get(nid) for f in firsts]
        grows = "  ".join(f"{(c.grows[0] * n / c.grows[2] + c.grows[1] * c.grows[2] * (n / c.grows[2]) * (n / c.grows[2] + 1) / 2) / n:.3f}"
                          for c in cs if c and c.grows)
        print(f"   {nid:16} {clip.get(nid, 0.0):>10.3f}" + "".join(f"{c.ms_row if c else float('nan'):>9.3f}" for c in cs) + "   " + grows)
    print(f"   {'unprobed':16} {w.unprobed / w.done:>10.3f}" + "".join(f"{f[2].unprobed:>9.3f}" for f in firsts))
    log = Log()
    log.read(view)
    print("   the catalogue on the clip walk:")
    print(chr(10).join("      " + line(e) for e in log.ordered()) or "      nothing found")
    s.close()


def sim():
    folder = tempfile.mkdtemp()
    path = simulations._clip(os.path.join(folder, "clip.avi"))

    def make():
        tools = simulations._tools()
        doc = D.from_tools(list(tools.values()), path)
        return Session(Graph(doc, Decoder(path), tools), simulations.EVERY)
    run(make, simulations.EVERY, 12, "the simulations' graph")


def purb(live):
    decmod.QUIET = True
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    st = store.current()

    def make():
        doc = D.load(DOC, tools)
        for node in doc.nodes:
            if live and node.tool == "bake":
                node.mode = D.LIVE
        return Session(Graph(doc, Decoder(doc.video), tools, open_bake=lambda bk, c: st.open_bake(bk, c)), 30)
    run(make, 30, 600, "purb-settings, every bake live" if live else "purb-settings, as saved")


if __name__ == "__main__":
    QApplication.instance() or QApplication([])
    which = sys.argv[1:] or ["sim", "live", "saved"]
    for name in which:
        sim() if name == "sim" else purb(name == "live")

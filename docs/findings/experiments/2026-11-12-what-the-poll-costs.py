"""The Fork under The poll judges a walk once, in docs/spec/stream-seams.md: the monitor's window, offscreen,
on one Graph and Ledger of video-tests/purb-settings.json, its bake live, over window walks that each
begin half a window past the last, so every walk is half cold. The monitor's poll is a "slot" named
"monitor" in the stream; printed for each eight walks are the walks in the history as they end, the
polls, a poll's mean and longest ms and the polls' share of the wall.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-12-what-the-poll-costs.py [walks] [rows] 2>NUL
"""
import os
import sys
import time
from types import SimpleNamespace

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player import store  # noqa: E402
from sieve_player.catalogue import WAITS  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.dev.timeview import Window  # noqa: E402
from sieve_player.graph import Graph  # noqa: E402
from sieve_player.ledger import Ledger  # noqa: E402
from sieve_player.pace import Pace  # noqa: E402
from sieve_player.registry import discover  # noqa: E402
from sieve_player.worker import Worker  # noqa: E402

DOC = os.path.join(ROOT, "video-tests", "purb-settings.json")
WALKS = int(sys.argv[1]) if len(sys.argv) > 1 else 96
ROWS = int(sys.argv[2]) if len(sys.argv) > 2 else 120
GROUP = 8


def main():
    QApplication.instance() or QApplication([])
    decmod.QUIET = True
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    st = store.current()
    doc = D.load(DOC, tools)
    doc.node("bake").mode = D.LIVE
    dec = Decoder(doc.video)
    g = Graph(doc, dec, tools, open_bake=lambda bk, c: st.open_bake(bk, c))
    led, pace, polls = Ledger(timed=lambda: g.stream.turn("monitor", "ledger")), Pace(), []
    g.on_event = lambda ev: (polls.append(ev) if ev.kind == "slot" and ev.node == "monitor" else None, led.event(ev))
    win = Window(SimpleNamespace(graph=g, ledger=led, pace=pace, dump=None))
    win.show()
    win._timer.start()
    g.sync()
    walked, series = [], []
    w = Worker(g)
    w.walked.connect(lambda d, m, *was: (walked.append((d, m)), pace.row("window", d, m, *was)))
    w.seriesReady.connect(lambda r, s, fps: series.append(r))
    print(f"{len(doc.nodes)} nodes, walks of {ROWS} rows each begun {ROWS // 2} past the last; waits names a share of {WAITS:.0%}")
    print(f"{'walks':>9} {'in history':>10} {'wall s':>7} {'polls':>6} {'mean ms':>8} {'longest':>8} {'share':>7}")
    t0, seen = time.perf_counter(), 0
    for i in range(WALKS):
        walked.clear()
        series.clear()
        w.set_window(i * (ROWS // 2) % max(g.count - ROWS, 1), ROWS)
        if not w.isRunning():
            w.start()
        t = time.perf_counter()
        while not (walked and walked[-1] == (ROWS, ROWS) and (series or not g.chain)):
            QApplication.processEvents()
            time.sleep(0.002)
            if time.perf_counter() - t > 600:
                sys.exit("the walk did not finish")
        if (i + 1) % GROUP == 0:
            wall, ms = time.perf_counter() - t0, [ev.ms for ev in polls[seen:]]
            print(f"{i + 2 - GROUP:>4}-{i + 1:<4} {len(led.view().walks):>10} {wall:>7.1f} {len(ms):>6} {sum(ms) / max(len(ms), 1):>8.2f} "
                  f"{max(ms, default=0.0):>8.2f} {sum(ms) / 1000 / wall:>7.2%}")
            t0, seen = time.perf_counter(), len(polls)
    entries = [(e.problem.kind, e.problem.subject) for e in win.log.ordered()]
    print("the log holds:", entries or "nothing")
    w.stop()
    win.close()
    g.close()
    dec.close()


if __name__ == "__main__":
    main()

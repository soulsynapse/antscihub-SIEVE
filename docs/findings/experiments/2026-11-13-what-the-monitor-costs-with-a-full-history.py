"""What the monitor's poll and its paint cost once the history is full, and where in them it goes: the
monitor's window, offscreen at its opening size, on one Graph and Ledger of video-tests/purb-settings.json,
over window walks that each begin half a window past the last, as 2026-11-12-what-the-poll-costs.py walks
them. Printed for each sixteen walks are a poll's and a paint's mean ms as the stream has them, a "slot"
and a "paint" named "monitor"; then, the walking over, the profile of POLLS polls and of POLLS paints of
the whole window, the functions of sieve_player by cumulative time.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-13-what-the-monitor-costs-with-a-full-history.py [walks] [rows] 2>NUL
"""
import cProfile
import os
import pstats
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
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.dev.timeview import Window  # noqa: E402
from sieve_player.graph import Graph  # noqa: E402
from sieve_player.ledger import Ledger  # noqa: E402
from sieve_player.pace import Pace  # noqa: E402
from sieve_player.registry import discover  # noqa: E402
from sieve_player.worker import Worker  # noqa: E402

DOC = os.path.join(ROOT, "video-tests", "purb-settings.json")
WALKS = int(sys.argv[1]) if len(sys.argv) > 1 else 72
ROWS = int(sys.argv[2]) if len(sys.argv) > 2 else 60
GROUP, POLLS, WALKING_S = 16, 40, 30.0


def said(what, pr, n=None):
    """Prints the profile `pr` a call of `what`: over `n` calls, or as many as it has of Window._judge, one a poll."""
    stats = pstats.Stats(pr)
    n = n or next(nc for (path, _, name), (_, nc, _, _, _) in stats.stats.items() if name == "_judge" and "timeview" in path)
    print(f"\n{what}, {n} of them under the profiler; cumulative ms each, calls each")
    rows = [(ct, nc, f"{os.path.basename(path)}:{line} {name}") for (path, line, name), (_, nc, _, ct, _) in stats.stats.items()
            if "sieve_player" in path and ("timeview" in path or "catalogue" in path or "ledger" in path or "theme" in path)]
    for ct, nc, name in sorted(rows, reverse=True)[:24]:
        print(f"  {ct / n * 1000:>7.2f} {nc / n:>8.1f}  {name}")


def profile(what, fn):
    pr = cProfile.Profile()
    pr.enable()
    for _ in range(POLLS):
        fn()
    pr.disable()
    said(what, pr, POLLS)


def main():
    QApplication.instance() or QApplication([])
    decmod.QUIET = True
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    st = store.current()
    doc = D.load(DOC, tools)
    doc.node("bake").mode = D.LIVE
    dec = Decoder(doc.video)
    g = Graph(doc, dec, tools, open_bake=lambda bk, c: st.open_bake(bk, c))
    led, pace, mine = Ledger(timed=lambda: g.stream.turn("monitor", "ledger")), Pace(), {"slot": [], "paint": []}
    g.on_event = lambda ev: (mine[ev.kind].append(ev.ms) if ev.node == "monitor" and ev.kind in mine else None, led.event(ev))
    win = Window(SimpleNamespace(graph=g, ledger=led, pace=pace, dump=None))
    win.show()
    g.sync()
    walked, series = [], []
    w = Worker(g)
    w.walked.connect(lambda d, m, *was: (walked.append((d, m)), pace.row("window", d, m, *was)))
    w.seriesReady.connect(lambda r, s, fps: series.append(r))
    print(f"{len(doc.nodes)} nodes, walks of {ROWS} rows each begun {ROWS // 2} past the last, the window {win.width()} by {win.height()}")
    print(f"{'walks':>9} {'in history':>10} {'polls':>6} {'poll ms':>8} {'paints':>7} {'paint ms':>9}")
    began, seen, walking = time.perf_counter(), {"slot": 0, "paint": 0}, cProfile.Profile()
    for i in range(WALKS):
        if i == 64:
            walking.enable()
        walked.clear()
        series.clear()
        w.set_window(i * (ROWS // 2) % max(g.count - ROWS, 1), ROWS)
        if not w.isRunning():
            w.start()
        while not (walked and walked[-1] == (ROWS, ROWS) and (series or not g.chain)):
            QApplication.processEvents()
            time.sleep(0.002)
        if (i + 1) % GROUP == 0 or time.perf_counter() - began > WALKING_S:
            ms = {k: v[seen[k]:] for k, v in mine.items()}
            print(f"{'to ' + str(i + 1):>9} {len(led.view().walks):>10} {len(ms['slot']):>6} {sum(ms['slot']) / max(len(ms['slot']), 1):>8.2f} "
                  f"{len(ms['paint']):>7} {sum(ms['paint']) / max(len(ms['paint']), 1):>9.2f}")
            seen = {k: len(v) for k, v in mine.items()}
        if time.perf_counter() - began > WALKING_S:
            print(f"the walking was stopped at {WALKING_S:.0f} s")
            break
    walking.disable()
    w.stop()
    win._timer.stop()
    if WALKS > 64:
        said("a poll while the lane walks, the GUI thread's part alone", walking)
    profile("a poll", win.refresh)
    profile("a paint of the whole window", win.grab)
    win.close()
    g.close()
    dec.close()


if __name__ == "__main__":
    main()

"""Experiment behind docs/findings/2026-11-12-what-the-trace-costs.md: the window walk of
video-tests/purb-settings.json, its bake live, cold on a fresh Graph and Decoder each time, under each consumer
of the stream named, every walk's time printed.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-12-what-the-trace-costs.py <how>[,<how>...] [walks] [rows] 2>NUL

Several consumers are walked in turn, walk by walk, in one process, so a slow spell of the machine's falls on
all of them. `how` is bare, on_event unset; drop, a consumer that does nothing with an event; ledger, a Ledger
no reader takes a view of, so the emitting thread folds; read, a Ledger whose view the GUI thread takes and
the catalogue reads at POLL, a window's work less its painting; dump, a Dump; window, full and small, the
monitor's window open on the walk's ledger at the size it opens at, full screen and at its smallest, on the
screen and not offscreen. The walk is the Worker's, on its own thread with the GUI thread turning its loop, as
the player has it.
"""
import os
import sys
import tempfile
import time
from types import SimpleNamespace

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player import store  # noqa: E402
from sieve_player.catalogue import Log  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.dev.timeview import SMALLEST, Window  # noqa: E402
from sieve_player.graph import Graph  # noqa: E402
from sieve_player.ledger import Ledger  # noqa: E402
from sieve_player.pace import Pace  # noqa: E402
from sieve_player.registry import discover  # noqa: E402
from sieve_player.trace import Dump  # noqa: E402
from sieve_player.worker import Worker  # noqa: E402

DOC = os.path.join(ROOT, "video-tests", "purb-settings.json")
HOWS = sys.argv[1].split(",")
WALKS = int(sys.argv[2]) if len(sys.argv) > 2 else 6
ROWS = int(sys.argv[3]) if len(sys.argv) > 3 else 600
POLL = 250      # ms between a reader's views


def walk(tools, st, how):
    doc = D.load(DOC, tools)
    doc.node("bake").mode = D.LIVE
    dec = Decoder(doc.video)
    g = Graph(doc, dec, tools, open_bake=lambda bk, c: st.open_bake(bk, c))
    dump = timer = win = None
    pace = Pace()
    if how in ("window", "full", "small"):
        led = Ledger(timed=lambda: g.stream.turn("monitor", "ledger"))
        g.on_event = led.event
        win = Window(SimpleNamespace(graph=g, ledger=led, pace=pace, dump=None), period_ms=POLL)
        if how == "small":
            win.resize(*SMALLEST)
        win.showFullScreen() if how == "full" else win.show()
    elif how == "drop":
        g.on_event = lambda ev: None
    elif how in ("ledger", "read"):
        led = Ledger()
        g.on_event = led.event
        if how == "read":
            log = Log()
            timer = QTimer(interval=POLL)
            timer.timeout.connect(lambda: log.read(led.view()))
            timer.start()
    elif how == "dump":
        dump = Dump(g, os.path.join(tempfile.gettempdir(), f"sieve-trace-cost-{os.getpid()}.jsonl"))
    elif how != "bare":
        sys.exit(f"no consumer called {how}")
    g.sync()
    n = min(ROWS, g.count)
    walked, series = [], []
    w = Worker(g)
    w.walked.connect(lambda d, m, *was: (walked.append((d, m)), pace.row("window", d, m, *was)))
    w.seriesReady.connect(lambda r, s, fps: series.append(r))
    w.set_window(0, n)
    t = time.perf_counter()
    w.start()
    while not (walked and walked[-1][0] == walked[-1][1] and (series or not g.chain)):
        QApplication.processEvents()
        time.sleep(0.002)
        if time.perf_counter() - t > 900:
            sys.exit("the walk did not finish")
    t = time.perf_counter() - t
    w.stop()
    if timer:
        timer.stop()
    if win:
        win.close()
        win.deleteLater()
    if dump:
        dump.close()
        os.remove(dump.path)
    g.close()
    dec.close()
    return t, n / g.fps / t


def main():
    QApplication.instance() or QApplication([])
    decmod.QUIET = True
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    st = store.current()
    out = {how: [] for how in HOWS}
    for _ in range(WALKS):
        for how in HOWS:
            out[how].append(walk(tools, st, how))
    for how, ws in out.items():
        print(f"{how:6} " + " ".join(f"{t * 1000:5.0f}" for t, _ in ws) + "  ms   "
              + " ".join(f"{x:4.2f}" for _, x in ws) + "  x realtime")


if __name__ == "__main__":
    main()

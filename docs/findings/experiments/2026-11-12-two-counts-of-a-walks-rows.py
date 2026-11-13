"""The Fork under One reading of a walk's start and of what its rows were, in docs/spec/stream-seams.md,
offscreen: for every window walk that reached its last row, the rows that ran, that a store held and
that read a bake as the Worker's `walked` signal counts them, which is what the player's control draws,
beside the ledger's for the walked node, or for the head where nothing is walked. Over the simulations
and the healthy walks, then over video-tests/purb-settings.json with its bake live and as the document
has it: a cold walk, the same again, one begun half a window on, and one scrubbed while it walks.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-12-two-counts-of-a-walks-rows.py 2>NUL
"""
import os
import shutil
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
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.dev.simulations import HEALTHY, SERVED, SIMULATIONS, _named, _Run  # noqa: E402
from sieve_player.graph import Graph  # noqa: E402
from sieve_player.ledger import Ledger  # noqa: E402
from sieve_player.registry import discover  # noqa: E402
from sieve_player.worker import Worker  # noqa: E402

DOC = os.path.join(ROOT, "video-tests", "purb-settings.json")
ROWS = 300
differing = 0


def said(name, signals, view):
    """Prints each whole window walk of `view` beside the `walked` signal that closed it."""
    global differing
    closed = [s for prev, s in zip([None, *signals], signals) if s[0] == s[1] and s != prev]     # a halt repeats a walk's last signal
    whole = [w for w in view.walks if w.lane == "window" and w.done >= w.length]
    if len(closed) != len(whole):
        print(f"{name}: {len(closed)} walks closed by a signal, {closed}, and {len(whole)} whole in the ledger; not compared")
        differing += 1
        return
    for i, ((done, _, ran, served), w) in enumerate(zip(closed, whole)):
        plan = w.plan or {}
        nid = plan.get("walk") or next(iter(plan.get("chain") or []), None)
        node = w.nodes.get(nid)
        control = (ran, done - ran - served, served)
        ledger = (0, 0, 0) if node is None else (node.ran, node.held, node.served)
        by = {n: x.served for n, x in w.nodes.items() if x.served}
        differing += control != ledger
        print(f"{name:<14} walk {i} of {done:>4} rows on {str(nid):<8} ran, held, served: the control {control}, the ledger {ledger}"
              + ("" if control == ledger else f"   differs; the ledger's served rows by node {by}")
              + (" · under more than one plan" if w.replanned else ""))


def simulations():
    names = [n for n in (*HEALTHY, *SIMULATIONS) if n not in SERVED or shutil.which("ffmpeg")]
    for name in names:
        with tempfile.TemporaryDirectory() as tmp, _Run(tmp, **_named(name).run) as r:
            signals = []
            r.worker.walked.connect(lambda *s: signals.append(s))
            _named(name)(r)
            for _ in range(20):     # the signals still queued for this thread
                QApplication.processEvents()
                time.sleep(0.002)
            said(name, signals, r.ledger.view())


def purb(tools, st, live):
    doc = D.load(DOC, tools)
    if live:
        doc.node("bake").mode = D.LIVE
    dec = Decoder(doc.video)
    g = Graph(doc, dec, tools, open_bake=lambda bk, c: st.open_bake(bk, c))
    led = Ledger()
    g.on_event = led.event
    g.sync()
    signals, series, scrub = [], [], [False]
    w = Worker(g)

    def walked(done, n, ran, served):
        signals.append((done, n, ran, served))
        if scrub[0] and done % 40 == 0 and done < n:
            w.request_row((done * 37) % g.count)

    w.walked.connect(walked)
    w.seriesReady.connect(lambda r, s, fps: series.append(r))
    for start, scrubbed in ((0, False), (0, False), (ROWS // 2, False), (2 * ROWS, True)):
        closed, scrub[0] = sum(s[0] == s[1] for s in signals), scrubbed
        series.clear()
        w.set_window(start, ROWS)
        if not w.isRunning():
            w.start()
        t = time.perf_counter()
        while not (sum(s[0] == s[1] for s in signals) > closed and (series or not g.chain)):
            QApplication.processEvents()
            time.sleep(0.002)
            if time.perf_counter() - t > 600:
                sys.exit("the walk did not finish")
    w.stop()
    said(f"purb {'live' if live else doc.node('bake').mode}", signals, led.view())
    g.close()
    dec.close()


def main():
    QApplication.instance() or QApplication([])
    decmod.QUIET = True
    simulations()
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    st = store.current()
    for live in (True, False):
        purb(tools, st, live)
    print(f"\n{differing} of the walks compared differ")


if __name__ == "__main__":
    main()

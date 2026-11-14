"""Experiment behind docs/findings/2026-11-14-what-saying-what-a-thread-is-in-costs.md: the window walk of
video-tests/purb-settings.json, its bake live, cold on a fresh Graph and Decoder each time, with a Ledger, its
Log and the machine's sampler attached as the player attaches them, under the probe as it stood at ce86e5a3
and under the tree's, which keeps each thread's open spans where the sampler reads them once a second.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-14-what-saying-what-a-thread-is-in-costs.py [walks] [rows] 2>NUL

`before` is Emitter.probe and Emitter.turn read out of ce86e5a3 and put on the tree's Emitter, the sampler
sampling the machine alone; `after` is the tree's, the sampler saying what each thread is in. The two are
walked in turn, walk by walk, in one process, so a slow spell of the machine's falls on both. Every walk's
time is printed, and how many of the sampler's "still_out" samples found a thread in a span.
"""
import os
import subprocess
import sys
import time

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import decoder as decmod  # noqa: E402
from sieve_player import document as D  # noqa: E402
from sieve_player import store, stream  # noqa: E402
from sieve_player.catalogue import Log  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.graph import Graph  # noqa: E402
from sieve_player.ledger import Ledger  # noqa: E402
from sieve_player.machine import Watch  # noqa: E402
from sieve_player.registry import discover  # noqa: E402
from sieve_player.worker import Worker  # noqa: E402

DOC = os.path.join(ROOT, "video-tests", "purb-settings.json")
WALKS = int(sys.argv[1]) if len(sys.argv) > 1 else 10
ROWS = int(sys.argv[2]) if len(sys.argv) > 2 else 600
WAS = "ce86e5a3"

was = {"__name__": "stream_as_it_stood"}
exec(subprocess.run(["git", "show", f"{WAS}:sieve_player/stream.py"], cwd=ROOT, capture_output=True, text=True, check=True).stdout, was)
PROBES = {"before": (was["Emitter"].probe, was["Emitter"].turn), "after": (stream.Emitter.probe, stream.Emitter.turn)}


def walk(tools, st, how, sink):
    stream.Emitter.probe, stream.Emitter.turn = PROBES[how]
    doc = D.load(DOC, tools)
    doc.node("bake").mode = D.LIVE
    dec = Decoder(doc.video)
    g = Graph(doc, dec, tools, open_bake=lambda bk, c: st.open_bake(bk, c))
    led = Ledger(timed=lambda: g.stream.turn("monitor", "ledger"), watch=Log())
    g.on_event = led.event
    sink[:] = [led.sample, g.stream.still_out if how == "after" else None]
    g.sync()
    n = min(ROWS, g.count)
    walked, series = [], []
    w = Worker(g)
    w.walked.connect(lambda d, m, *was: walked.append((d, m)))
    w.seriesReady.connect(lambda r, s, fps: series.append(r))
    w.set_window(0, n)
    t = time.perf_counter()
    w.start()
    while not (walked and walked[-1][0] == walked[-1][1] and (series or not g.chain)):
        QApplication.processEvents()
        time.sleep(0.002)
        if time.perf_counter() - t > 30:
            sys.exit("the walk did not finish")
    t = time.perf_counter() - t
    w.stop()
    sink[:] = [None, None]
    g.close()
    dec.close()
    return t


def main():
    QApplication.instance() or QApplication([])
    decmod.QUIET = True
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    st = store.current()
    sink, said = [None, None], [0, 0]

    def sample(name, value, t):
        if sink[0] is not None:
            sink[0](name, value, t)

    def still_out(cpu):
        out = sink[1](cpu) if sink[1] is not None else {}
        said[0] += sink[1] is not None
        said[1] += bool(out)
        return out
    machine = Watch(sample, still_out=still_out)     # one for the process: its counters take 0.4 s to open
    out = {how: [] for how in PROBES}
    for _ in range(WALKS):
        for how in PROBES:
            out[how].append(walk(tools, st, how, sink))
    machine.close()
    for how, ws in out.items():
        print(f"{how:6} " + " ".join(f"{t * 1000:5.0f}" for t in ws) + f"  ms   median {sorted(ws)[len(ws) // 2] * 1000:.0f}")
    print(f"{said[0]} samples of what each thread is in, {said[1]} finding one in a span")


if __name__ == "__main__":
    main()

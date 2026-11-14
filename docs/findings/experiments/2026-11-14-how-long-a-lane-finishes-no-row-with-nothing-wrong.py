"""Experiment behind docs/findings/2026-11-14-how-long-a-lane-finishes-no-row-with-nothing-wrong.md, the
sighting the Open on the time a lane may finish no row asks for in docs/spec/monitor.md: the longest a
lane of the Worker's goes between two rows finished on a healthy walk of video-tests/purb-settings.json,
its bake live, cold on a fresh Graph and Decoder, the window walked and then the clip for what is left
of SECONDS.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-14-how-long-a-lane-finishes-no-row-with-nothing-wrong.py [window rows] [seconds] 2>NUL

A lane's stretch runs from its last begin or progress, or the worker's last event in another lane or in
none, to its next begin or progress, by the clock at which each event was handed over. The longest of
each lane are printed with the row they ended at and the nodes whose spans took the most of them.
"""
import os
import sys
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
from sieve_player.graph import Graph  # noqa: E402
from sieve_player.registry import discover  # noqa: E402
from sieve_player.stream import BEGIN, HAND, NODES, PROGRESS  # noqa: E402
from sieve_player.worker import Worker  # noqa: E402

DOC = os.path.join(ROOT, "video-tests", "purb-settings.json")
ROWS = int(sys.argv[1]) if len(sys.argv) > 1 else 600
SECONDS = float(sys.argv[2]) if len(sys.argv) > 2 else 40.0
TOP = 5


def stretches(events, lane):
    """[(seconds, the rows done at its end, {node: ms of its spans in it})] of `lane`, longest first."""
    out, since, under, short = [], None, {}, False
    for now, ev in events:
        if ev.thread != "worker":
            continue
        if ev.lane == lane and ev.kind in (BEGIN, PROGRESS):
            if since is not None and short:
                out.append((now - since, ev.row if ev.kind == PROGRESS else 0, under))
            short = ev.length > 0 if ev.kind == BEGIN else ev.row < ev.length
            since, under = now, {}
        elif ev.lane != lane:
            since, under = now, {}
        elif ev.kind in NODES:
            under[ev.node] = under.get(ev.node, 0.0) + ev.ms
    return sorted(out, key=lambda s: -s[0])


def main():
    QApplication.instance() or QApplication([])
    decmod.QUIET = True
    tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
    st = store.current()
    doc = D.load(DOC, tools)
    doc.node("bake").mode = D.LIVE
    dec = Decoder(doc.video)
    g = Graph(doc, dec, tools, open_bake=lambda bk, c: st.open_bake(bk, c))
    events, facts = [], []
    g.on_event = lambda ev: (events.append((time.perf_counter(), ev)), ev.kind == "sync" and facts.append(ev.facts))
    g.sync()
    n = min(ROWS, g.count)
    walked, clip = [], []
    w = Worker(g)
    w.walked.connect(lambda d, m, *was: walked.append((d, m)))
    w.clipWalked.connect(lambda d, m, *was: clip.append((d, m)))
    w.set_window(0, n, by=HAND)
    t = time.perf_counter()
    w.start()
    asked = False
    while time.perf_counter() - t < SECONDS and not (clip and clip[-1][0] == clip[-1][1]):
        QApplication.processEvents()
        time.sleep(0.002)
        if not asked and walked and walked[-1][0] == walked[-1][1]:
            asked = True
            w.walk_clip(HAND)
    took = time.perf_counter() - t
    w.stop()
    g.close()
    dec.close()
    whole = {nid: f["whole_by"] for nid, f in facts[-1]["nodes"].items() if f["whole_by"]}
    print(f"{g.count} rows in the clip at {g.fps:.2f} fps; the window {walked[-1] if walked else None}, the clip {clip[-1] if clip else None}, in {took:.1f} s")
    print(f"the chain {facts[-1]['chain']}; run whole {whole or 'none'}; static {[nid for nid, f in facts[-1]['nodes'].items() if f['static']]}")
    for lane in ("window", "clip"):
        found = stretches(events, lane)
        print(f"{lane}: {len(found)} stretches; the longest, in ms, the rows done at its end and what its spans were under")
        for s, row, under in found[:TOP]:
            most = sorted(under.items(), key=lambda x: -x[1])[:4]
            print(f"  {s * 1000:8.1f}  at {row:>6}  " + ", ".join(f"{nid} {ms:.0f}" for nid, ms in most))
        if found:
            ms = sorted(s * 1000 for s, _, _ in found)
            print(f"  median {ms[len(ms) // 2]:.1f}, 99th percentile {ms[int(len(ms) * 0.99)]:.1f}")


if __name__ == "__main__":
    main()

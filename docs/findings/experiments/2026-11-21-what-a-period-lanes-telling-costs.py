"""What one telling of a period lane's progress costs by the periods it has queued: worker._Legs.emit
asks worker._walking of every leg left, and _walking looks for the leg's cut among the timed Walk's
cuts by equality. Over video-tests/GoPro-stress-test-periods-in-period-analysis.json and its held
file as they lay, one `period` gated by an unsmoothed `reduce` with `motion`, `reduce` and `smooth`
below it. No walk runs and no window opens; the plan is asked with the held runs behind it.

    .venv\Scripts\python -X utf8 docs\findings\experiments\2026-11-21-what-a-period-lanes-telling-costs.py 2>NUL

The document and its held file are Kendrick's and gitignored: with no run held from row 0 to the
clip's last row under the gate's key, the plan has no period and the script says so.
"""
import os
import sys
import time

os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from sieve_player import decoder as decmod
from sieve_player import document as D
from sieve_player import held
from sieve_player.decoder import Decoder
from sieve_player.graph import Graph
from sieve_player.heldwalks import gate_result
from sieve_player.registry import cut_by, discover
from sieve_player.worker import _clip_legs, _walks

DOC = os.path.join(ROOT, "video-tests", "GoPro-stress-test-periods-in-period-analysis.json")
decmod.QUIET = True
tools = {e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}
doc = D.load(DOC, tools)
runs = held.Runs(1 << 40, lambda nid, r: 0)
runs.take(held.File(held.path_for(DOC)).load())
dec = Decoder(doc.video)
dec.ends_at(max((r.rows for r in runs if r.cut is None and r.start == 0), default=dec.count))    # the crop ends short of the plate's claim, which a walk learns and this script does not walk


def cut_result(nid, key, within):
    by = cut_by(tools.get(doc.node(nid).tool))
    w = by and doc.source(nid, by[0])
    return gate_result(runs, w.src, key, within, dec.count) if w else None


g = Graph(doc, dec, tools, cut_result=cut_result)
p = g.snapshot()
print("timed", [(w.heads, w.chain, len(w.cuts)) for w in p.timed] or "none: no run of the gate is held over the clip whole")
legs = _clip_legs(p)


def emit_cost(plan, legs):
    t = time.perf_counter()
    under = _walks(plan)
    n = sum((leg.walked, leg.cut) in under for leg in legs)
    return 1000 * (time.perf_counter() - t), n


print("one _Legs.emit over %d legs, the legs' records the plan's own: %.0f ms (%d walked)" % (len(legs), *emit_cost(p, legs)))
t = time.perf_counter()
g.sync()
print(f"one sync {1000 * (time.perf_counter() - t):.0f} ms")
q = g.snapshot()
print("the same after a sync made the plan's records again, equal and not the same objects: %.0f ms (%d walked)" % emit_cost(q, legs))
half = legs[len(legs) // 2:]
print("with half the legs left: %.0f ms" % emit_cost(q, half)[0])

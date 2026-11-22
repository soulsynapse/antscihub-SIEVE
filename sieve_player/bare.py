"""`python -m sieve_player.bare job.json`: the clip walked in a process of its own, with no stream
and no interface beside it, and what a clip walk in the player holds left in a file: the series
chain's results over the clip, then each cut in time's that those and the cuts' own make. The
window starts it and reads its stdout, one JSON object a line: `{"done", "total", "rate"}` as rows
land, `{"count"}` where the stream ended short, `{"period", "of"}` as cuts are walked, then one of
`{"results": path}`, `{"refused": why}` or `{"failed": [row, node, text]}`. The file pickles (the
clip's results, their first row, fps, [(a cut's results, its first row, the cut as
heldwalks.period_run takes it), ...] as walked, the frame nodes' small rows its memo still holds, as
result_keeper.Keeper.take takes them). The walk is walk._Walk's, driven on this thread. Nothing else
of the walk is left on disk: the player's checkpoint carries the rows.
"""
import json
import os
import pickle
import sys
import time

from . import budget

TELL = 0.1      # s between the lines that say how far the walk is
HOLD = budget.here()["hold"] # what the memo and the plate's cache may each hold: nothing reads a row again but a tool reading near its own


def job(doc, video, tools, out):
    """What a bare walk is started with: the document as it stands, where it lives, the video the
    player has open, the tools by the folders their files are in and the file the results go to."""
    files = [os.path.abspath(t.__file__) for t in tools.values() if getattr(t, "__file__", None)]
    return {"document": doc.to_dict(), "path": doc.path, "video": video,
            "roots": sorted({os.path.dirname(f) for f in files}), "out": out}


class _Told:
    """A signal's place on a _Walk: what was last emitted, and a call for each."""

    def __init__(self, then=None):
        self.last, self.then = None, then

    def emit(self, *args):
        self.last = args
        if self.then is not None:
            self.then(*args)


def say(**line):
    print(json.dumps(line), flush=True)


def main(path):
    with open(path, encoding="utf-8") as f:
        j = json.load(f)
    for root in j["roots"]:
        sys.path.insert(0, os.path.dirname(root))
    from . import held
    from .decoder import Decoder, EndOfStream
    from .document import Document
    from .graph import Graph
    from .heldwalks import gate_result, held_chain, period_run
    from .registry import cut_by, discover
    from .walk import _Walk

    tools = {e.name: e.module for e in discover(*j["roots"]) if e.ok}
    doc = Document.from_dict(j["document"], tools)
    doc.path = j["path"]
    runs = held.Runs(1 << 62, lambda nid, result: 0)    # every run stays: the file is written of them all

    def cut_result(nid, key, within):
        by = cut_by(tools.get(doc.node(nid).tool))
        wired = by and doc.source(nid, by[0])
        return gate_result(runs, wired.src, key, within, footage.count) if wired else None

    footage = Decoder(j["video"], cache_bytes=HOLD)
    g = Graph(doc, footage, tools, memo_bytes=HOLD, keeps=True, cut_result=cut_result)
    g.sync()
    p = g.snapshot()
    if not g.fed(p.walk):
        say(refused="nothing reaches a walked node")
        return 1
    t0 = [None]

    def told(done, total, *was):
        t0[0] = t0[0] or (time.perf_counter(), done)
        dt = time.perf_counter() - t0[0][0]
        say(done=done, total=total, rate=(done - t0[0][1]) / dt if dt > 0 else 0.0)

    ready, refused, failed = _Told(), _Told(), _Told()
    walk = _Walk(g, name="clip", every=g.count, progress=_Told(told), ready=ready, refused=refused, failed=failed, tell_every=TELL, plan=p)
    walk.begin(0, g.count)
    try:
        while walk.i < walk.length:
            walk.turn()
    except EndOfStream:     # as the Worker takes it: the walk closes at the rows it has
        say(count=g.count)
        walk.ended()
        if failed.last:
            say(failed=[failed.last[0], failed.last[1], "the chain raised over the rows the stream had"])
            return 1
    except Exception as e:
        say(failed=[walk.start + walk.i, getattr(e, "sieve_node", ""), f"{type(e).__name__}: {e}"])
        return 1
    if refused.last:
        say(refused=refused.last[0])
        return 1
    results, start, fps = ready.last or ({}, 0, g.fps)
    has = {nid: r for nid, r in results.items() if isinstance(r, dict) and "signal" in r}
    rows = max((len(r["signal"]) for r in has.values()), default=0)
    runs.hold(0, rows, {nid: r for nid, r in has.items() if len(r["signal"]) == rows}, held_chain(p, p.chain))
    periods, tried = [], set()
    leg = _Walk(g, name="clip", every=1 << 62, progress=_Told(), ready=_Told(), refused=refused, failed=failed, keeps=True)
    try:
        while True:
            g.sync()
            p = g.snapshot()
            due = [(w, c) for w in p.timed for c in w.cuts
                   if c.extent.rows[0] < c.extent.rows[1] and (p.entries[w.heads[0]].src, c) not in tried]
            if not due:
                break
            for n, (w, c) in enumerate(due):
                of = (p.entries[w.heads[0]].src, c)
                tried.add(of)
                leg.plan, leg.walked, leg.cut, leg.ready.last = p.of(w), *of, None
                leg.begin(c.extent.rows[0], c.extent.rows[1] - c.extent.rows[0])
                while leg.i < leg.length:
                    leg.turn()
                if leg.ready.last is None:
                    continue
                got, first, _ = leg.ready.last
                periods.append((got, first, of))
                run = period_run(p, got, first, of)
                if run is not None:
                    runs.hold(run.start, run.rows, run.results, run.chain, run.cut, walked=run.walked)
                say(period=len(tried), of=len(tried) + len(due) - n - 1)
    except Exception as e:
        say(failed=[leg.start + leg.i, getattr(e, "sieve_node", ""), f"{type(e).__name__}: {e}"])
        return 1
    rows = {(key, chunk): got for key, chunk, got in g.keeper.kept(short=True)}
    with open(j["out"], "wb") as f:
        pickle.dump((results, start, fps, periods, rows), f, protocol=pickle.HIGHEST_PROTOCOL)
    say(results=j["out"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
